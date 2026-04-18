import discord
from discord import app_commands
from discord.ext import commands

from config import (
    AUTO_VOICE_TRIGGER,
    SKILL_PANEL_CHANNEL,
    SKILL_PANEL_DIRECT_JOIN_SKILLS,
    SKILL_PREFIX,
)
from cogs.repository.skill_invite_repository import SkillInviteRepository
from cogs.service.skill_service import SkillService


class SkillToggleButton(discord.ui.Button):
    """A single skill toggle button."""

    def __init__(
        self,
        service: SkillService,
        skill_name: str,
        emoji: str | None = None,
        allow_direct_join: bool = False,
    ):
        super().__init__(
            label=skill_name,
            emoji=emoji,
            style=discord.ButtonStyle.secondary,
            custom_id=f"skill_toggle:{skill_name}",
        )
        self._service = service
        self.skill_name = skill_name
        self._emoji_str = emoji
        self._allow_direct_join = allow_direct_join

    async def callback(self, interaction: discord.Interaction):
        role = self._service.find_role(
            interaction.guild,
            self.skill_name,
            self._emoji_str,
        )
        if not role:
            await interaction.response.send_message(
                f"❌ 找不到角色 **{self.skill_name}**。", ephemeral=True
            )
            return

        if role in interaction.user.roles:
            await interaction.user.remove_roles(role, reason="Skill panel toggle")
            await interaction.response.send_message(
                f"👋 你已離開湯技 **{self.skill_name}**", ephemeral=True
            )
        elif self._allow_direct_join:
            await interaction.user.add_roles(role, reason="Skill panel direct join")
            await interaction.response.send_message(
                f"✅ 你已加入湯技 **{self.skill_name}**", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                (
                    f"🔐 **{self.skill_name}** 現在採邀請碼加入。\n"
                    "請使用 `/skill join` 並輸入邀請碼。"
                ),
                ephemeral=True,
            )


class SkillPanelView(discord.ui.View):
    """Persistent view containing skill toggle buttons."""

    def __init__(
        self,
        service: SkillService,
        skills: list[tuple[str, str | None]],
        direct_join_skills: set[str] | None = None,
    ):
        super().__init__(timeout=None)
        direct_join_skills = direct_join_skills or set()
        for skill_name, emoji in skills:
            self.add_item(
                SkillToggleButton(
                    service,
                    skill_name,
                    emoji,
                    allow_direct_join=skill_name in direct_join_skills,
                )
            )


class SkillCommands(commands.GroupCog, name="skill"):
    """湯技管理模組 — 建立/刪除/加入/離開湯技角色與頻道"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.skill_service = SkillService(SkillInviteRepository())
        # guild_id -> message_id of the panel
        self._panel_messages: dict[int, int] = {}
        super().__init__()

    def _get_skills(self, guild: discord.Guild) -> list[tuple[str, str | None]]:
        return self.skill_service.get_skills(guild)

    def _build_panel_embed(
        self, skills: list[tuple[str, str | None]], guild: discord.Guild
    ) -> discord.Embed:
        return self.skill_service.build_panel_embed(skills, guild)

    def _skill_overwrites(self, guild: discord.Guild, role: discord.Role) -> dict:
        return self.skill_service.skill_overwrites(guild, role)

    async def _apply_skill_permissions(
        self,
        category: discord.CategoryChannel,
        role: discord.Role,
        reason: str,
    ):
        await self.skill_service.apply_skill_permissions(category, role, reason)

    async def _refresh_panel(self, guild: discord.Guild):
        """Update or create the skill panel in #湯技 channel."""
        channel = discord.utils.get(guild.text_channels, name=SKILL_PANEL_CHANNEL)
        if not channel:
            return

        skills = self._get_skills(guild)
        if not skills:
            return

        embed = self._build_panel_embed(skills, guild)
        view = SkillPanelView(self.skill_service, skills)
        self.bot.add_view(view)

        # Try to edit existing panel message
        msg_id = self._panel_messages.get(guild.id)
        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.edit(embed=embed, view=view)
                return
            except discord.NotFound:
                pass

        # Clean old bot messages and send new panel
        async for msg in channel.history(limit=50):
            if msg.author == self.bot.user:
                await msg.delete()

        new_msg = await channel.send(embed=embed, view=view)
        self._panel_messages[guild.id] = new_msg.id

    @commands.Cog.listener()
    async def on_ready(self):
        """Auto-post/update skill panel in #湯技 on startup."""
        for guild in self.bot.guilds:
            skills = self._get_skills(guild)
            if skills:
                self.bot.add_view(SkillPanelView(self.skill_service, skills))
            await self._refresh_panel(guild)

    # ── helpers ──────────────────────────────────────────────

    @staticmethod
    def _skill_category_name(name: str, emoji: str | None = None) -> str:
        return SkillService.skill_category_name(name, emoji)

    @staticmethod
    def _find_category(guild: discord.Guild, name: str) -> discord.CategoryChannel | None:
        return SkillService.find_category(guild, name)

    @staticmethod
    def _find_role(guild: discord.Guild, name: str) -> discord.Role | None:
        return SkillService.find_role(guild, name)

    @staticmethod
    def _auto_skill_role_color(name: str) -> discord.Colour:
        palette = [
            discord.Colour.blue(),
            discord.Colour.green(),
            discord.Colour.purple(),
            discord.Colour.orange(),
            discord.Colour.teal(),
            discord.Colour.magenta(),
            discord.Colour.gold(),
        ]
        index = sum(ord(ch) for ch in name.strip().lower()) % len(palette)
        return palette[index]

    async def _skill_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for skill names based on existing categories."""
        choices = []
        for cat in interaction.guild.categories:
            if cat.name.startswith(SKILL_PREFIX):
                skill_name = cat.name.removeprefix(SKILL_PREFIX).split(" ")[0]
                if current.lower() in skill_name.lower():
                    choices.append(app_commands.Choice(name=skill_name, value=skill_name))
        return choices[:25]

    # ── /skill create ────────────────────────────────────────

    @app_commands.command(name="create", description="建立新的湯技角色")
    @app_commands.describe(name="湯技名稱", emoji="湯技 emoji（選填）")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def skill_create(
        self,
        interaction: discord.Interaction,
        name: str,
        emoji: str | None = None,
    ):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # Check if skill already exists
        if self._find_category(guild, name):
            await interaction.followup.send(f"❌ 湯技 **{name}** 已經存在。")
            return

        # 1. Create role
        role_name = name.strip()
        if not role_name.startswith(SKILL_PREFIX):
            role_name = f"{SKILL_PREFIX}{role_name}"
        role = await guild.create_role(
            name=role_name,
            colour=self._auto_skill_role_color(name),
            mentionable=True,
            reason=f"Skill create by {interaction.user}",
        )

        # 2. Create category with permission overrides
        overwrites = self._skill_overwrites(guild, role)
        category_name = self._skill_category_name(name, emoji)
        category = await guild.create_category(
            name=category_name,
            overwrites=overwrites,
            reason=f"Skill create by {interaction.user}",
        )

        # 3. Create discussion + chat channels
        await category.create_forum(f"{name}-討論")
        await category.create_text_channel(f"{name}-聊天")

        # 4. Create voice trigger channel
        await category.create_voice_channel(AUTO_VOICE_TRIGGER)

        invite_code = self.skill_service.set_invite_code(guild.id, name)

        dm_status_text = "✅ 已將邀請碼私訊給你。"
        dm_failed = False
        try:
            await interaction.user.send(
                f"你建立的湯技 **{name}** 邀請碼為：`{invite_code}`\n"
                f"伺服器：**{guild.name}**\n"
                "可使用 `/skill info` 查看或重新產生邀請碼。"
            )
        except (discord.Forbidden, discord.HTTPException):
            dm_failed = True
            dm_status_text = "⚠️ 無法私訊你邀請碼（請確認已開啟私訊）。"

        create_msg = (
            f"✅ 湯技 **{name}** 已建立！\n"
            f"　• 角色：{role.mention}\n"
            f"　• 分類：{category_name}\n"
            f"　• 頻道：{name}-討論（論壇）、#{name}-聊天\n"
            f"　• 語音：{AUTO_VOICE_TRIGGER}\n"
            f"　• 邀請碼通知：{dm_status_text}"
        )
        if dm_failed:
            create_msg += f"\n　• 備援顯示邀請碼：`{invite_code}`"

        await interaction.followup.send(create_msg, ephemeral=True)
        await self._refresh_panel(guild)

    # ── /skill delete ────────────────────────────────────────

    @app_commands.command(name="delete", description="刪除湯技角色及其頻道")
    @app_commands.describe(name="湯技名稱")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.autocomplete(name=_skill_autocomplete)
    async def skill_delete(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        category = self._find_category(guild, name)
        if not category:
            await interaction.followup.send(f"❌ 找不到湯技 **{name}**。")
            return

        # Delete all channels in category
        for channel in category.channels:
            await channel.delete(reason=f"Skill delete by {interaction.user}")
        await category.delete(reason=f"Skill delete by {interaction.user}")

        # Delete role
        role = self._find_role(guild, name)
        if role:
            await role.delete(reason=f"Skill delete by {interaction.user}")

        self.skill_service.delete_invite_code(guild.id, name)

        await interaction.followup.send(f"✅ 湯技 **{name}** 已刪除（角色 + 分類 + 所有頻道）。")
        await self._refresh_panel(guild)

    # ── /skill join ──────────────────────────────────────────

    @app_commands.command(name="join", description="使用邀請碼加入湯技角色")
    @app_commands.describe(code="湯技邀請碼")
    async def skill_join(self, interaction: discord.Interaction, code: str):
        guild = interaction.guild
        matched = self.skill_service.find_skill_by_code(guild, code)

        if not matched:
            await interaction.response.send_message(
                "❌ 邀請碼無效，請向管理員確認最新邀請碼。", ephemeral=True
            )
            return

        name, role = matched

        if role in interaction.user.roles:
            await interaction.response.send_message(
                f"⚠️ 你已經擁有 **{name}** 角色了。", ephemeral=True
            )
            return

        await interaction.user.add_roles(role, reason="Skill join")
        await interaction.response.send_message(
            f"✅ 你已加入湯技 **{name}**！", ephemeral=True
        )

    # ── /skill info ──────────────────────────────────────────

    @app_commands.command(name="info", description="查看湯技詳情（可選擇重新產生邀請碼）")
    @app_commands.describe(name="湯技名稱", regenerate_invite="是否重新產生邀請碼")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.autocomplete(name=_skill_autocomplete)
    async def skill_info(
        self,
        interaction: discord.Interaction,
        name: str,
        regenerate_invite: bool = False,
    ):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        category = self._find_category(guild, name)
        role = self._find_role(guild, name)

        if not category and not role:
            await interaction.followup.send(f"❌ 找不到湯技 **{name}**。", ephemeral=True)
            return

        skill_name = name.strip()
        if regenerate_invite:
            invite_code = self.skill_service.set_invite_code(guild.id, skill_name)
        else:
            invite_code = self.skill_service.ensure_invite_code(guild.id, skill_name)

        role_mention = role.mention if role else "（找不到對應角色）"
        role_name = role.name if role else "（找不到對應角色）"
        category_name = category.name if category else f"{SKILL_PREFIX}{skill_name}"
        regen_text = "（已重新產生）" if regenerate_invite else ""

        await interaction.followup.send(
            f"📌 湯技 **{skill_name}** 詳情\n"
            f"　• 邀請碼：`{invite_code}` {regen_text}\n"
            f"　• 權限角色：{role_mention}\n"
            f"　• 角色名稱：`{role_name}`\n"
            f"　• 分類：`{category_name}`",
            ephemeral=True,
        )

    # ── /skill regen ────────────────────────────────────────

    @app_commands.command(name="regen", description="重新產生湯技邀請碼")
    @app_commands.describe(name="湯技名稱")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.autocomplete(name=_skill_autocomplete)
    async def skill_regen(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        role = self._find_role(guild, name)
        if not role:
            await interaction.followup.send(f"❌ 找不到湯技角色 **{name}**。")
            return

        new_code = self.skill_service.set_invite_code(guild.id, name)
        await interaction.followup.send(
            f"✅ **{name}** 邀請碼已重新產生：`{new_code}`"
        )

    # ── /skill leave ─────────────────────────────────────────

    @app_commands.command(name="leave", description="離開湯技角色")
    @app_commands.describe(name="湯技名稱")
    @app_commands.autocomplete(name=_skill_autocomplete)
    async def skill_leave(self, interaction: discord.Interaction, name: str):
        guild = interaction.guild
        role = self._find_role(guild, name)

        if not role:
            await interaction.response.send_message(
                f"❌ 找不到湯技角色 **{name}**。", ephemeral=True
            )
            return

        if role not in interaction.user.roles:
            await interaction.response.send_message(
                f"⚠️ 你沒有 **{name}** 角色。", ephemeral=True
            )
            return

        await interaction.user.remove_roles(role, reason="Skill leave")
        await interaction.response.send_message(
            f"✅ 你已離開湯技 **{name}**。", ephemeral=True
        )

    # ── /skill list ──────────────────────────────────────────

    @app_commands.command(name="list", description="列出所有湯技角色")
    async def skill_list(self, interaction: discord.Interaction):
        guild = interaction.guild
        skills = []

        for skill_name, emoji in self._get_skills(guild):
            role = self.skill_service.find_role(guild, skill_name, emoji)
            member_count = len(role.members) if role else 0
            prefix = f"{emoji} " if emoji else ""
            skills.append(f"• {prefix}**{skill_name}** — {member_count} 位成員")

        if not skills:
            await interaction.response.send_message("目前沒有任何湯技。", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎯 湯技列表",
            description="\n".join(skills),
            color=discord.Color.blue(),
        )
        await interaction.response.send_message(embed=embed)

    # ── /skill setup ─────────────────────────────────────────

    @app_commands.command(name="setup", description="為既有的湯技角色補建分類和頻道")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def skill_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        results = []

        for cat in guild.categories:
            if not cat.name.startswith(SKILL_PREFIX):
                continue

            skill_display = cat.name.removeprefix(SKILL_PREFIX)
            parts = skill_display.strip().split(" ", 1)
            skill_name = parts[0].strip()
            skill_emoji = parts[1].strip() if len(parts) > 1 else None
            added = []

            role = self.skill_service.find_role(guild, skill_name, skill_emoji)
            if role:
                await self._apply_skill_permissions(
                    cat,
                    role,
                    reason=f"Skill setup permission sync by {interaction.user}",
                )
                if not self.skill_service.get_invite_code(guild.id, skill_name):
                    new_code = self.skill_service.set_invite_code(guild.id, skill_name)
                    results.append(
                        f"**{skill_display}**：補發邀請碼 `{new_code}`"
                    )
            else:
                results.append(
                    f"**{skill_display}**：找不到對應角色，略過權限同步"
                )

            # Check and create missing discussion/chat channels
            existing_names = [ch.name for ch in cat.channels]
            discussion_name = f"{skill_name}-討論"
            discussion_channel = discord.utils.get(cat.channels, name=discussion_name)
            if not discussion_channel:
                await cat.create_forum(discussion_name)
                added.append(f"{discussion_name}（論壇）")
            elif isinstance(discussion_channel, discord.TextChannel):
                legacy_name = f"{discussion_name}-舊文字"
                if legacy_name in existing_names:
                    legacy_name = f"{discussion_name}-legacy"
                await discussion_channel.edit(
                    name=legacy_name,
                    reason=f"Skill setup migrate forum by {interaction.user}",
                )
                await cat.create_forum(discussion_name)
                added.append(f"{discussion_name}（論壇，已保留舊頻道 #{legacy_name}）")
            if f"{skill_name}-聊天" not in existing_names:
                await cat.create_text_channel(f"{skill_name}-聊天")
                added.append(f"#{skill_name}-聊天")

            # Check and create missing voice trigger
            has_voice_trigger = any(
                ch.name == AUTO_VOICE_TRIGGER for ch in cat.voice_channels
            )
            if not has_voice_trigger:
                await cat.create_voice_channel(AUTO_VOICE_TRIGGER)
                added.append(AUTO_VOICE_TRIGGER)

            if added:
                results.append(f"**{skill_display}**：{', '.join(added)}")

        if results:
            await interaction.followup.send(
                "✅ 已補建以下頻道：\n" + "\n".join(f"　{r}" for r in results)
            )
        else:
            await interaction.followup.send("✅ 所有湯技的頻道都已齊全，無需補建。")

    # ── /skill panel ─────────────────────────────────────────

    @app_commands.command(name="panel", description="發送湯技選擇面板（依環境變數套用可直接加入）")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def skill_panel(self, interaction: discord.Interaction):
        guild = interaction.guild
        skills = self._get_skills(guild)

        if not skills:
            await interaction.response.send_message(
                "❌ 目前沒有任何湯技，請先使用 `/skill create` 建立。", ephemeral=True
            )
            return

        skill_lookup = {name: emoji for name, emoji in skills}
        configured_direct_join = [
            name for name in SKILL_PANEL_DIRECT_JOIN_SKILLS if name in skill_lookup
        ]
        panel_skills = [(name, skill_lookup[name]) for name in configured_direct_join]
        requested_direct_join = set(configured_direct_join)
        if not panel_skills:
            await interaction.response.send_message(
                "❌ `SKILL_PANEL_DIRECT_JOIN_SKILLS` 沒有對應到任何現有湯技，請先確認 .env 設定。",
                ephemeral=True,
            )
            return

        direct_join_hint = (
            "可直接按鈕加入："
            + "、".join(f"**{name}**" for name in configured_direct_join)
            if requested_direct_join
            else "加入請使用 `/skill join` + 邀請碼；按鈕可快速離開。"
        )

        embed = discord.Embed(
            title="🎯 選擇你的湯技",
            description=direct_join_hint
            + "\n\n"
            + "\n".join(
                f"{'　' + emoji + ' ' if emoji else '　'} **{name}**"
                + ("（按鈕可直接加入）" if name in requested_direct_join else "")
                for name, emoji in panel_skills
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(
            text=(
                "指定湯技可直接按鈕加入；其餘維持邀請碼加入。"
                if requested_direct_join
                else "加入需邀請碼；按鈕可快速離開已加入湯技"
            )
        )

        view = SkillPanelView(
            self.skill_service,
            panel_skills,
            direct_join_skills=requested_direct_join,
        )
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ 湯技面板已發送！", ephemeral=True)

    # ── Error handlers ───────────────────────────────────────

    @skill_create.error
    @skill_delete.error
    @skill_info.error
    @skill_regen.error
    @skill_setup.error
    @skill_panel.error
    async def permission_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            if interaction.response.is_done():
                await interaction.followup.send("🚫 你需要「管理角色」權限才能使用此指令。", ephemeral=True)
            else:
                await interaction.response.send_message("🚫 你需要「管理角色」權限才能使用此指令。", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SkillCommands(bot))

