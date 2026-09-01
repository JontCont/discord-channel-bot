from dataclasses import asdict, dataclass, fields
from typing import Any, Mapping

import config
from cogs.repository.guild_settings_db import GuildSettingsDB


@dataclass(frozen=True, slots=True)
class GuildSettings:
    auto_voice_trigger: str = config.AUTO_VOICE_TRIGGER
    auto_voice_suffix: str = config.AUTO_VOICE_SUFFIX
    auto_voice_limit: int = config.AUTO_VOICE_LIMIT

    private_category: str = config.PRIVATE_CATEGORY
    private_trigger: str = config.PRIVATE_TRIGGER
    private_suffix: str = config.PRIVATE_SUFFIX
    private_limit: int = config.PRIVATE_LIMIT
    password_channel: str = config.PASSWORD_CHANNEL

    skill_prefix: str = config.SKILL_PREFIX
    skill_panel_channel: str = config.SKILL_PANEL_CHANNEL
    skill_panel_direct_join_skills: tuple[str, ...] = tuple(
        config.SKILL_PANEL_DIRECT_JOIN_SKILLS
    )

    xp_per_message_min: int = config.XP_PER_MESSAGE_MIN
    xp_per_message_max: int = config.XP_PER_MESSAGE_MAX
    xp_message_cooldown: int = config.XP_MESSAGE_COOLDOWN
    xp_per_voice_tick: int = config.XP_PER_VOICE_TICK
    xp_voice_interval: int = config.XP_VOICE_INTERVAL
    xp_daily_base: int = config.XP_DAILY_BASE
    levelup_channel: str = config.LEVELUP_CHANNEL
    level_roles: tuple[tuple[int, str, int], ...] = tuple(config.LEVEL_ROLES)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["skill_panel_direct_join_skills"] = list(
            self.skill_panel_direct_join_skills
        )
        data["level_roles"] = [list(role) for role in self.level_roles]
        return data


class GuildSettingsService:
    _FIELD_NAMES = frozenset(field.name for field in fields(GuildSettings))
    _REQUIRED_NAMES = frozenset(
        {
            "auto_voice_trigger",
            "auto_voice_suffix",
            "private_category",
            "private_trigger",
            "private_suffix",
            "password_channel",
            "skill_prefix",
            "skill_panel_channel",
            "levelup_channel",
        }
    )
    _INTEGER_RANGES = {
        "auto_voice_limit": (0, 99),
        "private_limit": (0, 99),
        "xp_per_message_min": (0, None),
        "xp_per_message_max": (0, None),
        "xp_message_cooldown": (0, None),
        "xp_per_voice_tick": (0, None),
        "xp_voice_interval": (1, None),
        "xp_daily_base": (0, None),
    }

    def __init__(self, db: GuildSettingsDB):
        self._db = db

    async def get(self, guild_id: int) -> GuildSettings:
        self._validate_guild_id(guild_id)
        stored = await self._db.get_all(guild_id)
        return self._build(stored)

    async def update(
        self, guild_id: int, changes: Mapping[str, Any]
    ) -> GuildSettings:
        self._validate_guild_id(guild_id)
        if not isinstance(changes, Mapping):
            raise TypeError("changes must be a mapping")

        unknown = set(changes) - self._FIELD_NAMES
        if unknown:
            names = ", ".join(sorted(str(key) for key in unknown))
            raise ValueError(f"unknown setting keys: {names}")

        current = await self._db.get_all(guild_id)
        merged = {**current, **changes}
        settings = self._build(merged)
        if changes:
            serialized = settings.to_dict()
            await self._db.set_many(
                guild_id, {key: serialized[key] for key in changes}
            )
        return settings

    @classmethod
    def _build(cls, values: Mapping[str, Any]) -> GuildSettings:
        unknown = set(values) - cls._FIELD_NAMES
        if unknown:
            names = ", ".join(sorted(str(key) for key in unknown))
            raise ValueError(f"unknown setting keys: {names}")

        normalized = dict(values)
        if "skill_panel_direct_join_skills" in normalized:
            normalized["skill_panel_direct_join_skills"] = cls._validate_names(
                "skill_panel_direct_join_skills",
                normalized["skill_panel_direct_join_skills"],
            )
        if "level_roles" in normalized:
            normalized["level_roles"] = cls._validate_level_roles(
                normalized["level_roles"]
            )

        settings = GuildSettings(**normalized)
        cls._validate(settings)
        return settings

    @classmethod
    def _validate(cls, settings: GuildSettings) -> None:
        for name in cls._REQUIRED_NAMES:
            value = getattr(settings, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

        if (
            settings.auto_voice_trigger.strip().casefold()
            == settings.private_trigger.strip().casefold()
        ):
            raise ValueError("auto_voice_trigger and private_trigger must be unique")

        for name, (minimum, maximum) in cls._INTEGER_RANGES.items():
            value = getattr(settings, name)
            if type(value) is not int:
                raise ValueError(f"{name} must be an integer")
            if value < minimum or maximum is not None and value > maximum:
                upper = f" and at most {maximum}" if maximum is not None else ""
                raise ValueError(f"{name} must be at least {minimum}{upper}")

        if settings.xp_per_message_min > settings.xp_per_message_max:
            raise ValueError(
                "xp_per_message_min must not exceed xp_per_message_max"
            )

    @staticmethod
    def _validate_guild_id(guild_id: int) -> None:
        if type(guild_id) is not int or guild_id <= 0:
            raise ValueError("guild_id must be a positive integer")

    @staticmethod
    def _validate_names(name: str, value: Any) -> tuple[str, ...]:
        if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
            raise ValueError(f"{name} must be a list of names")
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise ValueError(f"{name} must contain only non-empty names")
        normalized = tuple(item.strip() for item in value)
        if len(set(normalized)) != len(normalized):
            raise ValueError(f"{name} must not contain duplicate names")
        return normalized

    @staticmethod
    def _validate_level_roles(value: Any) -> tuple[tuple[int, str, int], ...]:
        if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
            raise ValueError("level_roles must be a list of role definitions")
        if not value:
            raise ValueError("level_roles must contain at least one role")

        roles: list[tuple[int, str, int]] = []
        for role in value:
            if not isinstance(role, (list, tuple)) or len(role) != 3:
                raise ValueError("each level role must contain level, name, and color")
            level, role_name, color = role
            if type(level) is not int or level < 1:
                raise ValueError("level role levels must be positive integers")
            if not isinstance(role_name, str) or not role_name.strip():
                raise ValueError("level role names must be non-empty strings")
            if type(color) is not int or not 0 <= color <= 0xFFFFFF:
                raise ValueError("level role colors must be integers from 0 to 0xFFFFFF")
            roles.append((level, role_name.strip(), color))

        levels = [level for level, _, _ in roles]
        names = [name for _, name, _ in roles]
        if len(set(levels)) != len(levels):
            raise ValueError("level role levels must be unique")
        if len(set(names)) != len(names):
            raise ValueError("level role names must be unique")
        if levels != sorted(levels):
            raise ValueError("level roles must be ordered by level")
        return tuple(roles)