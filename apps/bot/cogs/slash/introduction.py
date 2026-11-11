import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

import config
from cogs.repository.introduction_db import IntroductionDB


logger = logging.getLogger(__name__)


async def _report_error(interaction: discord.Interaction, error: Exception):
    logger.error(
        "Introduction interaction failed in guild %s",
        interaction.guild_id,
        exc_info=(type(error), error, error.__traceback__),
    )
    message = (
        "❌ 無法完成自我介紹操作，請確認 Bot 的頻道／訊息權限"
        "（置頂需「釘選訊息」權限），或稍後重試。"
    )
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


class IntroductionModal(discord.ui.Modal, title="自我介紹"):
    nickname = discord.ui.TextInput(label="稱呼", max_length=80)
    interests = discord.ui.TextInput(
        label="興趣／常玩的遊戲",
        style=discord.TextStyle.paragraph,
        max_length=500,
    )
    looking_for = discord.ui.TextInput(
        label="想認識的同好（選填）",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500,
    )
    availability = discord.ui.TextInput(
        label="常出沒時間（選填）", required=False, max_length=200
    )

    def __init__(self, cog: "Introduction"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        if not self.nickname.value.strip() or not self.interests.value.strip():
            await interaction.response.send_message(
                "❌ 稱呼與興趣不可只填空白。", ephemeral=True
            )
            return
        if interaction.guild is None or not isinstance(
            interaction.channel, discord.TextChannel
        ):
            await interaction.response.send_message(
                "❌ 請在伺服器的自我介紹文字頻道使用此表單。", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title="自我介紹",
            description=f"成員：{interaction.user.mention}",
            color=discord.Color.blue(),
        )
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url,
        )
        for label, value in (
            ("稱呼", self.nickname.value),
            ("興趣／常玩的遊戲", self.interests.value),
            ("想認識的同好", self.looking_for.value),
            ("常出沒時間", self.availability.value),
        ):
            embed.add_field(name=label, value=value.strip() or "未填寫", inline=False)

        message = await self.cog.publish(interaction, embed)
        await interaction.followup.send(
            f"✅ 已發布／更新你的自我介紹：{message.jump_url}", ephemeral=True
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await _report_error(interaction, error)


class IntroductionView(discord.ui.View):
    def __init__(self, cog: "Introduction"):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(
        label="填寫／更新自我介紹",
        style=discord.ButtonStyle.primary,
        custom_id="introduction:open",
    )
    async def open_form(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(IntroductionModal(self.cog))

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item,
    ):
        await _report_error(interaction, error)


class Introduction(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = IntroductionDB(config.SETTINGS_DB_PATH)
        self.view = IntroductionView(self)
        self._lock = asyncio.Lock()

    async def cog_load(self):
        await self.db.init()
        self.bot.add_view(self.view)

    async def cog_unload(self):
        self.bot.remove_view(self.view)
        await self.db.close()

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            for channel_id, message_id in await self.db.get_panels(guild.id):
                try:
                    channel = guild.get_channel(channel_id)
                    if channel is None:
                        channel = await guild.fetch_channel(channel_id)
                    if not isinstance(channel, discord.TextChannel):
                        logger.warning(
                            "Introduction panel channel %s is not a text channel",
                            channel_id,
                        )
                        continue
                    message = await channel.fetch_message(message_id)
                    if not message.pinned:
                        await message.pin(reason="Keep introduction form accessible")
                except discord.HTTPException:
                    logger.warning(
                        "Failed to pin introduction panel %s in channel %s",
                        message_id,
                        channel_id,
                        exc_info=True,
                    )

    async def publish(
        self, interaction: discord.Interaction, embed: discord.Embed
    ) -> discord.Message:
        guild = interaction.guild
        channel = interaction.channel
        if guild is None or not isinstance(channel, discord.TextChannel):
            raise ValueError("Introduction requires a guild text channel")

        async with self._lock:
            if await self.db.get_panel(guild.id, channel.id) is None:
                raise ValueError("Channel does not have an introduction panel")
            location = await self.db.get(guild.id, interaction.user.id)
            message = None
            if location is not None:
                channel_id, message_id = location
                try:
                    old_channel = guild.get_channel(channel_id)
                    if old_channel is None:
                        old_channel = await guild.fetch_channel(channel_id)
                    if not isinstance(old_channel, discord.TextChannel):
                        raise ValueError("Stored introduction channel is not a text channel")
                    message = await old_channel.fetch_message(message_id)
                except discord.NotFound:
                    # A deleted introduction can be recreated on the next submission.
                    message = None
            if message is not None:
                await message.edit(embed=embed, allowed_mentions=discord.AllowedMentions.none())
                return message

            message = await channel.send(
                embed=embed, allowed_mentions=discord.AllowedMentions.none()
            )
            await self.db.save(guild.id, interaction.user.id, channel.id, message.id)
            return message

    @app_commands.command(
        name="setup-introduction",
        description="建立自我介紹文字頻道與表單入口（需管理頻道權限）",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(category="自我介紹所在分類，預設為「一般」")
    async def setup_introduction(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel | None = None,
    ):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "❌ 請在伺服器中使用此指令。", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        async with self._lock:
            category = category or discord.utils.get(
                guild.categories, name=config.INTRODUCTION_CATEGORY
            )
            if category is None:
                category = await guild.create_category(
                    config.INTRODUCTION_CATEGORY, reason="Introduction setup"
                )
            channel = discord.utils.get(
                category.text_channels, name=config.INTRODUCTION_CHANNEL
            )
            if channel is None:
                channel = await category.create_text_channel(
                    config.INTRODUCTION_CHANNEL,
                    topic="點擊 Bot 按鈕填寫自我介紹；再次填寫會更新原文。",
                    reason=f"Introduction setup by {interaction.user}",
                )
            embed = discord.Embed(
                title="認識一下彼此",
                description=(
                    "點擊下方按鈕，填寫稱呼、興趣與想認識的同好。\n"
                    "送出後會公開發布在本頻道；再次填寫會更新原文，不新增第二篇。\n"
                    "自由參加，不影響加入湯技或使用語音房。請勿填寫敏感個人資料。\n"
                    "找不到按鈕時，可從本頻道的「置頂訊息」開啟這張說明卡。"
                ),
                color=discord.Color.blue(),
            )
            message_id = await self.db.get_panel(guild.id, channel.id)
            message = None
            if message_id is not None:
                try:
                    message = await channel.fetch_message(message_id)
                except discord.NotFound:
                    message = None
            if message is None:
                message = await channel.send(embed=embed, view=self.view)
                await self.db.save_panel(guild.id, channel.id, message.id)
            else:
                await message.edit(embed=embed, view=self.view)
            if not message.pinned:
                await message.pin(reason="Keep introduction form accessible")
        await interaction.followup.send(
            f"✅ 自我介紹入口已準備好：{channel.mention}", ephemeral=True
        )

    @setup_introduction.error
    async def setup_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "🚫 你需要「管理頻道」權限才能設定自我介紹。", ephemeral=True
            )
            return
        await _report_error(interaction, error)


async def setup(bot: commands.Bot):
    await bot.add_cog(Introduction(bot))
