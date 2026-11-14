import asyncio
import logging
import time
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

import config
from models.guild_settings import GuildSettings
from service.panel_service import upsert_panel
from service.skill_service import SkillService


logger = logging.getLogger(__name__)


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


def _can_join(channel: discord.VoiceChannel, member: discord.Member) -> bool:
    permissions = channel.permissions_for(member)
    return permissions.view_channel and permissions.connect


def _creatable_categories(
    guild: discord.Guild, member: discord.Member, private_category: str
) -> list[discord.CategoryChannel]:
    if guild.me is None:
        raise RuntimeError("Bot member is unavailable when listing room categories")
    categories = []
    excluded_names = {
        config.INTRODUCTION_CATEGORY.strip().casefold(),
        private_category.strip().casefold(),
    }
    for category in guild.categories:
        if category.name.strip().casefold() in excluded_names:
            continue
        bot_permissions = category.permissions_for(guild.me)
        if (
            category.permissions_for(member).view_channel
            and bot_permissions.view_channel
            and bot_permissions.manage_channels
        ):
            categories.append(category)
    return categories


async def _shareable_roles(
    bot: commands.Bot, member: discord.Member
) -> list[discord.Role]:
    settings = await bot.guild_settings_service.get(member.guild.id)
    roles = []
    for name, emoji in SkillService.get_skills(member.guild, settings.skill_prefix):
        role = SkillService.find_role(member.guild, name, settings.skill_prefix, emoji)
        if (
            role
            and role in member.roles
            and role != member.guild.default_role
            and role not in roles
        ):
            roles.append(role)
    return roles


async def _notification_channel(
    bot: commands.Bot, guild: discord.Guild
) -> discord.TextChannel | None:
    settings = await bot.guild_settings_service.get(guild.id)
    target = getattr(
        settings, "party_notification_channel", config.PARTY_NOTIFICATION_CHANNEL
    ).strip()
    raw_id = (
        target[2:-1].strip()
        if target.startswith("<#") and target.endswith(">")
        else target
    )
    if raw_id.isdigit():
        channel_id = int(raw_id)
        channel = guild.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            return channel
        return discord.utils.get(guild.text_channels, id=channel_id)

    channel_name = target or config.PARTY_NOTIFICATION_CHANNEL
    entry = discord.utils.get(guild.text_channels, name=settings.skill_panel_channel)
    if entry is None or entry.category is None:
        return None
    return discord.utils.get(
        entry.category.text_channels, name=channel_name
    )


def _party_title(party: dict[str, Any], fallback: str) -> str:
    title = str(party.get("title", fallback))
    game = party.get("game")
    return f"{game}｜{title}" if game else title


def _party_embed(
    channel: discord.VoiceChannel, owner: discord.Member, party: dict[str, Any]
) -> discord.Embed:
    embed = discord.Embed(
        title=f"🏠 {_party_title(party, channel.name)}",
        description=party.get("note") or "房主尚未留下備註。",
        color=discord.Color.green(),
    )
    embed.add_field(name="房主", value=owner.mention)
    embed.add_field(name="人數上限", value=str(channel.user_limit or "無限制"))
    embed.add_field(name="語音房", value=channel.mention, inline=False)
    role_ids = party.get("notify_role_ids", [])
    embed.add_field(
        name="通知身分",
        value="、".join(f"<@&{role_id}>" for role_id in role_ids) or "不標記身分組",
        inline=False,
    )
    return embed


async def _report_party_error(interaction: discord.Interaction, error: Exception):
    logger.error(
        "Party interaction failed in guild %s",
        interaction.guild_id,
        exc_info=(type(error), error, error.__traceback__),
    )
    message = "❌ 房間操作失敗，請確認 Bot 的頻道／訊息權限，或稍後重試。"
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


async def _require_party_access(interaction: discord.Interaction) -> bool:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message(
            "❌ 只能在 Discord 伺服器中使用揪團功能。", ephemeral=True
        )
        return False

    if not isinstance(interaction.channel, discord.TextChannel) or not isinstance(
        interaction.user, discord.Member
    ):
        await interaction.response.send_message(
            "❌ 請在伺服器的文字頻道使用開房功能。", ephemeral=True
        )
        return False
    permissions = interaction.channel.permissions_for(interaction.user)
    if not permissions.view_channel or not permissions.send_messages:
        await interaction.response.send_message(
            "🚫 你沒有在這個文字頻道發文的權限。", ephemeral=True
        )
        return False
    client = getattr(interaction, "client", None)
    if hasattr(client, "guild_settings_service"):
        settings = await client.guild_settings_service.get(guild.id)
        if not getattr(settings, "party_enabled", True):
            await interaction.response.send_message(
                "🚫 此伺服器目前未啟用揪團房間功能。", ephemeral=True
            )
            return False
    return True


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


async def _announce_party(
    bot: commands.Bot,
    guild: discord.Guild,
    member: discord.Member,
    channel: discord.VoiceChannel,
    party: dict[str, Any],
    roles: list[discord.Role],
) -> str:
    """Post the new room to the notification channel and return a status line."""
    if not roles:
        return "ℹ️ 未選擇通知身分，不發送揪團通知。"
    destination = await _notification_channel(bot, guild)
    if destination is None:
        return "⚠️ 找不到揪團通知頻道，未發送通知；請管理員執行 /party setup。"
    if guild.me is None:
        logger.error("Bot member is unavailable in guild %s", guild.id)
        return "⚠️ 無法確認 Bot 的頻道權限，未發送通知。"
    bot_permissions = destination.permissions_for(guild.me)
    if not (
        bot_permissions.view_channel
        and bot_permissions.send_messages
        and bot_permissions.embed_links
    ):
        return "⚠️ Bot 需要通知頻道的檢視、傳送訊息與嵌入連結權限，未發送通知。"
    try:
        await destination.send(
            content=" ".join(role.mention for role in roles) or None,
            embed=_party_embed(channel, member, party),
            view=VoiceChannelLinkView(channel),
            allowed_mentions=discord.AllowedMentions(
                everyone=False, users=False, roles=roles, replied_user=False
            ),
        )
    except (discord.Forbidden, discord.HTTPException):
        logger.warning(
            "Failed to announce party room in guild %s", guild.id, exc_info=True
        )
        return "⚠️ 通知發送失敗，請確認 Bot 的頻道權限。"
    return f"📣 已通知到 {destination.mention}。"


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
        if not await _require_party_access(interaction):
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
        if not _can_join(channel, member):
            await interaction.response.send_message(
                "🚫 你沒有進入這個語音房的權限，請聯絡管理員。", ephemeral=True
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


class PartyCreateModal(discord.ui.Modal, title="建立房間"):
    def __init__(
        self,
        bot: commands.Bot,
        categories: list[discord.CategoryChannel],
        roles: list[discord.Role],
        default_category: str = "",
    ):
        super().__init__()
        self.bot = bot
        if not categories:
            raise ValueError("Room form requires at least one available category")
        default_id = next((
            category.id for category in categories[:25]
            if default_category and category.name.casefold() == default_category.casefold()
        ), categories[0].id)
        self.category_select = discord.ui.Select(
            custom_id="room_category",
            placeholder="選擇房間建立位置",
            options=[
                discord.SelectOption(
                    label=category.name[:100],
                    value=str(category.id),
                    default=category.id == default_id,
                )
                for category in categories[:25]
            ],
        )
        self.room_name = discord.ui.TextInput(
            custom_id="room_name",
            placeholder="例如：一起畫圖、閒聊、歡樂場缺 2",
            max_length=100,
        )
        self.user_limit = discord.ui.TextInput(
            custom_id="room_limit",
            placeholder="2 到 99",
            default="5",
            min_length=1,
            max_length=2,
        )
        self.note = discord.ui.TextInput(
            custom_id="room_note",
            placeholder="例如：需麥克風、預計聊兩小時",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=200,
        )
        self.notify_roles = discord.ui.Select(
            custom_id="room_notify_roles",
            placeholder="可多選；不選就不標記身分組",
            min_values=0,
            max_values=min(len(roles), 25) or 1,
            required=False,
            options=[
                discord.SelectOption(label=role.name[:100], value=str(role.id))
                for role in roles[:25]
            ] or [discord.SelectOption(label="沒有可通知的湯技，不標記身分組", value="none")],
        )
        self.add_item(discord.ui.Label(
            text="建立分類",
            description="新房公開；排除一般及私人分類，只列可用分類，最多顯示前 25 個。",
            component=self.category_select,
        ))
        self.add_item(discord.ui.Label(text="房名", component=self.room_name))
        self.add_item(discord.ui.Label(text="人數", component=self.user_limit))
        self.add_item(discord.ui.Label(text="備註", component=self.note))
        self.add_item(discord.ui.Label(
            text="通知身分",
            description="只列已加入湯技（最多前 25 個），可多選；送出後立即通知，不選則不發送通知。",
            component=self.notify_roles,
        ))

    async def on_submit(self, interaction: discord.Interaction):
        if not config.DYNAMIC_VOICE_CREATE_ENABLED:
            await interaction.response.send_message(
                "🚫 此 Bot 執行環境已停用動態語音房建立功能。", ephemeral=True
            )
            return
        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "❌ 只能在 Discord 伺服器中建立揪團。", ephemeral=True
            )
            return
        if not await _require_party_access(interaction):
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

        selected_categories = self.category_select.values
        if len(selected_categories) != 1:
            await interaction.response.send_message(
                "❌ 請選擇一個建立分類。", ephemeral=True
            )
            return
        settings = await self.bot.guild_settings_service.get(guild.id)
        category = next((
            item for item in _creatable_categories(guild, member, settings.private_category)
            if str(item.id) == selected_categories[0]
        ), None)
        if category is None:
            await interaction.response.send_message(
                "🚫 分類已不存在或權限已變更，請重新開啟表單選擇。",
                ephemeral=True,
            )
            return
        selected_roles = set(self.notify_roles.values) - {"none"}
        roles = [
            role for role in await _shareable_roles(self.bot, member)
            if str(role.id) in selected_roles
        ]
        if selected_roles != {str(role.id) for role in roles}:
            await interaction.response.send_message(
                "🚫 只能選擇你目前已加入的湯技作為通知身分，請重新開啟表單。",
                ephemeral=True,
            )
            return
        channel_name = self.room_name.value.strip()
        note = self.note.value.strip()
        if not channel_name:
            await interaction.response.send_message(
                "❌ 房名不可只填空白。", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        try:
            channel = await guild.create_voice_channel(
                channel_name,
                category=category,
                user_limit=user_limit,
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(
                        view_channel=True,
                        connect=True,
                        speak=True,
                        use_voice_activation=True,
                    )
                },
                reason=f"Party created by {member}",
            )
        except (discord.Forbidden, discord.HTTPException):
            logger.warning("Failed to create party room in guild %s", guild.id, exc_info=True)
            await interaction.followup.send(
                "❌ 無法建立語音房，請確認 Bot 具有管理頻道權限。",
                ephemeral=True,
            )
            return

        party = {
            "title": channel_name,
            "note": note,
            "notify_role_ids": [role.id for role in roles],
            "created_at": int(time.time()),
        }
        self.bot.room_registry.register(
            channel.id,
            member.id,
            party=party,
        )

        moved = False
        if member.voice and member.voice.channel:
            try:
                await member.move_to(channel, reason="Party room created")
                moved = True
            except (discord.Forbidden, discord.HTTPException):
                logger.warning(
                    "Party room created but failed to move member %s", member.id, exc_info=True
                )
        status = "✅ 已建立揪團並將你移入語音房。" if moved else "✅ 已建立揪團，請開啟語音房加入。"
        notice = await _announce_party(self.bot, guild, member, channel, party, roles)
        await interaction.followup.send(
            f"{status}\n{notice}",
            embed=_party_embed(channel, member, party),
            view=VoiceChannelLinkView(channel),
            ephemeral=True,
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await _report_party_error(interaction, error)


async def _open_party_modal(bot: commands.Bot, interaction: discord.Interaction):
    if not await _require_party_access(interaction):
        return
    guild = interaction.guild
    member = interaction.user
    if guild is None or not isinstance(member, discord.Member):
        raise ValueError("Room form requires a guild member")
    settings = await bot.guild_settings_service.get(guild.id)
    categories = _creatable_categories(guild, member, settings.private_category)
    if not categories:
        await interaction.response.send_message(
            "❌ 沒有可用的建立分類；請確認你能檢視分類，且 Bot 有管理頻道權限。",
            ephemeral=True,
        )
        return
    roles = await _shareable_roles(bot, member)
    await interaction.response.send_modal(
        PartyCreateModal(bot, categories, roles)
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
            limit = channel.user_limit or "∞"
            options.append(
                discord.SelectOption(
                    label=_party_title(party, channel.name)[:100],
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
        if not await _require_party_access(interaction):
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
        if not _can_join(channel, interaction.user):
            await interaction.response.send_message(
                "🚫 你沒有進入這個語音房的權限，請聯絡管理員。", ephemeral=True
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
    if not await _require_party_access(interaction):
        return

    if not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message(
            "❌ 只能由伺服器成員查看房間。", ephemeral=True
        )
        return
    rooms = [
        room for room in _party_rooms(bot, guild)
        if _can_join(room[0], interaction.user)
    ]
    if not rooms:
        settings = await bot.guild_settings_service.get(guild.id)
        await interaction.response.send_message(
            "目前沒有進行中的揪團。你可以建立第一個！",
            view=PartyPanelView(bot, settings),
            ephemeral=True,
        )
        return

    lines = []
    for channel, room_info, party in rooms[:25]:
        owner = guild.get_member(int(room_info["owner"]))
        owner_name = owner.mention if owner else "未知房主"
        limit = channel.user_limit or "∞"
        lines.append(
            f"• **{_party_title(party, channel.name)}**\n"
            f"  {owner_name} · {len(channel.members)}/{limit} 人 · {channel.mention}"
        )
    embed = discord.Embed(
        title="🏠 進行中的房間",
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
    def __init__(self, bot: commands.Bot, settings: GuildSettings | None = None):
        super().__init__(timeout=None)
        self.bot = bot
        settings = settings or GuildSettings()
        self.create_party.label = settings.party_panel_create_label
        self.list_parties.label = settings.party_panel_list_label

    @discord.ui.button(
        label="建立房間",
        emoji="➕",
        style=discord.ButtonStyle.primary,
        custom_id="party:create",
    )
    async def create_party(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ):
        await _open_party_modal(self.bot, interaction)

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

    async def on_error(
        self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item
    ):
        await _report_party_error(interaction, error)


class PartyCommands(commands.GroupCog, name="party"):
    """遊戲揪團大廳、動態語音房與加入流程。"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(PartyPanelView(self.bot))
        for guild in self.bot.guilds:
            settings = await self.bot.guild_settings_service.get(guild.id)
            channel = discord.utils.get(
                guild.text_channels, name=settings.skill_panel_channel
            )
            if channel is not None:
                try:
                    await self._refresh_panel(channel)
                except discord.HTTPException:
                    logger.exception("Failed to refresh community room panel in guild %s", guild.id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None or self.bot.user is None:
            return
        if self.bot.user not in message.mentions:
            return
        normalized = message.content.casefold()
        if not any(phrase in normalized for phrase in CREATE_PHRASES):
            return
        if not isinstance(message.channel, discord.TextChannel):
            return
        settings = await self.bot.guild_settings_service.get(message.guild.id)
        await message.reply(
            "🏠 點擊下方按鈕選擇分類並建立房間。",
            view=PartyPanelView(self.bot, settings),
            mention_author=False,
        )

    async def _refresh_panel(self, channel: discord.TextChannel) -> bool:
        if channel.category is None:
            raise ValueError("Community entry must be inside a category")
        settings = await self.bot.guild_settings_service.get(channel.guild.id)
        entry = discord.utils.get(
            channel.guild.text_channels, name=settings.skill_panel_channel
        )
        if entry is not None and entry.category is not None:
            notification = await _notification_channel(self.bot, channel.guild)
            configured_target = getattr(
                settings, "party_notification_channel", config.PARTY_NOTIFICATION_CHANNEL
            ).strip()
            raw_id = (
                configured_target[2:-1].strip()
                if configured_target.startswith("<#") and configured_target.endswith(">")
                else configured_target
            )
            if notification is None and not raw_id.isdigit():
                await entry.category.create_text_channel(
                    configured_target or config.PARTY_NOTIFICATION_CHANNEL,
                    topic="新建房間的自動通知；只會標記房主已加入的湯技。",
                    reason="Community room notifications setup",
                )
        else:
            logger.warning(
                "Community entry %s is missing or has no category in guild %s",
                settings.skill_panel_channel,
                channel.guild.id,
            )
        embed = discord.Embed(
            title=settings.party_panel_title,
            description=settings.party_panel_description,
            color=discord.Color.blue(),
        )
        embed.add_field(
            name=settings.party_panel_create_heading,
            value=settings.party_panel_create_description,
            inline=False,
        )
        embed.add_field(
            name=settings.party_panel_list_heading,
            value=settings.party_panel_list_description,
            inline=False,
        )
        await upsert_panel(
            self.bot, channel, embed, PartyPanelView(self.bot, settings),
            previous_titles=("🎮 遊戲揪團大廳",),
            component_prefix="party:",
        )
        return entry is not None and entry.category is not None

    @app_commands.command(name="setup", description="建立或更新置頂開房面板與通知頻道")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def setup_panel(self, interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ 請在分類內的文字頻道使用此指令。", ephemeral=True
            )
            return
        if not await _require_party_access(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        notifications_ready = await self._refresh_panel(interaction.channel)
        message = (
            "✅ 開房面板與通知頻道已準備好。"
            if notifications_ready
            else "⚠️ 開房面板已更新，但找不到分類內的社群入口，無法建立通知頻道。請檢查後台面板頻道設定。"
        )
        await interaction.followup.send(message, ephemeral=True)

    @app_commands.command(name="create", description="選擇分類並建立公開語音房")
    async def create_party(self, interaction: discord.Interaction):
        await _open_party_modal(self.bot, interaction)

    @app_commands.command(name="list", description="查看目前進行中的遊戲揪團")
    async def list_parties(self, interaction: discord.Interaction):
        await _send_party_list(self.bot, interaction)

    @setup_panel.error
    @create_party.error
    async def setup_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "🚫 你需要管理頻道權限才能建立揪團面板。", ephemeral=True
            )
            return
        await _report_party_error(interaction, error)


async def setup(bot: commands.Bot):
    await bot.add_cog(PartyCommands(bot))