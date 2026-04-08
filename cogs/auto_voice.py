import discord
from discord import app_commands
from discord.ext import commands

from config import AUTO_VOICE_TRIGGER, AUTO_VOICE_SUFFIX

PRIVATE_CATEGORY = "🔒 私人湯"
PRIVATE_TRIGGER = "➕ 開設私人包廂"
PRIVATE_SUFFIX = "的包廂"
PRIVATE_LIMIT = 4


class AutoVoice(commands.Cog):
    """自動語音頻道模組 — 公開語音房 & 私人包廂"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # channel_id -> {"owner": user_id, "private": bool}
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
                }
                await member.move_to(new_channel)

            # Private room trigger
            elif after.channel.name == PRIVATE_TRIGGER:
                category = after.channel.category
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
                }
                await member.move_to(new_channel)

        # --- Cleanup: delete empty auto-created channels ---
        if before.channel is not None and before.channel.id in self.active_channels:
            if len(before.channel.members) == 0:
                self.active_channels.pop(before.channel.id, None)
                await before.channel.delete(reason="Auto-voice: channel empty")

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
        if category:
            has_trigger = any(
                ch.name == PRIVATE_TRIGGER for ch in category.voice_channels
            )
            if has_trigger:
                await interaction.followup.send(
                    f"⏭️ 「{PRIVATE_CATEGORY}」分類和觸發頻道已存在。"
                )
                return
        else:
            category = await guild.create_category(
                name=PRIVATE_CATEGORY,
                reason=f"Private room setup by {interaction.user}",
            )

        await category.create_voice_channel(
            name=PRIVATE_TRIGGER,
            reason=f"Private room setup by {interaction.user}",
        )

        await interaction.followup.send(
            f"✅ 已建立「{PRIVATE_CATEGORY}」分類與「{PRIVATE_TRIGGER}」觸發頻道。"
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
