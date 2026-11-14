from dataclasses import fields
from typing import Any, Mapping

from repository.guild_settings_db import GuildSettingsDB
from core.constants.limits import (
    BOOLEAN_FIELDS,
    INTEGER_RANGES,
    PANEL_TEXT_LIMITS,
    REQUIRED_STRING_FIELDS,
)
from models.guild_settings import GuildSettings


class GuildSettingsService:
    PANEL_TEXT_LIMITS = PANEL_TEXT_LIMITS
    _FIELD_NAMES = frozenset(field.name for field in fields(GuildSettings))
    _BOOLEAN_NAMES = BOOLEAN_FIELDS
    _REQUIRED_NAMES = REQUIRED_STRING_FIELDS
    _INTEGER_RANGES = INTEGER_RANGES

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
        normalized = dict(values)
        normalized.pop("party_skill", None)
        normalized.pop("party_category", None)

        unknown = set(normalized) - cls._FIELD_NAMES
        if unknown:
            names = ", ".join(sorted(str(key) for key in unknown))
            raise ValueError(f"unknown setting keys: {names}")

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
        """主校驗入口：依據領域責任拆分各項獨立校驗。"""
        cls._validate_panel_texts(settings)
        cls._validate_booleans(settings)
        cls._validate_required_strings(settings)
        cls._validate_triggers(settings)
        cls._validate_integers(settings)
        cls._validate_xp_settings(settings)

    @classmethod
    def _validate_panel_texts(cls, settings: GuildSettings) -> None:
        """校驗所有面板文字長度限制與總字數約束。"""
        for name, maximum in cls.PANEL_TEXT_LIMITS.items():
            value = getattr(settings, name)
            if not isinstance(value, str) or (name != "skill_panel_footer" and not value.strip()):
                raise ValueError(f"{name} must be a non-empty string")
            if len(value) > maximum:
                raise ValueError(f"{name} must not exceed {maximum} characters")

        party_text = (
            settings.party_panel_title,
            settings.party_panel_description,
            settings.party_panel_create_heading,
            settings.party_panel_create_description,
            settings.party_panel_list_heading,
            settings.party_panel_list_description,
        )
        if sum(map(len, party_text)) > 6000:
            raise ValueError("room panel text must not exceed 6000 characters in total")

        skill_text = (
            settings.skill_panel_title,
            settings.skill_panel_description,
            settings.skill_panel_footer,
        )
        if sum(map(len, skill_text)) > 6000:
            raise ValueError("skill panel text must not exceed 6000 characters in total")

    @classmethod
    def _validate_booleans(cls, settings: GuildSettings) -> None:
        """校驗布林型態開關。"""
        for name in cls._BOOLEAN_NAMES:
            value = getattr(settings, name)
            if not isinstance(value, bool):
                raise ValueError(f"{name} must be a boolean")

    @classmethod
    def _validate_required_strings(cls, settings: GuildSettings) -> None:
        """校驗必填非空字串欄位。"""
        for name in cls._REQUIRED_NAMES:
            value = getattr(settings, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

    @staticmethod
    def _validate_triggers(settings: GuildSettings) -> None:
        """校驗觸發詞唯一性。"""
        if (
            settings.auto_voice_trigger.strip().casefold()
            == settings.private_trigger.strip().casefold()
        ):
            raise ValueError("auto_voice_trigger and private_trigger must be unique")

    @classmethod
    def _validate_integers(cls, settings: GuildSettings) -> None:
        """校驗整數範圍。"""
        for name, (minimum, maximum) in cls._INTEGER_RANGES.items():
            value = getattr(settings, name)
            if type(value) is not int:
                raise ValueError(f"{name} must be an integer")
            if value < minimum or (maximum is not None and value > maximum):
                upper = f" and at most {maximum}" if maximum is not None else ""
                raise ValueError(f"{name} must be at least {minimum}{upper}")

    @staticmethod
    def _validate_xp_settings(settings: GuildSettings) -> None:
        """校驗經驗值範圍邊界。"""
        if settings.xp_per_message_min > settings.xp_per_message_max:
            raise ValueError("xp_per_message_min must not exceed xp_per_message_max")

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
    def _parse_single_level_role(role: Any) -> tuple[int, str, int]:
        """解析單一等級身分組定義並驗證其屬性型態與邊界。"""
        if not isinstance(role, (list, tuple)) or len(role) != 3:
            raise ValueError("each level role must contain level, name, and color")
        level, role_name, color = role
        if type(level) is not int or level < 1:
            raise ValueError("level role levels must be positive integers")
        if not isinstance(role_name, str) or not role_name.strip():
            raise ValueError("level role names must be non-empty strings")
        if type(color) is not int or not 0 <= color <= 0xFFFFFF:
            raise ValueError("level role colors must be integers from 0 to 0xFFFFFF")
        return (level, role_name.strip(), color)

    @classmethod
    def _validate_level_roles(cls, value: Any) -> tuple[tuple[int, str, int], ...]:
        if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
            raise ValueError("level_roles must be a list of role definitions")
        if not value:
            raise ValueError("level_roles must contain at least one role")

        roles = [cls._parse_single_level_role(role) for role in value]
        levels = [level for level, _, _ in roles]
        names = [name for _, name, _ in roles]
        if len(set(levels)) != len(levels):
            raise ValueError("level role levels must be unique")
        if len(set(names)) != len(names):
            raise ValueError("level role names must be unique")
        if levels != sorted(levels):
            raise ValueError("level roles must be ordered by level")
        return tuple(roles)