"""
Bot Bootstrap & Composition Root.

官方依據: PEP 8, PEP 257 & Clean Architecture (Robert C. Martin).
負責系統生命週期初始化、裝配 DI 容器、啟動 API 與 Discord Bot。
"""
import asyncio
import logging
import discord
import uvicorn
from discord.ext import commands

from api import create_api
from config import (
    API_HOST,
    API_PORT,
    AUTO_VOICE_TRIGGER,
    BOT_PREFIX,
    DISCORD_TOKEN,
    DYNAMIC_VOICE_CREATE_ENABLED,
    DYNAMIC_VOICE_DELETE_ENABLED,
    GUILD_ID,
    PRIVATE_TRIGGER,
)
from core.container import ServiceContainer
from core.error_handler import handle_command_error
from core.logging import setup_logging

setup_logging()
logger = logging.getLogger("bot")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=BOT_PREFIX,
    intents=intents,
    help_command=None,
)

COGS = [
    "cogs.prefix.general",
    "cogs.slash.embeds",
    "cogs.slash.slash_commands",
    "cogs.slash.introduction",
    "cogs.slash.auto_voice",
    "cogs.slash.private_room",
    "cogs.slash.skill_commands",
    "cogs.slash.party",
    "cogs.slash.leveling",
    "cogs.slash.help",
]


def _validate_config() -> None:
    """Fail fast if configurable trigger names collide."""
    if AUTO_VOICE_TRIGGER == PRIVATE_TRIGGER:
        raise ValueError(
            f"AUTO_VOICE_TRIGGER and PRIVATE_TRIGGER must differ, "
            f"both are set to '{AUTO_VOICE_TRIGGER}'"
        )


@bot.event
async def on_ready() -> None:
    """Discord Gateway 連線就緒事件。"""
    logger.info("Bot is online as %s (ID: %s)", bot.user, bot.user.id)
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            logger.info("Synced %d slash command(s) to guild %s", len(synced), GUILD_ID)
        else:
            synced = await bot.tree.sync()
            logger.info("Synced %d slash command(s) globally", len(synced))
    except Exception:
        logger.exception("Failed to sync slash commands")


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    """委派給核心錯誤處理管線。"""
    await handle_command_error(ctx, error)


async def main() -> None:
    """應用程式 Composition Root 進入點。"""
    _validate_config()
    logger.info(
        "Dynamic voice operations: create=%s, delete=%s",
        DYNAMIC_VOICE_CREATE_ENABLED,
        DYNAMIC_VOICE_DELETE_ENABLED,
    )

    # 1. 裝配與初始化 DI 容器 (Composition Root)
    container = ServiceContainer.create()
    await container.init()

    # 綁定至 bot 物件供 Cogs 與表現層存取
    bot.container = container
    bot.guild_settings_service = container.guild_settings_service

    # 2. 建立並啟動 FastAPI 管理後台
    api = create_api(bot.guild_settings_service, bot)
    api_server = uvicorn.Server(
        uvicorn.Config(api, host=API_HOST, port=API_PORT, log_level="info")
    )
    api_task = asyncio.create_task(api_server.serve())

    # 3. 載入 Discord Cogs 並啟動 Bot
    async with bot:
        try:
            for cog in COGS:
                try:
                    await bot.load_extension(cog)
                    logger.info("Loaded cog: %s", cog)
                except Exception:
                    logger.exception("Failed to load cog: %s", cog)
            await bot.start(DISCORD_TOKEN)
        finally:
            api_server.should_exit = True
            await api_task
            await container.close()


if __name__ == "__main__":
    asyncio.run(main())
