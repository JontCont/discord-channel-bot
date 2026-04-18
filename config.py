import os
from dotenv import load_dotenv

load_dotenv()


def _is_english(lang: str) -> bool:
    normalized = (lang or "").lower()
    return normalized.startswith("en")


def _pick_by_language(lang: str, zh_text: str, en_text: str) -> str:
    return en_text if _is_english(lang) else zh_text


def _get_localized_env(key: str, lang: str, zh_default: str, en_default: str) -> str:
    value = os.getenv(key)
    if value is None or value == "":
        return _pick_by_language(lang, zh_default, en_default)
    return value


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# i18n settings
# Supported examples: zh-TW, zh-CN, en-US, en
BOT_LANGUAGE = os.getenv("BOT_LANGUAGE", "zh-TW")

# Guild ID for instant slash command sync (optional, recommended for dev)
GUILD_ID = os.getenv("GUILD_ID", "")

# Auto-voice settings
AUTO_VOICE_TRIGGER = _get_localized_env(
    "AUTO_VOICE_TRIGGER",
    BOT_LANGUAGE,
    "➕ 建立語音頻道",
    "➕ Create Voice Channel",
)
AUTO_VOICE_SUFFIX = _get_localized_env(
    "AUTO_VOICE_SUFFIX",
    BOT_LANGUAGE,
    "語音房",
    "Voice Room",
)
AUTO_VOICE_LIMIT = int(os.getenv("AUTO_VOICE_LIMIT", "6"))

# Private room settings
PRIVATE_CATEGORY = _get_localized_env(
    "PRIVATE_CATEGORY",
    BOT_LANGUAGE,
    "🔒 私人湯",
    "🔒 Private Rooms",
)
PRIVATE_TRIGGER = _get_localized_env(
    "PRIVATE_TRIGGER",
    BOT_LANGUAGE,
    "➕ 開設私人包廂",
    "➕ Create Private Room",
)
PRIVATE_SUFFIX = _get_localized_env(
    "PRIVATE_SUFFIX",
    BOT_LANGUAGE,
    "的包廂",
    "'s Room",
)
PRIVATE_LIMIT = int(os.getenv("PRIVATE_LIMIT", "4"))
PASSWORD_CHANNEL = _get_localized_env(
    "PASSWORD_CHANNEL",
    BOT_LANGUAGE,
    "🔑｜輸入密碼",
    "🔑-password",
)

# Skill settings
SKILL_PREFIX = _get_localized_env(
    "SKILL_PREFIX",
    BOT_LANGUAGE,
    "湯技：",
    "Skill: ",
)
SKILL_PANEL_CHANNEL = _get_localized_env(
    "SKILL_PANEL_CHANNEL",
    BOT_LANGUAGE,
    "湯技",
    "skills",
)


def _parse_name_list(raw: str) -> list[str]:
    import re

    parsed: list[str] = []
    for part in re.split(r"[,，、]", raw):
        name = part.strip()
        if name and name not in parsed:
            parsed.append(name)
    return parsed


SKILL_PANEL_DIRECT_JOIN_SKILLS = _parse_name_list(
    os.getenv(
        "SKILL_PANEL_DIRECT_JOIN_SKILLS",
        "鍛造術,遊戲術,墨繪術,幻想術",
    )
)

# Leveling settings
LEVELING_DB_PATH = os.getenv("LEVELING_DB_PATH", "data/leveling.db")
XP_PER_MESSAGE_MIN = int(os.getenv("XP_PER_MESSAGE_MIN", "15"))
XP_PER_MESSAGE_MAX = int(os.getenv("XP_PER_MESSAGE_MAX", "25"))
XP_MESSAGE_COOLDOWN = int(os.getenv("XP_MESSAGE_COOLDOWN", "60"))
XP_PER_VOICE_TICK = int(os.getenv("XP_PER_VOICE_TICK", "10"))
XP_VOICE_INTERVAL = int(os.getenv("XP_VOICE_INTERVAL", "300"))
XP_DAILY_BASE = int(os.getenv("XP_DAILY_BASE", "50"))
LEVELUP_CHANNEL = _get_localized_env(
    "LEVELUP_CHANNEL",
    BOT_LANGUAGE,
    "等級公告",
    "level-up",
)

# Level milestones: (level, role_name, color_hex)
_DEFAULT_LEVEL_ROLES_ZH = [
    (1,  "🌱 湯友 LV1 新手湯友",  0x95A5A6),
    (5,  "🍵 湯友 LV5 泡湯常客",  0x3498DB),
    (10, "♨️ 湯友 LV10 溫泉達人", 0x2ECC71),
    (15, "🔥 湯友 LV15 熱湯勇者", 0xE67E22),
    (20, "💎 湯友 LV20 湯中豪傑", 0x9B59B6),
    (25, "⚡ 湯友 LV25 傳說湯師", 0xF1C40F),
    (30, "🌟 湯友 LV30 湯界名人", 0xE74C3C),
    (35, "👑 湯友 LV35 湯池霸主", 0x1ABC9C),
    (40, "🐉 湯友 LV40 神湯使者", 0xE91E63),
    (50, "🏆 湯友 LV50 湯神",     0xFFD700),
]

_DEFAULT_LEVEL_ROLES_EN = [
    (1,  "🌱 Soaker LV1 Beginner",     0x95A5A6),
    (5,  "🍵 Soaker LV5 Regular",      0x3498DB),
    (10, "♨️ Soaker LV10 Hot Spring Pro", 0x2ECC71),
    (15, "🔥 Soaker LV15 Brave Bather", 0xE67E22),
    (20, "💎 Soaker LV20 Elite",        0x9B59B6),
    (25, "⚡ Soaker LV25 Legend",       0xF1C40F),
    (30, "🌟 Soaker LV30 Celebrity",    0xE74C3C),
    (35, "👑 Soaker LV35 Overlord",     0x1ABC9C),
    (40, "🐉 Soaker LV40 Spirit Envoy", 0xE91E63),
    (50, "🏆 Soaker LV50 Bath Deity",   0xFFD700),
]

_DEFAULT_LEVEL_ROLES = (
    _DEFAULT_LEVEL_ROLES_EN if _is_english(BOT_LANGUAGE) else _DEFAULT_LEVEL_ROLES_ZH
)


def _parse_level_roles(raw: str | None) -> list[tuple[int, str, int]]:
    """Parse LEVEL_ROLES from env: [lv,"name","#COLOR"],[lv,"name","#COLOR"],..."""
    if not raw:
        return _DEFAULT_LEVEL_ROLES
    import re
    roles = []
    for m in re.finditer(r'\[(\d+)\s*,\s*"([^"]+)"\s*,\s*"#([0-9A-Fa-f]{6})"\]', raw):
        roles.append((int(m.group(1)), m.group(2), int(m.group(3), 16)))
    return roles if roles else _DEFAULT_LEVEL_ROLES


LEVEL_ROLES = _parse_level_roles(os.getenv("LEVEL_ROLES"))
