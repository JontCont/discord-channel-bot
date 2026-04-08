import random
import string

import discord
from discord import app_commands
from discord.ext import commands

from config import AUTO_VOICE_TRIGGER, AUTO_VOICE_SUFFIX

PRIVATE_CATEGORY = "🔒 私人湯"
PRIVATE_TRIGGER = "➕ 開設私人包廂"
PRIVATE_SUFFIX = "的包廂"
PRIVATE_LIMIT = 4
PASSWORD_CHANNEL = "🔑｜輸入密碼"


def _generate_password(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class AutoVoice(commands.Cog):
    """自動語音頻道模組 — 公開語音房 & 私人包廂"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # channel_id -> {"owner": user_id, "private": bool, "password": str|None}
        self.active_channels: dict[int, dict] = {}

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        # --- User joined a trigger channel ---
        if after.channel is not None:
            # Public voice trigger
            if after.channel.name == AUTO_VOICE_TRIGGER:
                category = after.channel.category
                channel_name = f"{member.display_name} 的{AUTO_VOICE_SUFFIX}"

                new_channel = await member.guild.create_voice_channel(
                    name=channel_name,
                    category=category,
                    user_limit=6,
                    reason=f"Auto-voice: created for {member}",
                )
                self.active_channels[new_channel.id] = {
                    "owner": member.id,
                    "private": False,
                    "password": None,
                }
                await member.move_to(new_channel)

            # Private room trigger
            elif after.channel.name == PRIVATE_TRIGGER:
                category = after.channel.category
                password = _generate_password()
                channel_name = f"🔒 {member.display_name}{PRIVATE_SUFFIX}"

                overwrites = {
                    member.guild.default_role: discord.PermissionOverwrite(
                        connect=False, view_channel=True
                    ),
                    member: discord.PermissionOverwrite(
                        connect=True, view_channel=True, manage_channels=True
                    ),
                    member.guild.me: discord.PermissionOverwrite(
                        connect=True, view_channel=True, manage_channels=True
                    ),
                }

                new_channel = await member.guild.create_voice_channel(
                    name=channel_name,
                    category=category,
                    user_limit=PRIVATE_LIMIT,
                    overwrites=overwrites,
                    reason=f"Private room: created for {member}",
                )
                self.active_channels[new_channel.id] = {
                    "owner": member.id,
                    "private": True,
                    "password": password,
                }
                await member.move_to(new_channel)

                # DM the password to the owner
                try:
                    embed = discord.Embed(
                        title="🔒 你的私人包廂已建立",
                        description=(
                            f"頻道：**{channel_name}**\n"
                            f"密碼：`{password}`\n\n"
                            f"將密碼分享給朋友，他們可以在 **#{PASSWORD_CHANNEL}** 頻道輸入密碼加入！"
                        ),
                        color=discord.Color.orange(),
                    )
                    await member.send(embed=embed)
                except discord.Forbidden:
                    pass

        # --- Cleanup: delete empty auto-created channels ---
        if before.channel is not None and before.channel.id in self.active_channels:
            if len(before.channel.members) == 0:
                self.active_channels.pop(before.channel.id, None)
                await before.channel.delete(reason="Auto-voice: channel empty")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for password input in the password channel."""
        if message.author.bot:
            return
        if message.channel.name != PASSWORD_CHANNEL:
            return

        entered = message.content.strip()

        # Always delete the message to hide the password
        try:
            await message.delete()
        except discord.Forbidden:
            pass

        # Find matching private room
        for channel_id, info in self.active_channels.items():
            if info["private"] and info["password"] == entered:
                voice_channel = message.guild.get_channel(channel_id)
                if voice_channel is None:
                    continue

                # Grant connect permission
                await voice_channel.set_permissions(
                    message.author, connect=True, view_channel=True
                )

                confirm = await message.channel.send(
                    f"✅ {message.author.mention} 密碼正確！你現在可以加入 **{voice_channel.name}** 了。",
                )
                # Auto-delete confirmation after 5 seconds
                await confirm.delete(delay=5)
                return

        # Wrong password
        err = await message.channel.send(
            f"❌ {message.author.mention} 密碼錯誤，請再試一次。"
        )
        await err.delete(delay=5)

    # ── Helper: check ownership ──────────────────────────────

    def _get_owned_channel(
        self, interaction: discord.Interaction
    ) -> tuple[discord.VoiceChannel | None, str | None]:
        """Return (channel, error_message). error_message is None on success."""
        if interaction.user.voice is None or interaction.user.voice.channel is None:
            return None, "❌ 你必須先在語音頻道中才能使用此指令。"

        channel = interaction.user.voice.channel
        info = self.active_channels.get(channel.id)
        if info is None:
            return None, "❌ 這不是自動建立的語音頻道。"
        if info["owner"] != interaction.user.id:
            return None, "❌ 只有房主才能使用此指令。"
        return channel, None

    # ── /voice-name ──────────────────────────────────────────

    @app_commands.command(
        name="voice-name",
        description="重新命名你目前的自動語音頻道",
    )
    @app_commands.describe(name="新的頻道名稱")
    async def voice_name(self, interaction: discord.Interaction, name: str):
        channel, err = self._get_owned_channel(interaction)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return

        await channel.edit(name=name)
        await interaction.response.send_message(
            f"✅ 頻道已重新命名為 **{name}**", ephemeral=True
        )

    # ── /voice-limit ─────────────────────────────────────────

    @app_commands.command(
        name="voice-limit",
        description="設定你的語音頻道人數上限",
    )
    @app_commands.describe(limit="人數上限（0 = 無限制）")
    async def voice_limit(self, interaction: discord.Interaction, limit: int):
        channel, err = self._get_owned_channel(interaction)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return

        await channel.edit(user_limit=max(0, min(limit, 99)))
        display = "無限制" if limit == 0 else str(limit)
        await interaction.response.send_message(
            f"✅ 人數上限已設為 **{display}**", ephemeral=True
        )

    # ── /voice-invite ────────────────────────────────────────

    @app_commands.command(
        name="voice-invite",
        description="邀請成員進入你的私人包廂",
    )
    @app_commands.describe(member="要邀請的成員")
    async def voice_invite(
        self, interaction: discord.Interaction, member: discord.Member
    ):
        channel, err = self._get_owned_channel(interaction)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return

        info = self.active_channels[channel.id]
        if not info["private"]:
            await interaction.response.send_message(
                "ℹ️ 這是公開語音房，不需要邀請。", ephemeral=True
            )
            return

        await channel.set_permissions(member, connect=True, view_channel=True)
        await interaction.response.send_message(
            f"✅ 已邀請 {member.mention} 進入包廂。", ephemeral=True
        )

    # ── /voice-kick ──────────────────────────────────────────

    @app_commands.command(
        name="voice-kick",
        description="將成員踢出你的語音頻道",
    )
    @app_commands.describe(member="要踢出的成員")
    async def voice_kick(
        self, interaction: discord.Interaction, member: discord.Member
    ):
        channel, err = self._get_owned_channel(interaction)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return

        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ 你不能踢出自己。", ephemeral=True
            )
            return

        info = self.active_channels[channel.id]
        if info["private"]:
            await channel.set_permissions(member, overwrite=None)
        if member.voice and member.voice.channel == channel:
            await member.move_to(None)

        await interaction.response.send_message(
            f"✅ 已將 {member.mention} 踢出頻道。", ephemeral=True
        )

    # ── /setup-voice ─────────────────────────────────────────

    @app_commands.command(
        name="setup-voice",
        description="在所有分類下建立自動語音觸發頻道",
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def setup_voice(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        created = []
        skipped = []

        for category in guild.categories:
            if category.name == PRIVATE_CATEGORY:
                continue

            exists = any(
                ch.name == AUTO_VOICE_TRIGGER
                for ch in category.voice_channels
            )
            if exists:
                skipped.append(category.name)
                continue

            await guild.create_voice_channel(
                name=AUTO_VOICE_TRIGGER,
                category=category,
                reason=f"Auto-voice setup by {interaction.user}",
            )
            created.append(category.name)

        lines = []
        if created:
            lines.append("✅ 已建立觸發頻道於：\n" + "\n".join(f"　• {c}" for c in created))
        if skipped:
            lines.append("⏭️ 已存在，跳過：\n" + "\n".join(f"　• {c}" for c in skipped))
        if not created and not skipped:
            lines.append("⚠️ 伺服器中沒有任何分類。")

        await interaction.followup.send("\n\n".join(lines), ephemeral=True)

    # ── /setup-private ───────────────────────────────────────

    @app_commands.command(
        name="setup-private",
        description="建立私人包廂分類與觸發頻道",
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def setup_private(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        category = discord.utils.get(guild.categories, name=PRIVATE_CATEGORY)
        if not category:
            category = await guild.create_category(
                name=PRIVATE_CATEGORY,
                reason=f"Private room setup by {interaction.user}",
            )

        results = []

        # Create password text channel
        has_pw_channel = any(
            ch.name == PASSWORD_CHANNEL for ch in category.text_channels
        )
        if not has_pw_channel:
            await category.create_text_channel(
                name=PASSWORD_CHANNEL,
                topic="輸入包廂密碼即可加入私人語音頻道，訊息會自動刪除。",
                reason=f"Private room setup by {interaction.user}",
            )
            results.append(f"#{PASSWORD_CHANNEL}")

        # Create voice trigger
        has_trigger = any(
            ch.name == PRIVATE_TRIGGER for ch in category.voice_channels
        )
        if not has_trigger:
            await category.create_voice_channel(
                name=PRIVATE_TRIGGER,
                reason=f"Private room setup by {interaction.user}",
            )
            results.append(PRIVATE_TRIGGER)

        if results:
            await interaction.followup.send(
                f"✅ 已在「{PRIVATE_CATEGORY}」建立：\n"
                + "\n".join(f"　• {r}" for r in results)
            )
        else:
            await interaction.followup.send(
                f"⏭️ 「{PRIVATE_CATEGORY}」分類和所有頻道已存在。"
            )

    @setup_voice.error
    @setup_private.error
    async def setup_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            if interaction.response.is_done():
                await interaction.followup.send(
                    "🚫 你需要「管理頻道」權限才能使用此指令。", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "🚫 你需要「管理頻道」權限才能使用此指令。", ephemeral=True
                )


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoVoice(bot))
