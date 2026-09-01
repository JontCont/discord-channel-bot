import random
import string

import discord
from discord import app_commands
from discord.ext import commands


def _generate_password(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class PrivateRoom(commands.Cog):
    """私人包廂模組 — 密碼制私人語音房"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @property
    def registry(self):
        return self.bot.room_registry

    def _iter_level_roles(
        self,
        guild: discord.Guild,
        level_roles: tuple[tuple[int, str, int], ...],
    ):
        """Yield existing configured milestone roles."""
        for _, role_name, _ in level_roles:
            role = discord.utils.get(guild.roles, name=role_name)
            if role is not None:
                yield role

    # ── Voice state: private trigger & cleanup ───────────────

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        settings = await self.bot.guild_settings_service.get(member.guild.id)

        # Private room trigger
        if (
            after.channel is not None
            and after.channel.name == settings.private_trigger
        ):
            category = after.channel.category
            password = _generate_password()
            channel_name = f"🔒 {member.display_name}{settings.private_suffix}"

            # Lock the room by default, then explicitly grant the owner and bot access.
            overwrites = {
                member.guild.default_role: discord.PermissionOverwrite(
                    connect=False, view_channel=True
                ),
                # The room owner can enter, speak, and manage their own private room.
                member: discord.PermissionOverwrite(
                    connect=True,
                    view_channel=True,
                    speak=True,
                    use_voice_activation=True,
                    manage_channels=True,
                ),
                # The bot keeps management access so it can continue handling invites/cleanup.
                member.guild.me: discord.PermissionOverwrite(
                    connect=True,
                    view_channel=True,
                    speak=True,
                    use_voice_activation=True,
                    manage_channels=True,
                ),
            }

            # Keep private rooms visible for leveling roles even if category denies them.
            # They still cannot join until invited/password grants member-specific permission.
            for role in self._iter_level_roles(member.guild, settings.level_roles):
                overwrites[role] = discord.PermissionOverwrite(
                    connect=False,
                    view_channel=True,
                )

            new_channel = await member.guild.create_voice_channel(
                name=channel_name,
                category=category,
                user_limit=settings.private_limit,
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
                        f"將密碼分享給朋友，他們可以在 **#{settings.password_channel}** 頻道輸入密碼加入！"
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
        if message.guild is None:
            return

        settings = await self.bot.guild_settings_service.get(message.guild.id)
        if message.channel.name != settings.password_channel:
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
                    message.author,
                    connect=True,
                    view_channel=True,
                    speak=True,
                    use_voice_activation=True,
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
        description="邀請指定成員進入你目前所屬的私人語音包廂（僅房主可用）",
    )
    @app_commands.describe(member="要直接邀請進入包廂的成員")
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

        await channel.set_permissions(
            member,
            connect=True,
            view_channel=True,
            speak=True,
            use_voice_activation=True,
        )
        await interaction.response.send_message(
            f"✅ 已邀請 {member.mention} 進入包廂。", ephemeral=True
        )

    # ── /setup-private ───────────────────────────────────────

    @app_commands.command(
        name="setup-private",
        description="建立私人包廂分類、密碼驗證頻道與包廂觸發語音頻道（需管理頻道權限）",
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def setup_private(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        settings = await self.bot.guild_settings_service.get(guild.id)

        category = discord.utils.get(
            guild.categories, name=settings.private_category
        )
        if not category:
            category = await guild.create_category(
                name=settings.private_category,
                reason=f"Private room setup by {interaction.user}",
            )

        results = []

        has_pw_channel = any(
            ch.name == settings.password_channel for ch in category.text_channels
        )
        if not has_pw_channel:
            await category.create_text_channel(
                name=settings.password_channel,
                topic="輸入包廂密碼即可加入私人語音頻道",
                reason=f"Private room setup by {interaction.user}",
            )
            results.append(f"#{settings.password_channel}")

        password_channel = discord.utils.get(
            category.text_channels,
            name=settings.password_channel,
        )

        has_trigger = any(
            ch.name == settings.private_trigger for ch in category.voice_channels
        )
        if not has_trigger:
            await category.create_voice_channel(
                name=settings.private_trigger,
                reason=f"Private room setup by {interaction.user}",
            )
            results.append(settings.private_trigger)

        trigger_channel = discord.utils.get(
            category.voice_channels,
            name=settings.private_trigger,
        )

        # ── Fix visibility for @everyone and all existing level roles ──────────
        # Set explicit overwrites so category/channel-level denies don't block members.
        reason = f"Private room setup by {interaction.user}"
        everyone = guild.default_role

        # Category: everyone can see it
        await category.set_permissions(everyone, view_channel=True, reason=reason)

        # Password channel: everyone can see and type (messages auto-deleted)
        if password_channel is not None:
            await password_channel.set_permissions(
                everyone,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                reason=reason,
            )

        # Trigger voice channel: everyone can see and enter to create a room
        if trigger_channel is not None:
            await trigger_channel.set_permissions(
                everyone,
                view_channel=True,
                connect=True,
                reason=reason,
            )

        # Also apply to any existing level roles (redundant but explicit)
        role_updates = 0
        for role in self._iter_level_roles(guild, settings.level_roles):
            await category.set_permissions(role, view_channel=True, reason=reason)
            role_updates += 1
            if password_channel is not None:
                await password_channel.set_permissions(
                    role,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    reason=reason,
                )
            if trigger_channel is not None:
                await trigger_channel.set_permissions(
                    role, view_channel=True, connect=True, reason=reason
                )

        sync_note = f"🔧 已修正 @everyone 可見性權限。"
        if role_updates:
            sync_note += f"（另同步 {role_updates} 個等級角色）"

        if results:
            msg = (
                f"✅ 已在「{settings.private_category}」建立：\n"
                + "\n".join(f"　• {r}" for r in results)
                + f"\n\n{sync_note}"
            )
            await interaction.followup.send(msg)
            await self._post_password_rules(
                guild, settings.private_category, settings.password_channel
            )
        else:
            await interaction.followup.send(
                f"⏭️ 「{settings.private_category}」分類和所有頻道已存在。\n{sync_note}"
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

    async def _post_password_rules(
        self,
        guild: discord.Guild,
        private_category: str,
        password_channel: str,
    ):
        """Post or update the rules embed in the password channel."""
        for cat in guild.categories:
            if cat.name == private_category:
                break
        else:
            return

        channel = discord.utils.get(cat.text_channels, name=password_channel)
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
            settings = await self.bot.guild_settings_service.get(guild.id)
            await self._post_password_rules(
                guild, settings.private_category, settings.password_channel
            )

    # ── /fix-private-perms ──────────────────────────────────
    
    @app_commands.command(
        name="fix-private-perms",
        description="修復所有現有私人包廂的權限（確保房主完整管理權與隔離設定，需管理頻道權限）",
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def fix_private_perms(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        settings = await self.bot.guild_settings_service.get(guild.id)
        
        category = discord.utils.get(
            guild.categories, name=settings.private_category
        )
        if not category:
            await interaction.followup.send(
                f"❌ 找不到「{settings.private_category}」分類。請先執行 /setup-private。"
            )
            return
        
        fixed_count = 0
        error_count = 0
        fixed_channels = []
        
        for channel in category.voice_channels:
            # Skip trigger channel
            if channel.name == settings.private_trigger:
                continue
            
            # Check if this is a private room (has lock emoji or is in registry)
            if not channel.name.startswith("🔒"):
                continue
            
            try:
                # Get room info from registry
                info = self.registry.get(channel.id)
                if info and info.get("owner_id"):
                    owner = guild.get_member(info["owner_id"])
                    if owner:
                        # Grant full permissions to owner
                        await channel.set_permissions(
                            owner,
                            connect=True,
                            view_channel=True,
                            speak=True,
                            use_voice_activation=True,
                            manage_channels=True,
                            reason=f"Fix private room permissions by {interaction.user}",
                        )
                        
                        # Ensure bot has permissions
                        await channel.set_permissions(
                            guild.me,
                            connect=True,
                            view_channel=True,
                            speak=True,
                            use_voice_activation=True,
                            manage_channels=True,
                            reason=f"Fix private room permissions by {interaction.user}",
                        )
                        
                        # Ensure @everyone cannot connect but can view
                        await channel.set_permissions(
                            guild.default_role,
                            connect=False,
                            view_channel=True,
                            reason=f"Fix private room permissions by {interaction.user}",
                        )
                        
                        fixed_channels.append(f"🔒 {channel.name}")
                        fixed_count += 1
            except Exception as e:
                error_count += 1
                print(f"Error fixing permissions for {channel.name}: {e}")
        
        if fixed_count > 0:
            msg = f"✅ 已修復 {fixed_count} 個私人包廂的權限：\n"
            for ch_name in fixed_channels[:10]:  # Show first 10
                msg += f"　• {ch_name}\n"
            if len(fixed_channels) > 10:
                msg += f"　... 以及其他 {len(fixed_channels) - 10} 個頻道\n"
            if error_count > 0:
                msg += f"\n⚠️ {error_count} 個頻道修復失敗"
            await interaction.followup.send(msg)
        else:
            await interaction.followup.send(
                "ℹ️ 沒有找到需要修復的私人包廂，或所有包廂權限已正確設定。"
            )
    
    @fix_private_perms.error
    async def fix_perms_error(
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
