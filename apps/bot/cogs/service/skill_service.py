import secrets

import discord

from cogs.repository.skill_invite_repository import SkillInviteRepository


class SkillService:
    """Business layer: skill domain rules and operations."""

    def __init__(self, repo: SkillInviteRepository):
        self.repo = repo

    @staticmethod
    def find_role(
        guild: discord.Guild,
        name: str,
        skill_prefix: str,
        emoji: str | None = None,
    ) -> discord.Role | None:
        name = name.strip()
        candidates = {name, f"{skill_prefix}{name}"}
        if emoji:
            candidates.add(f"{name} {emoji}")
            candidates.add(f"{skill_prefix}{name} {emoji}")

        for role in guild.roles:
            if role.name.strip() in candidates:
                return role
        return None

    @staticmethod
    def find_category(
        guild: discord.Guild, name: str, skill_prefix: str
    ) -> discord.CategoryChannel | None:
        target = f"{skill_prefix}{name}"
        for cat in guild.categories:
            if cat.name.startswith(target):
                return cat
        return None

    @staticmethod
    def skill_category_name(
        name: str, skill_prefix: str, emoji: str | None = None
    ) -> str:
        if emoji:
            return f"{skill_prefix}{name} {emoji}"
        return f"{skill_prefix}{name}"

    @staticmethod
    def get_skills(
        guild: discord.Guild, skill_prefix: str
    ) -> list[tuple[str, str | None]]:
        skills = []
        for cat in guild.categories:
            if cat.name.startswith(skill_prefix):
                rest = cat.name.removeprefix(skill_prefix).strip()
                parts = rest.split(" ", 1)
                skill_name = parts[0].strip()
                emoji = parts[1].strip() if len(parts) > 1 else None
                skills.append((skill_name, emoji))
        return skills

    def build_panel_embed(
        self,
        skills: list[tuple[str, str | None]],
        guild: discord.Guild,
        skill_prefix: str,
        direct_join_skills: tuple[str, ...],
    ) -> discord.Embed:
        lines = []
        for name, emoji in skills:
            role = self.find_role(guild, name, skill_prefix, emoji)
            count = len(role.members) if role else 0
            prefix = f"{emoji} " if emoji else ""
            join_hint = "（按鈕可直接加入）" if name in direct_join_skills else "（需邀請碼）"
            lines.append(f"{prefix}**{name}** — {count} 位成員 {join_hint}")

        embed = discord.Embed(
            title="🎯 選擇你的湯技",
            description=(
                "點擊下方按鈕即可快速加入或離開對應的湯技！\n\n"
                + "\n".join(lines)
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="💡 指定湯技可直接加入；其餘請使用邀請碼。按鈕皆可離開")
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
                view_channel=False,
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

    def find_skill_by_code(
        self, guild: discord.Guild, code: str, skill_prefix: str
    ) -> tuple[str, discord.Role] | None:
        target = code.strip().upper()
        for name, emoji in self.get_skills(guild, skill_prefix):
            role = self.find_role(guild, name, skill_prefix, emoji)
            if not role:
                continue
            if self.get_invite_code(guild.id, name) == target:
                return name, role
        return None
