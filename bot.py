import asyncio
import logging
import discord
from discord.ext import commands

from config import DISCORD_TOKEN, BOT_PREFIX, GUILD_ID, AUTO_VOICE_TRIGGER, PRIVATE_TRIGGER

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bot")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

COGS = [
    "cogs.prefix.general",
    "cogs.slash.embeds",
    "cogs.slash.slash_commands",
    "cogs.slash.auto_voice",
    "cogs.slash.private_room",
    "cogs.slash.skill_commands",
    "cogs.slash.leveling",
]


def _validate_config():
    """Fail fast if configurable trigger names collide."""
    if AUTO_VOICE_TRIGGER == PRIVATE_TRIGGER:
        raise ValueError(
            f"AUTO_VOICE_TRIGGER and PRIVATE_TRIGGER must differ, "
            f"both are set to '{AUTO_VOICE_TRIGGER}'"
        )


@bot.event
async def on_ready():
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
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ 缺少參數: `{error.param.name}`")
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 你沒有權限執行此指令。")
        return
    logger.error("Unhandled error in command %s: %s", ctx.command, error)
    await ctx.send("❌ 發生未預期的錯誤，請稍後再試。")


async def main():
    _validate_config()
    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                logger.info("Loaded cog: %s", cog)
            except Exception:
                logger.exception("Failed to load cog: %s", cog)
        await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
