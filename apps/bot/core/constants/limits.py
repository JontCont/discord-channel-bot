"""
Validation and Boundary Constants.

官方依據: PEP 591 (Final Typing) & PEP 586.
存放系統驗證邊界、字符長度上限與數值邊界，確保跨模組引用時不可被篡改。
"""
from typing import Final

# Discord Embed 與面板文字長度限制
PANEL_TEXT_LIMITS: Final[dict[str, int]] = {
    "party_panel_title": 256,
    "party_panel_description": 4096,
    "party_panel_create_heading": 256,
    "party_panel_create_description": 1024,
    "party_panel_list_heading": 256,
    "party_panel_list_description": 1024,
    "party_panel_create_label": 80,
    "party_panel_list_label": 80,
    "skill_panel_title": 256,
    "skill_panel_description": 4096,
    "skill_panel_footer": 2048,
}

# 數值型設定欄位的允許區間 (min, max)；None 表示無上限
INTEGER_RANGES: Final[dict[str, tuple[int, int | None]]] = {
    "auto_voice_limit": (0, 99),
    "private_limit": (0, 99),
    "xp_per_message_min": (0, None),
    "xp_per_message_max": (0, None),
    "xp_message_cooldown": (0, None),
    "xp_per_voice_tick": (0, None),
    "xp_voice_interval": (1, None),
    "xp_daily_base": (0, None),
}

# 必填字串欄位
REQUIRED_STRING_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "auto_voice_trigger",
        "auto_voice_suffix",
        "private_category",
        "private_trigger",
        "private_suffix",
        "password_channel",
        "skill_prefix",
        "skill_panel_channel",
        "party_notification_channel",
        "levelup_channel",
    }
)

# 布林值開關欄位
BOOLEAN_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "auto_voice_enabled",
        "private_rooms_enabled",
        "skills_enabled",
        "party_enabled",
        "leveling_enabled",
    }
)
