import discord
from discord import app_commands
from discord.ext import commands

from config import AUTO_VOICE_TRIGGER

SKILL_PREFIX = "湯技："
SKILL_PANEL_CHANNEL = "湯技"


class SkillToggleButton(discord.ui.Button):
    """A single skill toggle button."""

    def __init__(self, skill_name: str, emoji: str | None = None):
        super().__init__(
            label=skill_name,
            emoji=emoji,
            style=discord.ButtonStyle.secondary,
            custom_id=f"skill_toggle:{skill_name}",
        )
        self.skill_name = skill_name

    async def callback(self, interaction: discord.Interaction):
        # Check both plain name and prefixed name
        role = discord.utils.get(interaction.guild.roles, name=self.skill_name)
        if not role:
            role = discord.utils.get(
                interaction.guild.roles, name=f"{SKILL_PREFIX}{self.skill_name}"
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
        else:
            await interaction.user.add_roles(role, reason="Skill panel toggle")
            await interaction.response.send_message(
                f"✅ 你已加入湯技 **{self.skill_name}**", ephemeral=True
            )


class SkillPanelView(discord.ui.View):
    """Persistent view containing skill toggle buttons."""

    def __init__(self, skills: list[tuple[str, str | None]]):
        super().__init__(timeout=None)
        for skill_name, emoji in skills:
            self.add_item(SkillToggleButton(skill_name, emoji))


class SkillCommands(commands.GroupCog, name="skill"):
    """湯技管理模組 — 建立/刪除/加入/離開湯技角色與頻道"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # guild_id -> message_id of the panel
        self._panel_messages: dict[int, int] = {}
        super().__init__()

    def _get_skills(self, guild: discord.Guild) -> list[tuple[str, str | None]]:
        """Return list of (skill_name, emoji) from categories."""
        skills = []
        for cat in guild.categories:
            if cat.name.startswith(SKILL_PREFIX):
                rest = cat.name.removeprefix(SKILL_PREFIX)
                parts = rest.split(" ", 1)
                skill_name = parts[0]
                emoji = parts[1].strip() if len(parts) > 1 else None
                skills.append((skill_name, emoji))
        return skills

    def _build_panel_embed(
        self, skills: list[tuple[str, str | None]], guild: discord.Guild
    ) -> discord.Embed:
        lines = []
        for name, emoji in skills:
            role = self._find_role(guild, name)
            count = len(role.members) if role else 0
            prefix = f"{emoji} " if emoji else ""
            lines.append(f"{prefix}**{name}** — {count} 位成員")

        embed = discord.Embed(
            title="🎯 選擇你的湯技",
            description=(
                "點擊下方按鈕加入或離開湯技角色\n"
                "再點一次即可切換\n\n" + "\n".join(lines)
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="點擊按鈕即可加入/離開對應湯技")
        return embed

    async def _refresh_panel(self, guild: discord.Guild):
        """Update or create the skill panel in #湯技 channel."""
        channel = discord.utils.get(guild.text_channels, name=SKILL_PANEL_CHANNEL)
        if not channel:
            return

        skills = self._get_skills(guild)
        if not skills:
            return

        embed = self._build_panel_embed(skills, guild)
        view = SkillPanelView(skills)
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
                self.bot.add_view(SkillPanelView(skills))
            await self._refresh_panel(guild)

    # ── helpers ──────────────────────────────────────────────

    @staticmethod
    def _skill_category_name(name: str, emoji: str | None = None) -> str:
        if emoji:
            return f"{SKILL_PREFIX}{name} {emoji}"
        return f"{SKILL_PREFIX}{name}"

    @staticmethod
    def _find_category(guild: discord.Guild, name: str) -> discord.CategoryChannel | None:
        """Find a category whose name starts with the skill prefix + name."""
        target = f"{SKILL_PREFIX}{name}"
        for cat in guild.categories:
            if cat.name.startswith(target):
                return cat
        return None

    @staticmethod
    def _find_role(guild: discord.Guild, name: str) -> discord.Role | None:
        """Find role by name, checking both plain and prefixed formats."""
        for role in guild.roles:
            if role.name == name or role.name == f"{SKILL_PREFIX}{name}":
                return role
        return None

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
        role = await guild.create_role(
            name=name,
            mentionable=True,
            reason=f"Skill create by {interaction.user}",
        )

        # 2. Create category with permission overrides
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=True),
            role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        category_name = self._skill_category_name(name, emoji)
        category = await guild.create_category(
            name=category_name,
            overwrites=overwrites,
            reason=f"Skill create by {interaction.user}",
        )

        # 3. Create text channels
        await category.create_text_channel(f"{name}-討論")
        await category.create_text_channel(f"{name}-聊天")

        # 4. Create voice trigger channel
        await category.create_voice_channel(AUTO_VOICE_TRIGGER)

        await interaction.followup.send(
            f"✅ 湯技 **{name}** 已建立！\n"
            f"　• 角色：{role.mention}\n"
            f"　• 分類：{category_name}\n"
            f"　• 頻道：#{name}-討論、#{name}-聊天\n"
            f"　• 語音：{AUTO_VOICE_TRIGGER}"
        )
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

        await interaction.followup.send(f"✅ 湯技 **{name}** 已刪除（角色 + 分類 + 所有頻道）。")
        await self._refresh_panel(guild)

    # ── /skill join ──────────────────────────────────────────

    @app_commands.command(name="join", description="加入湯技角色")
    @app_commands.describe(name="湯技名稱")
    @app_commands.autocomplete(name=_skill_autocomplete)
    async def skill_join(self, interaction: discord.Interaction, name: str):
        guild = interaction.guild
        role = self._find_role(guild, name)

        if not role:
            await interaction.response.send_message(
                f"❌ 找不到湯技角色 **{name}**。", ephemeral=True
            )
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(
                f"⚠️ 你已經擁有 **{name}** 角色了。", ephemeral=True
            )
            return

        await interaction.user.add_roles(role, reason="Skill join")
        await interaction.response.send_message(
            f"✅ 你已加入湯技 **{name}**！", ephemeral=True
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

        for cat in guild.categories:
            if cat.name.startswith(SKILL_PREFIX):
                skill_display = cat.name.removeprefix(SKILL_PREFIX)
                skill_name = skill_display.split(" ")[0]
                role = self._find_role(guild, skill_name)
                member_count = len(role.members) if role else 0
                skills.append(f"• **{skill_display}** — {member_count} 位成員")

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
            skill_name = skill_display.split(" ")[0]
            added = []

            # Check and create missing text channels
            existing_names = [ch.name for ch in cat.channels]
            if f"{skill_name}-討論" not in existing_names:
                await cat.create_text_channel(f"{skill_name}-討論")
                added.append(f"#{skill_name}-討論")
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

    @app_commands.command(name="panel", description="發送湯技選擇面板（按鈕加入/離開）")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def skill_panel(self, interaction: discord.Interaction):
        guild = interaction.guild
        skills = self._get_skills(guild)

        if not skills:
            await interaction.response.send_message(
                "❌ 目前沒有任何湯技，請先使用 `/skill create` 建立。", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🎯 選擇你的湯技",
            description="點擊按鈕加入或離開湯技角色，再點一次即可切換。\n\n"
            + "\n".join(
                f"{'　' + emoji + ' ' if emoji else '　'} **{name}**"
                for name, emoji in skills
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="點擊按鈕即可加入/離開對應湯技")

        view = SkillPanelView(skills)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ 湯技面板已發送！", ephemeral=True)

    # ── Error handlers ───────────────────────────────────────

    @skill_create.error
    @skill_delete.error
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
