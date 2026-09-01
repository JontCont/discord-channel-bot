import time
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands


CREATE_PHRASES = (
    "create server",
    "create room",
    "建立伺服器",
    "建立房間",
    "建立揪團",
    "開房",
)


def _party_rooms(
    bot: commands.Bot, guild: discord.Guild
) -> list[tuple[discord.VoiceChannel, dict[str, Any], dict[str, Any]]]:
    rooms = []
    for channel_id, room_info in bot.room_registry.entries():
        party = room_info.get("party")
        if not isinstance(party, dict):
            continue
        channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.VoiceChannel):
            continue
        rooms.append((channel, room_info, party))
    return sorted(rooms, key=lambda item: int(item[2].get("created_at", 0)))


def _voice_channel_link(channel: discord.VoiceChannel) -> str:
    return f"https://discord.com/channels/{channel.guild.id}/{channel.id}"


def _category_matches(channel: Any, category_name: str) -> bool:
    category = getattr(channel, "category", None)
    if category is None:
        category = getattr(getattr(channel, "parent", None), "category", None)
    return bool(
        category
        and category.name.casefold() == category_name.strip().casefold()
    )


async def _require_party_category(
    bot: commands.Bot, interaction: discord.Interaction
) -> bool:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message(
            "❌ 只能在 Discord 伺服器中使用揪團功能。", ephemeral=True
        )
        return False

    settings = await bot.guild_settings_service.get(guild.id)
    if _category_matches(interaction.channel, settings.party_category):
        return True

    await interaction.response.send_message(
        f"🚫 揪團功能只能在「{settings.party_category}」類別下使用。",
        ephemeral=True,
    )
    return False


class VoiceChannelLinkView(discord.ui.View):
    def __init__(self, channel: discord.VoiceChannel):
        super().__init__(timeout=60)
        self.add_item(
            discord.ui.Button(
                label="開啟語音房",
                emoji="🔊",
                url=_voice_channel_link(channel),
            )
        )


class PartyJoinConfirmView(discord.ui.View):
    def __init__(self, bot: commands.Bot, channel: discord.VoiceChannel):
        super().__init__(timeout=60)
        self.bot = bot
        self.channel_id = channel.id

    @discord.ui.button(label="進入揪團", emoji="🔊", style=discord.ButtonStyle.green)
    async def join_party(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "❌ 只能在 Discord 伺服器中加入揪團。", ephemeral=True
            )
            return
        if not await _require_party_category(self.bot, interaction):
            return

        channel = guild.get_channel(self.channel_id)
        if (
            not isinstance(channel, discord.VoiceChannel)
            or not self.bot.room_registry.get(channel.id)
        ):
            await interaction.response.send_message(
                "⚠️ 這個揪團已經結束，請重新開啟列表。", ephemeral=True
            )
            return
        if member.voice and member.voice.channel == channel:
            await interaction.response.send_message(
                "✅ 你已經在這個語音房中。", ephemeral=True
            )
            return
        if channel.user_limit and len(channel.members) >= channel.user_limit:
            await interaction.response.send_message(
                "⚠️ 這個語音房目前已滿。", ephemeral=True
            )
            return
        if member.voice is None or member.voice.channel is None:
            await interaction.response.send_message(
                "⚠️ 請先加入任一語音頻道，再按下進入按鈕；Bot 會直接將你移入。",
                ephemeral=True,
            )
            return

        try:
            await member.move_to(channel, reason="Joined party after confirmation")
        except (discord.Forbidden, discord.HTTPException):
            await interaction.response.send_message(
                "❌ 無法移動你，請確認 Bot 具有移動成員權限。", ephemeral=True
            )
            return

        button.disabled = True
        await interaction.response.edit_message(
            content=f"✅ 已將你移動到 {channel.mention}。", view=self
        )


class PartyCreateModal(discord.ui.Modal, title="建立遊戲揪團"):
    game = discord.ui.TextInput(
        label="遊戲",
        placeholder="例如：CS2、Valorant、魔物獵人",
        max_length=40,
    )
    topic = discord.ui.TextInput(
        label="揪團標題",
        placeholder="例如：競技缺 2、歡樂場新手可",
        max_length=50,
    )
    user_limit = discord.ui.TextInput(
        label="房間人數上限",
        placeholder="2 到 99",
        default="5",
        min_length=1,
        max_length=2,
    )
    note = discord.ui.TextInput(
        label="備註（選填）",
        placeholder="例如：台服、需麥克風、預計玩兩小時",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=200,
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "❌ 只能在 Discord 伺服器中建立揪團。", ephemeral=True
            )
            return
        if not await _require_party_category(self.bot, interaction):
            return

        try:
            user_limit = int(self.user_limit.value.strip())
        except ValueError:
            user_limit = 0
        if not 2 <= user_limit <= 99:
            await interaction.response.send_message(
                "❌ 房間人數上限必須是 2 到 99。", ephemeral=True
            )
            return

        for channel, room_info, _party in _party_rooms(self.bot, guild):
            if room_info.get("owner") == member.id:
                await interaction.response.send_message(
                    f"⚠️ 你已經有一個進行中的揪團：{channel.mention}",
                    view=VoiceChannelLinkView(channel),
                    ephemeral=True,
                )
                return

        settings = await self.bot.guild_settings_service.get(guild.id)
        category = discord.utils.find(
            lambda item: item.name.casefold() == settings.party_category.casefold(),
            guild.categories,
        )
        if category is None:
            await interaction.response.send_message(
                f"❌ 找不到「{settings.party_category}」類別，請先在 Web 後台重新設定。",
                ephemeral=True,
            )
            return

        game = self.game.value.strip()
        topic = self.topic.value.strip()
        note = self.note.value.strip()
        channel_name = f"🎮 {game}｜{topic}"[:100]

        try:
            channel = await guild.create_voice_channel(
                channel_name,
                category=category,
                user_limit=user_limit,
                reason=f"Party created by {member}",
            )
        except (discord.Forbidden, discord.HTTPException):
            await interaction.response.send_message(
                "❌ 無法建立語音房，請確認 Bot 具有管理頻道權限。",
                ephemeral=True,
            )
            return

        self.bot.room_registry.register(
            channel.id,
            member.id,
            party={
                "game": game,
                "title": topic,
                "note": note,
                "created_at": int(time.time()),
            },
        )

        moved = False
        if member.voice and member.voice.channel:
            try:
                await member.move_to(channel, reason="Party room created")
                moved = True
            except (discord.Forbidden, discord.HTTPException):
                pass

        embed = discord.Embed(
            title=f"🎮 {game}｜{topic}",
            description=note or "房主尚未留下備註。",
            color=discord.Color.green(),
        )
        embed.add_field(name="房主", value=member.mention)
        embed.add_field(name="人數上限", value=str(user_limit))
        embed.add_field(name="語音房", value=channel.mention, inline=False)
        status = "✅ 已建立揪團並將你移入語音房。" if moved else "✅ 已建立揪團，請開啟語音房加入。"
        await interaction.response.send_message(
            status,
            embed=embed,
            view=VoiceChannelLinkView(channel),
            ephemeral=True,
        )


class PartySelect(discord.ui.Select):
    def __init__(
        self,
        bot: commands.Bot,
        rooms: list[tuple[discord.VoiceChannel, dict[str, Any], dict[str, Any]]],
    ):
        self.bot = bot
        options = []
        for channel, _room_info, party in rooms[:25]:
            game = str(party.get("game", "遊戲"))
            topic = str(party.get("title", channel.name))
            limit = channel.user_limit or "∞"
            options.append(
                discord.SelectOption(
                    label=f"{game}｜{topic}"[:100],
                    description=f"目前 {len(channel.members)}/{limit} 人"[:100],
                    value=str(channel.id),
                    emoji="🎮",
                )
            )
        super().__init__(
            placeholder="選擇想加入的揪團",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ 只能在 Discord 伺服器中加入揪團。", ephemeral=True
            )
            return
        if not await _require_party_category(self.bot, interaction):
            return

        channel = guild.get_channel(int(self.values[0]))
        if (
            not isinstance(channel, discord.VoiceChannel)
            or not self.bot.room_registry.get(channel.id)
        ):
            await interaction.response.send_message(
                "⚠️ 這個揪團已經結束，請重新開啟列表。", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"要進入 {channel.mention} 嗎？請先加入任一語音頻道，再按下按鈕。",
            view=PartyJoinConfirmView(self.bot, channel),
            ephemeral=True,
        )


class PartyListView(discord.ui.View):
    def __init__(
        self,
        bot: commands.Bot,
        rooms: list[tuple[discord.VoiceChannel, dict[str, Any], dict[str, Any]]],
    ):
        super().__init__(timeout=120)
        self.add_item(PartySelect(bot, rooms))


async def _send_party_list(bot: commands.Bot, interaction: discord.Interaction):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message(
            "❌ 只能在 Discord 伺服器中查看揪團。", ephemeral=True
        )
        return
    if not await _require_party_category(bot, interaction):
        return

    rooms = _party_rooms(bot, guild)
    if not rooms:
        await interaction.response.send_message(
            "目前沒有進行中的揪團。你可以建立第一個！",
            view=PartyPanelView(bot),
            ephemeral=True,
        )
        return

    lines = []
    for channel, room_info, party in rooms[:25]:
        owner = guild.get_member(int(room_info["owner"]))
        owner_name = owner.mention if owner else "未知房主"
        limit = channel.user_limit or "∞"
        lines.append(
            f"• **{party.get('game', '遊戲')}｜{party.get('title', channel.name)}**\n"
            f"  {owner_name} · {len(channel.members)}/{limit} 人 · {channel.mention}"
        )
    embed = discord.Embed(
        title="🎮 進行中的遊戲揪團",
        description="\n".join(lines),
        color=discord.Color.blue(),
    )
    if len(rooms) > 25:
        embed.set_footer(text=f"僅顯示前 25 個揪團，共 {len(rooms)} 個。")
    await interaction.response.send_message(
        embed=embed,
        view=PartyListView(bot, rooms),
        ephemeral=True,
    )


class PartyPanelView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="建立揪團",
        emoji="➕",
        style=discord.ButtonStyle.primary,
        custom_id="party:create",
    )
    async def create_party(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ):
        if not await _require_party_category(self.bot, interaction):
            return
        await interaction.response.send_modal(PartyCreateModal(self.bot))

    @discord.ui.button(
        label="查看房間",
        emoji="🎮",
        style=discord.ButtonStyle.secondary,
        custom_id="party:list",
    )
    async def list_parties(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ):
        await _send_party_list(self.bot, interaction)


class PartyCommands(commands.GroupCog, name="party"):
    """遊戲揪團大廳、動態語音房與加入流程。"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(PartyPanelView(self.bot))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None or self.bot.user is None:
            return
        if self.bot.user not in message.mentions:
            return
        normalized = message.content.casefold()
        if not any(phrase in normalized for phrase in CREATE_PHRASES):
            return
        settings = await self.bot.guild_settings_service.get(message.guild.id)
        if not _category_matches(message.channel, settings.party_category):
            await message.reply(
                f"🚫 揪團功能只能在「{settings.party_category}」類別下使用。",
                mention_author=False,
            )
            return
        await message.reply(
            "🎮 點擊下方按鈕建立遊戲揪團。",
            view=PartyPanelView(self.bot),
            mention_author=False,
        )

    @app_commands.command(name="setup", description="在目前頻道建立固定揪團面板")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def setup_panel(self, interaction: discord.Interaction):
        if interaction.channel is None:
            await interaction.response.send_message(
                "❌ 找不到目前的文字頻道。", ephemeral=True
            )
            return
        if not await _require_party_category(self.bot, interaction):
            return
        embed = discord.Embed(
            title="🎮 遊戲揪團大廳",
            description=(
                "想找人一起玩嗎？建立一個揪團語音房，"
                "或查看目前正在等待隊友的房間。"
            ),
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="建立揪團",
            value="填寫遊戲、標題、人數與備註後，自動建立語音房。",
            inline=False,
        )
        embed.add_field(
            name="查看房間",
            value="先加入任一語音頻道，再從即時列表選擇揪團，Bot 會直接移動你。",
            inline=False,
        )
        await interaction.channel.send(embed=embed, view=PartyPanelView(self.bot))
        await interaction.response.send_message("✅ 揪團面板已建立。", ephemeral=True)

    @app_commands.command(name="create", description="開啟表單建立遊戲揪團")
    async def create_party(self, interaction: discord.Interaction):
        if not await _require_party_category(self.bot, interaction):
            return
        await interaction.response.send_modal(PartyCreateModal(self.bot))

    @app_commands.command(name="list", description="查看目前進行中的遊戲揪團")
    async def list_parties(self, interaction: discord.Interaction):
        await _send_party_list(self.bot, interaction)

    @setup_panel.error
    async def setup_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "🚫 你需要管理頻道權限才能建立揪團面板。", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(PartyCommands(bot))