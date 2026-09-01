import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks


logger = logging.getLogger(__name__)


class AutoVoice(commands.Cog):
    """自動語音頻道模組 — 公開語音房 & 房主管理指令"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cleanup_empty_rooms.start()

    async def cog_unload(self):
        self.cleanup_empty_rooms.cancel()

    @property
    def registry(self):
        return self.bot.room_registry

    # ── Voice state: public trigger & cleanup ────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        settings = await self.bot.guild_settings_service.get(member.guild.id)

        # Public voice trigger
        if (
            after.channel is not None
            and after.channel.name == settings.auto_voice_trigger
        ):
            category = after.channel.category
            channel_name = f"{member.display_name} 的{settings.auto_voice_suffix}"

            new_channel = await member.guild.create_voice_channel(
                name=channel_name,
                category=category,
                user_limit=settings.auto_voice_limit,
                reason=f"Auto-voice: created for {member}",
            )
            self.registry.register(new_channel.id, member.id)
            await member.move_to(new_channel)

        # Cleanup: delete empty auto-created channels
        if before.channel is not None and self.registry.get(before.channel.id):
            if len(before.channel.members) == 0:
                await self._delete_registered_channel(
                    before.channel, reason="Auto-voice: channel empty"
                )

    async def _delete_registered_channel(
        self, channel: discord.VoiceChannel, *, reason: str
    ) -> bool:
        if channel.members:
            return False
        try:
            await channel.delete(reason=reason)
        except discord.NotFound:
            pass
        except (discord.Forbidden, discord.HTTPException):
            logger.warning(
                "Failed to delete empty dynamic voice channel %s (%s)",
                channel.name,
                channel.id,
                exc_info=True,
            )
            return False
        self.registry.unregister(channel.id)
        return True

    @staticmethod
    def _looks_like_private_room(channel: discord.VoiceChannel) -> bool:
        guild = channel.guild
        bot_member = guild.me
        if bot_member is None or not channel.name.startswith("🔒"):
            return False
        everyone_permissions = channel.overwrites_for(guild.default_role)
        bot_permissions = channel.overwrites_for(bot_member)
        return (
            everyone_permissions.connect is False
            and bot_permissions.connect is True
            and bot_permissions.manage_channels is True
        )

    @tasks.loop(minutes=1)
    async def cleanup_empty_rooms(self):
        """Recover missed voice events and remove orphaned dynamic rooms."""
        for channel_id, _info in self.registry.entries():
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                self.registry.unregister(channel_id)
                continue
            if not isinstance(channel, discord.VoiceChannel):
                self.registry.unregister(channel_id)
                continue
            if not channel.members:
                await self._delete_registered_channel(
                    channel, reason="Auto-voice: periodic empty-room cleanup"
                )

        for guild in self.bot.guilds:
            try:
                settings = await self.bot.guild_settings_service.get(guild.id)
                category = discord.utils.get(
                    guild.categories, name=settings.private_category
                )
                if category is None:
                    continue
                for channel in tuple(category.voice_channels):
                    if self.registry.get(channel.id) or channel.members:
                        continue
                    if channel.name == settings.private_trigger:
                        continue
                    if not self._looks_like_private_room(channel):
                        continue
                    try:
                        await channel.delete(
                            reason="Private room: orphaned empty-room cleanup"
                        )
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        logger.warning(
                            "Failed to delete orphaned private room %s (%s)",
                            channel.name,
                            channel.id,
                            exc_info=True,
                        )
            except Exception:
                logger.exception("Failed to scan empty rooms in guild %s", guild.id)

    @cleanup_empty_rooms.before_loop
    async def before_cleanup_empty_rooms(self):
        await self.bot.wait_until_ready()

    # ── /voice-name ──────────────────────────────────────────

    @app_commands.command(
        name="voice-name",
        description="重新命名你目前所擁有的動態語音頻道（僅房主可用）",
    )
    @app_commands.describe(name="新的語音頻道名稱")
    async def voice_name(self, interaction: discord.Interaction, name: str):
        channel, err = self.registry.get_owned_channel(interaction)
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
        description="設定你的動態語音頻道人數上限（僅房主可用）",
    )
    @app_commands.describe(limit="人數上限（0 為無限制，最大 99）")
    async def voice_limit(self, interaction: discord.Interaction, limit: int):
        channel, err = self.registry.get_owned_channel(interaction)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return

        await channel.edit(user_limit=max(0, min(limit, 99)))
        display = "無限制" if limit == 0 else str(limit)
        await interaction.response.send_message(
            f"✅ 人數上限已設為 **{display}**", ephemeral=True
        )

    # ── /voice-kick ──────────────────────────────────────────

    @app_commands.command(
        name="voice-kick",
        description="將指定成員踢出你的動態語音頻道（僅房主可用）",
    )
    @app_commands.describe(member="要踢出的成員")
    async def voice_kick(
        self, interaction: discord.Interaction, member: discord.Member
    ):
        channel, err = self.registry.get_owned_channel(interaction)
        if err:
            await interaction.response.send_message(err, ephemeral=True)
            return

        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ 你不能踢出自己。", ephemeral=True
            )
            return

        info = self.registry.get(channel.id)
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
        description="在伺服器各分類下批次建立自動語音觸發頻道（需管理頻道權限）",
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def setup_voice(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        settings = await self.bot.guild_settings_service.get(guild.id)
        created = []
        skipped = []

        for category in guild.categories:
            if category.name == settings.private_category:
                continue

            exists = any(
                ch.name == settings.auto_voice_trigger
                for ch in category.voice_channels
            )
            if exists:
                skipped.append(category.name)
                continue

            await guild.create_voice_channel(
                name=settings.auto_voice_trigger,
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

    @setup_voice.error
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
    await bot.add_cog(AutoVoice(bot))
