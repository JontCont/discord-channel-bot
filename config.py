import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Guild ID for instant slash command sync (optional, recommended for dev)
GUILD_ID = os.getenv("GUILD_ID", "")

# Auto-voice settings
AUTO_VOICE_TRIGGER = os.getenv("AUTO_VOICE_TRIGGER", "➕ 建立語音頻道")
AUTO_VOICE_SUFFIX = os.getenv("AUTO_VOICE_SUFFIX", "語音房")
AUTO_VOICE_LIMIT = int(os.getenv("AUTO_VOICE_LIMIT", "6"))

# Private room settings
PRIVATE_CATEGORY = os.getenv("PRIVATE_CATEGORY", "🔒 私人湯")
PRIVATE_TRIGGER = os.getenv("PRIVATE_TRIGGER", "➕ 開設私人包廂")
PRIVATE_SUFFIX = os.getenv("PRIVATE_SUFFIX", "的包廂")
PRIVATE_LIMIT = int(os.getenv("PRIVATE_LIMIT", "4"))
PASSWORD_CHANNEL = os.getenv("PASSWORD_CHANNEL", "🔑｜輸入密碼")

# Skill settings
SKILL_PREFIX = os.getenv("SKILL_PREFIX", "湯技：")
SKILL_PANEL_CHANNEL = os.getenv("SKILL_PANEL_CHANNEL", "湯技")

# Leveling settings
LEVELING_DB_PATH = os.getenv("LEVELING_DB_PATH", "data/leveling.db")
XP_PER_MESSAGE_MIN = int(os.getenv("XP_PER_MESSAGE_MIN", "15"))
XP_PER_MESSAGE_MAX = int(os.getenv("XP_PER_MESSAGE_MAX", "25"))
XP_MESSAGE_COOLDOWN = int(os.getenv("XP_MESSAGE_COOLDOWN", "60"))
XP_PER_VOICE_TICK = int(os.getenv("XP_PER_VOICE_TICK", "10"))
XP_VOICE_INTERVAL = int(os.getenv("XP_VOICE_INTERVAL", "300"))
XP_DAILY_BASE = int(os.getenv("XP_DAILY_BASE", "50"))
LEVELUP_CHANNEL = os.getenv("LEVELUP_CHANNEL", "等級公告")

# Level milestones: (level, role_name, color_hex)
_DEFAULT_LEVEL_ROLES = [
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
