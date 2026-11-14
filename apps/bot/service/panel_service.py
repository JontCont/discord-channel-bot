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
    component_prefix: str | None = None,
) -> discord.Message:
    if len(embed.description or "") > 4096 or len(embed) > 6000:
        raise ValueError("Panel text, including dynamic skill rows, exceeds Discord embed limits.")

    def matches(message: discord.Message) -> bool:
        if message.author != bot.user:
            return False
        if component_prefix:
            ids = [
                component.custom_id
                for row in message.components
                if isinstance(row, discord.ActionRow)
                for component in row.children
                if isinstance(component, (discord.Button, discord.SelectMenu)) and component.custom_id
            ]
            if ids:
                return any(custom_id.startswith(component_prefix) for custom_id in ids)
        return any(
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
