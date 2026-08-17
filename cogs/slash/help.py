import discord
from discord import app_commands
from discord.ext import commands

from config import (
    AUTO_VOICE_LIMIT,
    AUTO_VOICE_SUFFIX,
    AUTO_VOICE_TRIGGER,
    BOT_PREFIX,
    LEVELUP_CHANNEL,
    PASSWORD_CHANNEL,
    PRIVATE_CATEGORY,
    PRIVATE_LIMIT,
    PRIVATE_TRIGGER,
    SKILL_PANEL_CHANNEL,
    SKILL_PREFIX,
)


def _get_help_embed(category: str = "overview") -> discord.Embed:
    category = (category or "overview").lower()

    if category in ("auto_voice", "voice", "語音"):
        embed = discord.Embed(
            title="🔊 自動語音頻道系統手冊",
            description=(
                "當成員進入觸發頻道時，系統會自動建立專屬語音房；全員離開後會自動清理刪除。\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="📌 運作機制",
            value=(
                f"• **進入觸發**：進入「`{AUTO_VOICE_TRIGGER}`」頻道即可自動建立「`使用者 的{AUTO_VOICE_SUFFIX}`」\n"
                f"• **人數預設**：預設上限 {AUTO_VOICE_LIMIT} 人（房主可調整）\n"
                f"• **自動刪除**：房內所有成員離開後，頻道將立即自動刪除"
            ),
            inline=False,
        )
        embed.add_field(
            name="🎮 房主專用指令（在自己房間內使用）",
            value=(
                "• `/voice-name <名稱>` — 重新命名你的動態語音頻道\n"
                "• `/voice-limit <人數>` — 設定房間人數上限（`0` 為無限制）\n"
                "• `/voice-kick <成員>` — 將特定成員移出你的語音頻道"
            ),
            inline=False,
        )
        embed.add_field(
            name="⚙️ 管理員維護指令",
            value=(
                "• `/setup-voice` — 在伺服器所有分類下批次補建自動語音觸發頻道（需「管理頻道」權限）"
            ),
            inline=False,
        )
        embed.set_footer(text="💡 提示：只有語音房的建立者（房主）才能使用改名、限額與踢人指令")
        return embed

    if category in ("private_room", "private", "包廂", "私人"):
        embed = discord.Embed(
            title="🔒 私人包廂系統手冊",
            description=(
                "提供密碼鎖定與受邀機制的私人語音空間，房主可自由分享密碼或直接邀請成員。\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.orange(),
        )
        embed.add_field(
            name="📌 建立與加入流程",
            value=(
                f"1️⃣ 進入「`{PRIVATE_TRIGGER}`」觸發頻道，系統自動在「`{PRIVATE_CATEGORY}`」分類下建立上鎖包廂（預設上限 {PRIVATE_LIMIT} 人）\n"
                f"2️⃣ 機器人會私訊 6 碼隨機密碼給房主\n"
                f"3️⃣ 其他成員前往 **#{PASSWORD_CHANNEL}** 頻道輸入密碼，即可解鎖並加入該包廂（輸入的密碼訊息會自動銷毀確保隱私）\n"
                f"4️⃣ 當所有成員離開包廂後，房間將自動銷毀且密碼立即失效"
            ),
            inline=False,
        )
        embed.add_field(
            name="🔑 相關指令",
            value=(
                "• `/voice-invite <成員>` — 房主專用：直接邀請指定成員進入私人包廂（免輸密碼）\n"
                "• `/setup-private` — 管理員專用：建立私人包廂分類、密碼頻道與觸發頻道（需「管理頻道」權限）\n"
                "• `/fix-private-perms` — 管理員專用：修復現有包廂權限以確保房主擁有管理權（需「管理頻道」權限）"
            ),
            inline=False,
        )
        embed.set_footer(text=f"💡 遇到無法看見或進入包廂時，請管理員執行 /setup-private 同步權限")
        return embed

    if category in ("skill", "skills", "湯技"):
        embed = discord.Embed(
            title="🏷️ 湯技角色與頻道系統手冊",
            description=(
                "「湯技」整合了**專屬身分組**、**私密分類**、**討論論壇**、**文字聊天**與**語音頻道**，並支援邀請碼與按鈕面板加入。\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.purple(),
        )
        embed.add_field(
            name="👥 成員指令",
            value=(
                "• `/skill join <邀請碼>` — 輸入 8 碼專屬邀請碼，加入該湯技身分組與所有專屬頻道\n"
                "• `/skill leave <名稱>` — 離開指定湯技身分組並移除專屬頻道存取權\n"
                "• `/skill list` — 列出伺服器現有的全部湯技身分組與目前加入人數"
            ),
            inline=False,
        )
        embed.add_field(
            name="🛠️ 管理員指令（需「管理角色」權限）",
            value=(
                "• `/skill create <名稱> [emoji]` — **一鍵完整建立湯技**：\n"
                f"　 1. 建立身分組角色（`{SKILL_PREFIX}<名稱>`）\n"
                f"　 2. 建立專屬私密分類（`{SKILL_PREFIX}<名稱> <emoji>`）\n"
                f"　 3. 建立論壇討論區（`<名稱>-討論`）\n"
                f"　 4. 建立文字聊天室（`#<名稱>-聊天`）\n"
                f"　 5. 建立自動語音觸發頻道（`{AUTO_VOICE_TRIGGER}`）\n"
                "　 6. 生成 8 碼邀請碼並私訊給建立者\n"
                f"　 7. 自動更新 **#{SKILL_PANEL_CHANNEL}** 互動面板\n"
                "• `/skill delete <名稱>` — 刪除指定湯技的身分組、分類、全部專屬頻道與邀請碼\n"
                "• `/skill info <名稱> [regenerate]` — 查看湯技邀請碼、身分組與分類資訊（可選重新產生）\n"
                "• `/skill regen <名稱>` — 為指定湯技重新產生新的邀請碼（舊碼作廢）\n"
                "• `/skill setup` — 檢查既有湯技，自動補齊缺失的頻道（論壇/聊天/語音觸發）並同步身分組權限\n"
                "• `/skill panel` — 在當前頻道發送互動按鈕面板（支援按鈕加入/離開）"
            ),
            inline=False,
        )
        embed.set_footer(text=f"💡 機器人啟動時會自動在 #{SKILL_PANEL_CHANNEL} 頻道維護互動面板")
        return embed

    if category in ("leveling", "level", "等級", "活躍"):
        embed = discord.Embed(
            title="🎮 活躍值與等級系統手冊",
            description=(
                "透過伺服器日常互動（文字發言、語音掛機、每日簽到）獲取經驗值 XP，自動升級並解鎖專屬稱號身分組！\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.green(),
        )
        embed.add_field(
            name="📈 經驗值 (XP) 獲取途徑",
            value=(
                "• 💬 **文字聊天**：每則訊息獲取 `15~25 XP`（冷卻時間 60 秒，避免刷頻）\n"
                "• 🎙️ **語音掛機**：語音頻道人數 ≥ 2 人時，每 5 分鐘獲得 `10 XP`\n"
                "• 📅 **每日簽到**：基礎 `50 XP`，連續 7 天享 `1.5 倍`，連續 30 天享 `2.0 倍` 加成"
            ),
            inline=False,
        )
        embed.add_field(
            name="👥 成員指令",
            value=(
                "• `/daily` — 進行每日簽到，領取 XP 並累積連續簽到天數\n"
                "• `/rank [成員]` — 查看個人或指定成員的等級卡、稱號、排名、連續簽到與升級進度\n"
                "• `/leaderboard` — 查看伺服器活躍值排行榜 TOP 10"
            ),
            inline=False,
        )
        embed.add_field(
            name="⚙️ 管理員指令（需「管理角色」權限）",
            value=(
                f"• `/level-preview` — 預覽升級公告（發至 **#{LEVELUP_CHANNEL}**）、等級卡與排行榜效果\n"
                "• `/level-init` — 為全體現有成員初始化等級資料並發放 LV1 起始身分組"
            ),
            inline=False,
        )
        embed.set_footer(text="💡 等級達標時系統會自動發放對應稱號身分組並在等級頻道發布升級公告")
        return embed

    if category in ("general", "util", "一般", "公告"):
        embed = discord.Embed(
            title="📢 一般功能與公告模組手冊",
            description="提供伺服器常用工具、公告發布與前綴指令。\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=discord.Color.gold(),
        )
        embed.add_field(
            name="⚡ 斜線指令 (Slash Commands)",
            value=(
                "• `/help [類別]` — 開啟功能說明清單與互動選單\n"
                "• `/userinfo [成員]` — 查看指定成員或自己的詳細帳號與伺服器資訊\n"
                "• `/announce <標題> <內容>` — 發送格式化的嵌入式公告（需「管理訊息」權限）"
            ),
            inline=False,
        )
        embed.add_field(
            name="⌨️ 前綴指令（預設前綴 `!`）",
            value=(
                f"• `{BOT_PREFIX}ping` — 測試機器人與 Discord 伺服器間的延遲 (ms)\n"
                f"• `{BOT_PREFIX}info` — 查看機器人所在伺服器數量與運行延遲\n"
                f"• `{BOT_PREFIX}help [類別]` — 顯示文字版指令說明"
            ),
            inline=False,
        )
        return embed

    if category in ("admin", "管理", "管理員"):
        embed = discord.Embed(
            title="⚙️ 管理員指令總整理",
            description="各模組需管理權限之維護指令彙整清單。\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=discord.Color.dark_red(),
        )
        embed.add_field(
            name="🏷️ 湯技管理（需「管理角色」權限）",
            value=(
                "• `/skill create <名稱> [emoji]` — 完整建立湯技身分組、分類、論壇/聊天/語音頻道與邀請碼\n"
                "• `/skill delete <名稱>` — 刪除指定湯技所有資源\n"
                "• `/skill info <名稱> [regenerate]` — 查詢/更換邀請碼與檢視身分組\n"
                "• `/skill regen <名稱>` — 重新產生邀請碼\n"
                "• `/skill setup` — 補齊缺失頻道與修復權限\n"
                "• `/skill panel` — 發送互動選單面板"
            ),
            inline=False,
        )
        embed.add_field(
            name="🔊 語音與包廂設定（需「管理頻道」權限）",
            value=(
                "• `/setup-voice` — 在伺服器所有分類批次建立動態語音觸發頻道\n"
                "• `/setup-private` — 建立私人包廂分類、密碼頻道與觸發頻道\n"
                "• `/fix-private-perms` — 批次修復所有包廂之房主管理權限"
            ),
            inline=False,
        )
        embed.add_field(
            name="🎮 等級與公告（需「管理角色」或「管理訊息」權限）",
            value=(
                "• `/level-init` — 全伺服器成員等級初始化與 LV1 身分組發放\n"
                "• `/level-preview` — 預覽升級公告、等級卡與排行榜\n"
                "• `/announce <標題> <內容>` — 發送嵌入式公告"
            ),
            inline=False,
        )
        embed.set_footer(text="💡 使用前請確認 Bot 身分組在 Discord 伺服器身分組階層中位於最高層")
        return embed

    # Default: overview
    embed = discord.Embed(
        title="🤖 Discord Channel Bot 功能總覽手冊",
        description=(
            "歡迎使用 **Discord Channel Bot**！這是一個專為伺服器打造的模組化管理機器人。\n"
            "你可以使用下方的**下拉式選單**切換查看各模組的詳細說明與指令清單。\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="🔊 自動語音頻道 (`/help auto_voice`)",
        value="進房自動建立專屬語音房、全員離開自動刪除；房主可改名、限額與踢人。",
        inline=False,
    )
    embed.add_field(
        name="🔒 私人包廂系統 (`/help private_room`)",
        value=f"自動建立上鎖語音包廂，機器人私訊密碼給房主，其他人於 **#{PASSWORD_CHANNEL}** 輸入密碼加入。",
        inline=False,
    )
    embed.add_field(
        name="🏷️ 湯技角色與頻道 (`/help skill`)",
        value=f"一鍵建立湯技身分組、分類、論壇討論區、聊天頻道與語音觸發；支援邀請碼與 **#{SKILL_PANEL_CHANNEL}** 按鈕面板。",
        inline=False,
    )
    embed.add_field(
        name="🎮 活躍值等級系統 (`/help leveling`)",
        value=f"文字聊天、語音掛機、每日簽到獲取 XP；自動升級並發放稱號身分組，提供等級卡與排行榜。",
        inline=False,
    )
    embed.add_field(
        name="📢 一般工具與公告 (`/help general`)",
        value=f"使用者資訊查詢、Embed 公告發布，以及 `{BOT_PREFIX}ping` 等實用工具。",
        inline=False,
    )
    embed.add_field(
        name="⚙️ 管理員專區 (`/help admin`)",
        value="伺服器管理員專用的維護、修復與初始化指令整理。",
        inline=False,
    )
    embed.set_footer(text=f"💡 輸入 /help 或 !help 查看；使用選單可快速瀏覽各模組細節")
    return embed


class HelpSelect(discord.ui.Select):
    """Dropdown select menu for navigating help categories."""

    def __init__(self):
        options = [
            discord.SelectOption(
                label="全部總覽",
                value="overview",
                description="查看所有功能模組簡介與快速導引",
                emoji="📋",
                default=True,
            ),
            discord.SelectOption(
                label="自動語音房",
                value="auto_voice",
                description="動態建立語音房、房主改名/限額/踢人",
                emoji="🔊",
            ),
            discord.SelectOption(
                label="私人包廂系統",
                value="private_room",
                description="密碼鎖定語音包廂、邀請與密碼驗證機制",
                emoji="🔒",
            ),
            discord.SelectOption(
                label="湯技角色系統",
                value="skill",
                description="湯技身分組、論壇/聊天/語音頻道、邀請碼與面板",
                emoji="🏷️",
            ),
            discord.SelectOption(
                label="等級與活躍值",
                value="leveling",
                description="聊天/語音/簽到 XP、等級卡、排行榜與稱號",
                emoji="🎮",
            ),
            discord.SelectOption(
                label="一般工具與公告",
                value="general",
                description="使用者查詢、Embed 公告與前綴指令",
                emoji="📢",
            ),
            discord.SelectOption(
                label="管理員專區",
                value="admin",
                description="管理員維護、修復與初始化指令整理",
                emoji="⚙️",
            ),
        ]
        super().__init__(
            placeholder="🔽 請選擇要查看的功能模組說明...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="help_menu_select",
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        for opt in self.options:
            opt.default = opt.value == selected

        embed = _get_help_embed(selected)
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    """Interactive view holding the HelpSelect dropdown."""

    def __init__(self, default_category: str = "overview"):
        super().__init__(timeout=180)
        select = HelpSelect()
        for opt in select.options:
            opt.default = opt.value == default_category
        self.add_item(select)


class HelpCommand(commands.Cog):
    """說明手冊模組 — 提供 /help 與 !help 指令"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="顯示機器人各項功能與指令使用手冊（支援互動下拉選單）",
    )
    @app_commands.describe(category="直接切換至指定模組說明（留空顯示總覽）")
    @app_commands.choices(
        category=[
            app_commands.Choice(name="📋 總覽 (Overview)", value="overview"),
            app_commands.Choice(name="🔊 自動語音房 (Auto Voice)", value="auto_voice"),
            app_commands.Choice(name="🔒 私人包廂 (Private Rooms)", value="private_room"),
            app_commands.Choice(name="🏷️ 湯技系統 (Skill System)", value="skill"),
            app_commands.Choice(name="🎮 等級與活躍 (Leveling)", value="leveling"),
            app_commands.Choice(name="📢 一般與公告 (General & Utilities)", value="general"),
            app_commands.Choice(name="⚙️ 管理員專區 (Admin Commands)", value="admin"),
        ]
    )
    async def slash_help(
        self,
        interaction: discord.Interaction,
        category: app_commands.Choice[str] | None = None,
    ):
        selected_key = category.value if category else "overview"
        embed = _get_help_embed(selected_key)
        view = HelpView(default_category=selected_key)
        await interaction.response.send_message(embed=embed, view=view)

    @commands.command(name="help")
    async def prefix_help(self, ctx: commands.Context, category: str | None = None):
        """查看機器人功能與指令說明"""
        selected_key = category or "overview"
        embed = _get_help_embed(selected_key)
        view = HelpView(default_category=selected_key)
        await ctx.send(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCommand(bot))
