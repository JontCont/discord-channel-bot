import inspect

import discord
from discord.ext import commands


async def upsert_panel(
    bot: commands.Bot,
    channel: discord.TextChannel,
    embed: discord.Embed,
    view: discord.ui.View,
    *,
    previous_titles: tuple[str, ...] = (),
) -> discord.Message:
    def matches(message: discord.Message) -> bool:
        return message.author == bot.user and any(
            item.title in (embed.title, *previous_titles) for item in message.embeds
        )

    pins = channel.pins()
    if inspect.isawaitable(pins):
        pinned_messages = await pins
    else:
        pinned_messages = [message async for message in pins]
    message = next((item for item in pinned_messages if matches(item)), None)
    if message is None:
        async for item in channel.history(limit=100):
            if matches(item):
                message = item
                break
    if message is None:
        message = await channel.send(embed=embed, view=view)
    else:
        await message.edit(embed=embed, view=view)
    if not message.pinned:
        await message.pin(reason="Keep community panel accessible")
    return message
