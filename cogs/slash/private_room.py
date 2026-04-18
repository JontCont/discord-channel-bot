import random
import string

import discord
from discord import app_commands
from discord.ext import commands

from config import (
    PRIVATE_CATEGORY,
    PRIVATE_TRIGGER,
    PRIVATE_SUFFIX,
    PRIVATE_LIMIT,
    PASSWORD_CHANNEL,
)


def _generate_password(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class PrivateRoom(commands.Cog):
    """私人包廂模組 — 密碼制私人語音房"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @property
    def registry(self):
        return self.bot.room_registry

    # ── Voice state: private trigger & cleanup ───────────────

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        # Private room trigger
        if after.channel is not None and after.channel.name == PRIVATE_TRIGGER:
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
            self.registry.register(
                new_channel.id, member.id, private=True, password=password
            )
            await member.move_to(new_channel)

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

    # ── Password input listener ──────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for password input in the password channel."""
        if message.author.bot:
            return
        if message.channel.name != PASSWORD_CHANNEL:
            return

        entered = message.content.strip()

        try:
            await message.delete()
        except discord.Forbidden:
            pass

        channel_id, _ = self.registry.find_by_password(entered)
        if channel_id:
            voice_channel = message.guild.get_channel(channel_id)
            if voice_channel:
                await voice_channel.set_permissions(
                    message.author, connect=True, view_channel=True
                )
                confirm = await message.channel.send(
                    f"✅ {message.author.mention} 密碼正確！你現在可以加入 **{voice_channel.name}** 了。",
                )
                await confirm.delete(delay=5)
                return

        err = await message.channel.send(
            f"❌ {message.author.mention} 密碼錯誤，請再試一次。"
        )
        await err.delete(delay=5)

    # ── /voice-invite ────────────────────────────────────────

    @app_commands.command(
        name="voice-invite",
        description="邀請成員進入你的私人包廂",
    )
    @app_commands.describe(member="要邀請的成員")
    async def voice_invite(
        self, interaction: discord.Interaction, member: discord.Member
    ):
        channel, err = self.registry.get_owned_channel(interaction)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return

        info = self.registry.get(channel.id)
        if not info["private"]:
            await interaction.response.send_message(
                "ℹ️ 這是公開語音房，不需要邀請。", ephemeral=True
            )
            return

        await channel.set_permissions(member, connect=True, view_channel=True)
        await interaction.response.send_message(
            f"✅ 已邀請 {member.mention} 進入包廂。", ephemeral=True
        )

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

        has_pw_channel = any(
            ch.name == PASSWORD_CHANNEL for ch in category.text_channels
        )
        if not has_pw_channel:
            await category.create_text_channel(
                name=PASSWORD_CHANNEL,
                topic="輸入包廂密碼即可加入私人語音頻道",
                reason=f"Private room setup by {interaction.user}",
            )
            results.append(f"#{PASSWORD_CHANNEL}")

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
            await self._post_password_rules(guild)
        else:
            await interaction.followup.send(
                f"⏭️ 「{PRIVATE_CATEGORY}」分類和所有頻道已存在。"
            )

    def _build_password_rules_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🔑 私人包廂密碼頻道",
            description=(
                "在這裡輸入密碼即可加入朋友的私人語音包廂！\n"
                "━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.orange(),
        )
        embed.add_field(
            name="📋 使用方式",
            value=(
                "1️⃣ 向包廂房主取得密碼\n"
                "2️⃣ 在此頻道直接輸入密碼\n"
                "3️⃣ 密碼正確後即可加入語音頻道"
            ),
            inline=False,
        )
        embed.add_field(
            name="ℹ️ 注意事項",
            value=(
                "• 你的訊息會**自動刪除**，請放心輸入\n"
                "• 直接輸入密碼即可，不需要加任何指令\n"
                "• 每組密碼對應一個私人包廂\n"
                "• 包廂關閉後密碼即失效"
            ),
            inline=False,
        )
        embed.set_footer(text="💡 房主可透過 /voice-invite 直接邀請成員")
        return embed

    async def _post_password_rules(self, guild: discord.Guild):
        """Post or update the rules embed in the password channel."""
        for cat in guild.categories:
            if cat.name == PRIVATE_CATEGORY:
                break
        else:
            return

        channel = discord.utils.get(cat.text_channels, name=PASSWORD_CHANNEL)
        if not channel:
            return

        embed = self._build_password_rules_embed()

        async for msg in channel.history(limit=10):
            if msg.author == self.bot.user and msg.embeds:
                if msg.embeds[0].title == embed.title:
                    await msg.edit(embed=embed)
                    return

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        """Post password rules embed on startup."""
        for guild in self.bot.guilds:
            await self._post_password_rules(guild)

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
    from cogs.service.room_registry import RoomRegistry

    if not hasattr(bot, "room_registry"):
        bot.room_registry = RoomRegistry()
    await bot.add_cog(PrivateRoom(bot))
