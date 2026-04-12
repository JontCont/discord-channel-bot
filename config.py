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
