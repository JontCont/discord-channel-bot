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
