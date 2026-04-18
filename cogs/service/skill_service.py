import secrets

import discord

from config import AUTO_VOICE_TRIGGER, SKILL_PREFIX
from cogs.repository.skill_invite_repository import SkillInviteRepository


class SkillService:
    """Business layer: skill domain rules and operations."""

    def __init__(self, repo: SkillInviteRepository):
        self.repo = repo

    @staticmethod
    def find_role(
        guild: discord.Guild, name: str, emoji: str | None = None
    ) -> discord.Role | None:
        name = name.strip()
        candidates = {name, f"{SKILL_PREFIX}{name}"}
        if emoji:
            candidates.add(f"{name} {emoji}")
            candidates.add(f"{SKILL_PREFIX}{name} {emoji}")

        for role in guild.roles:
            if role.name.strip() in candidates:
                return role
        return None

    @staticmethod
    def find_category(guild: discord.Guild, name: str) -> discord.CategoryChannel | None:
        target = f"{SKILL_PREFIX}{name}"
        for cat in guild.categories:
            if cat.name.startswith(target):
                return cat
        return None

    @staticmethod
    def skill_category_name(name: str, emoji: str | None = None) -> str:
        if emoji:
            return f"{SKILL_PREFIX}{name} {emoji}"
        return f"{SKILL_PREFIX}{name}"

    @staticmethod
    def get_skills(guild: discord.Guild) -> list[tuple[str, str | None]]:
        skills = []
        for cat in guild.categories:
            if cat.name.startswith(SKILL_PREFIX):
                rest = cat.name.removeprefix(SKILL_PREFIX).strip()
                parts = rest.split(" ", 1)
                skill_name = parts[0].strip()
                emoji = parts[1].strip() if len(parts) > 1 else None
                skills.append((skill_name, emoji))
        return skills

    def build_panel_embed(
        self, skills: list[tuple[str, str | None]], guild: discord.Guild
    ) -> discord.Embed:
        lines = []
        for name, emoji in skills:
            role = self.find_role(guild, name)
            count = len(role.members) if role else 0
            prefix = f"{emoji} " if emoji else ""
            lines.append(f"{prefix}**{name}** — {count} 位成員")

        embed = discord.Embed(
            title="🎯 選擇你的湯技",
            description=(
                "加入：請使用 `/skill join` + 邀請碼\n"
                "離開：可直接點下方按鈕\n\n" + "\n".join(lines)
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="加入需邀請碼；按鈕可快速離開已加入湯技")
        return embed

    @staticmethod
    def skill_overwrites(guild: discord.Guild, role: discord.Role) -> dict:
        role_overwrite = discord.PermissionOverwrite(
            view_channel=True,
            read_message_history=True,
            send_messages=True,
            send_messages_in_threads=True,
            create_public_threads=True,
            create_private_threads=True,
            add_reactions=True,
            embed_links=True,
            attach_files=True,
            use_external_emojis=True,
            use_application_commands=True,
            connect=True,
            speak=True,
            stream=True,
            use_voice_activation=True,
        )
        if hasattr(discord.Permissions, "use_external_stickers"):
            role_overwrite.use_external_stickers = True
        if hasattr(discord.Permissions, "send_polls"):
            role_overwrite.send_polls = True
        if hasattr(discord.Permissions, "create_polls"):
            role_overwrite.create_polls = True
        if hasattr(discord.Permissions, "use_embedded_activities"):
            role_overwrite.use_embedded_activities = True
        if hasattr(discord.Permissions, "start_embedded_activities"):
            role_overwrite.start_embedded_activities = True

        return {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=False,
                connect=False,
            ),
            role: role_overwrite,
        }

    async def apply_skill_permissions(
        self,
        category: discord.CategoryChannel,
        role: discord.Role,
        reason: str,
    ):
        overwrites = self.skill_overwrites(category.guild, role)
        await category.edit(overwrites=overwrites, reason=reason)
        for channel in category.channels:
            await channel.edit(sync_permissions=True, reason=reason)

    def get_invite_code(self, guild_id: int, skill_name: str) -> str | None:
        return self.repo.get(guild_id, skill_name)

    def delete_invite_code(self, guild_id: int, skill_name: str):
        self.repo.delete(guild_id, skill_name)

    def generate_unique_code(self, guild_id: int, length: int = 8) -> str:
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        used = self.repo.codes_for_guild(guild_id)
        for _ in range(100):
            code = "".join(secrets.choice(alphabet) for _ in range(length))
            if code not in used:
                return code
        raise RuntimeError("Failed to generate a unique invite code")

    def set_invite_code(self, guild_id: int, skill_name: str, code: str | None = None) -> str:
        final_code = (code or self.generate_unique_code(guild_id)).upper().strip()
        self.repo.set(guild_id, skill_name, final_code)
        return final_code

    def ensure_invite_code(self, guild_id: int, skill_name: str) -> str:
        code = self.get_invite_code(guild_id, skill_name)
        if code:
            return code
        return self.set_invite_code(guild_id, skill_name)

    def find_skill_by_code(self, guild: discord.Guild, code: str) -> tuple[str, discord.Role] | None:
        target = code.strip().upper()
        for name, _emoji in self.get_skills(guild):
            role = self.find_role(guild, name)
            if not role:
                continue
            if self.get_invite_code(guild.id, name) == target:
                return name, role
        return None

    @property
    def auto_voice_trigger(self) -> str:
        return AUTO_VOICE_TRIGGER
