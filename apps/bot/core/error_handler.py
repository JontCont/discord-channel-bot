"""
Global Error Handling Pipeline.

官方依據: Discord.py Error Handling Guide.
集中處理 Discord 指令例外與全域未捕捉異常，防止伺服器靜默崩潰並回饋適當錯誤提示。
"""
import logging
from discord.ext import commands

logger = logging.getLogger("core.error_handler")


async def handle_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    """處理 Discord 前綴指令發生的例外。

    Args:
        ctx: 指令執行上下文。
        error: 拋出之例外物件。
    """
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ 缺少必要參數: `{error.param.name}`")
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 你沒有權限執行此指令。")
        return

    logger.error("Unhandled error in command '%s': %s", ctx.command, error, exc_info=error)
    await ctx.send("❌ 發生未預期的錯誤，請稍後再試。")
