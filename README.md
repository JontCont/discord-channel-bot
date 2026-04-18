# 🤖 Discord Channel Bot

一個功能豐富的 Discord 機器人，使用 [discord.py](https://github.com/Rapptz/discord.py) 建立，採用 Cogs 模組化架構。支援自動語音頻道、私人包廂、湯技角色系統、活躍值等級系統等實用功能，讓你的伺服器管理更輕鬆！

> **Python 3.10+** · **discord.py ≥ 2.3.0** · **支援 Docker 部署**

---

## ✨ 功能總覽

### 🎯 基本指令

使用前綴指令（預設 `!`）快速互動，例如查看延遲與機器人資訊。

### ⚡ Slash 指令

支援 Discord 原生 Slash 指令，包括查詢使用者資訊等。

### 📢 公告 Embed

透過 `/announce` 指令發送格式化的嵌入式公告訊息（需要管理訊息權限）。

### 🔊 自動語音頻道系統

- **公開語音房** — 加入「➕ 建立語音頻道」觸發頻道，自動建立專屬語音房，所有人離開後自動刪除。
- **私人包廂** — 加入「➕ 開設私人包廂」觸發頻道，自動建立上鎖的私人語音房。機器人會私訊密碼給房主，其他人需要在 `#🔑｜輸入密碼` 頻道輸入密碼才能進入。
- **房主管理指令** — 改名、設人數上限、邀請或踢出成員。

### 🏷️ 湯技角色系統

一鍵建立「湯技」技能角色，自動生成對應的分類、文字頻道和語音觸發器。成員可自由加入/離開，管理員可發送互動按鈕面板，方便成員一鍵選擇。

### 🎮 活躍值等級系統

透過聊天、語音掛機、每日簽到賺取經驗值，自動升級並獲得稱號角色。

- **經驗值來源** — 💬 文字聊天（15~25 XP）、🎙️ 語音掛機（10 XP/5 分鐘）、📅 每日簽到（50 XP）
- **連續簽到加成** — 連續 7 天 ×1.5、連續 30 天 ×2.0
- **10 個里程碑稱號** — 從 🌱 新手湯友（LV1）到 🏆 湯神（LV50）
- **升級公告** — 自動在 `#等級公告` 頻道發送升級通知
- **等級卡 & 排行榜** — `/rank` 查看個人等級、`/leaderboard` 查看 TOP 10

---

## 🚀 快速開始

### 本機啟動

```bash
# 1. 建立虛擬環境
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 2. 安裝套件
pip install -r requirements.txt

# 3. 設定環境變數
copy .env.example .env       # Windows
# cp .env.example .env       # macOS / Linux
# 編輯 .env 填入你的 Bot Token

# 4. 啟動機器人
python bot.py
```

### Docker 啟動

```bash
# 1. 設定環境變數
copy .env.example .env
# 編輯 .env 填入你的 Bot Token

# 2. 構建並啟動容器
docker-compose up -d --build

# 3. 查看日誌
docker-compose logs -f

# 4. 停止服務
docker-compose down
```

---

## 📁 專案結構

```
discord-channel-bot/
├── bot.py                    # 主程式入口
├── config.py                 # 環境變數設定
├── cogs/
│   ├── __init__.py
│   ├── prefix/               # 前綴指令模組
│   │   └── general.py        # 基本指令 (ping, info)
│   ├── slash/                # 其他 Slash 指令模組
│   │   ├── slash_commands.py # Slash 指令 (userinfo)
│   │   ├── embeds.py         # Embed 訊息指令
│   │   ├── auto_voice.py     # 公開自動語音頻道
│   │   ├── private_room.py   # 私人包廂 & 密碼系統
│   │   ├── skill_commands.py # 湯技角色系統
│   │   └── leveling.py       # 活躍值等級系統
│   ├── repository/           # 共用資料層
│   │   ├── leveling_db.py    # 等級資料庫層 (SQLite)
│   │   └── skill_invite_repository.py # 湯技邀請碼資料層
│   └── service/              # 共用服務層
│       ├── room_registry.py  # 語音房共享狀態管理
│       └── skill_service.py  # 湯技規則與流程
├── data/                     # 資料目錄（等級資料庫）
├── Dockerfile                # Docker 映像定義
├── docker-compose.yml        # Docker Compose 設定
├── requirements.txt
├── .env.example
├── .dockerignore
└── .gitignore
```

---

## ⚙️ 環境變數

在 `.env` 檔案中設定以下環境變數：

| 變數名稱 | 必填 | 預設值 | 說明 |
|---|---|---|---|
| `DISCORD_TOKEN` | ✅ | — | 你的 Discord Bot Token |
| `BOT_PREFIX` | — | `!` | 前綴指令符號 |
| `LOG_LEVEL` | — | `INFO` | 日誌等級（DEBUG / INFO / WARNING / ERROR） |
| `GUILD_ID` | — | — | 開發用伺服器 ID，設定後 Slash 指令會即時同步到該伺服器 |
| `AUTO_VOICE_TRIGGER` | — | `➕ 建立語音頻道` | 公開語音房觸發頻道名稱 |
| `AUTO_VOICE_SUFFIX` | — | `語音房` | 自動建立的語音頻道後綴名 |
| `AUTO_VOICE_LIMIT` | — | `6` | 公開語音房預設人數上限 |
| `PRIVATE_CATEGORY` | — | `🔒 私人湯` | 私人包廂分類名稱 |
| `PRIVATE_TRIGGER` | — | `➕ 開設私人包廂` | 私人包廂觸發頻道名稱 |
| `PRIVATE_SUFFIX` | — | `的包廂` | 私人包廂頻道後綴名 |
| `PRIVATE_LIMIT` | — | `4` | 私人包廂預設人數上限 |
| `PASSWORD_CHANNEL` | — | `🔑｜輸入密碼` | 密碼輸入頻道名稱 |
| `SKILL_PREFIX` | — | `湯技：` | 湯技分類前綴 |
| `SKILL_PANEL_CHANNEL` | — | `湯技` | 湯技面板頻道名稱 |
| `LEVELING_DB_PATH` | — | `data/leveling.db` | 等級資料庫檔案路徑 |
| `XP_PER_MESSAGE_MIN` | — | `15` | 每則訊息最低 XP |
| `XP_PER_MESSAGE_MAX` | — | `25` | 每則訊息最高 XP |
| `XP_MESSAGE_COOLDOWN` | — | `60` | 訊息 XP 冷卻時間（秒） |
| `XP_PER_VOICE_TICK` | — | `10` | 語音掛機每次獲得的 XP |
| `XP_VOICE_INTERVAL` | — | `300` | 語音 XP 計算間隔（秒） |
| `XP_DAILY_BASE` | — | `50` | 每日簽到基礎 XP |
| `LEVELUP_CHANNEL` | — | `等級公告` | 升級公告頻道名稱 |
| `LEVEL_ROLES` | — | （內建 10 階） | 等級里程碑角色，格式：`[lv,"名稱","#HEX"],...` |

---

## 📋 指令一覽

### 基本指令（prefix/general.py）

| 指令 | 說明 |
|---|---|
| `!ping` | 查看機器人延遲 |
| `!info` | 顯示機器人資訊 |

### Slash 指令（slash/slash_commands.py）

| 指令 | 說明 |
|---|---|
| `/userinfo [使用者]` | 查詢使用者資訊 |

### Embed 訊息（slash/embeds.py）

| 指令 | 權限需求 | 說明 |
|---|---|---|
| `/announce <標題> <內容>` | 管理訊息 | 發送格式化的嵌入式公告 |

### 自動語音頻道（slash/auto_voice.py）

| 指令 | 權限需求 | 說明 |
|---|---|---|
| `/voice-name <名稱>` | 房主 | 修改自己語音房的名稱 |
| `/voice-limit <人數>` | 房主 | 設定語音房人數上限 |
| `/voice-kick <使用者>` | 房主 | 將使用者踢出語音房 |
| `/setup-voice` | 管理頻道 | 在所有分類中新增語音觸發頻道 |

### 私人包廂（slash/private_room.py）

| 指令 | 權限需求 | 說明 |
|---|---|---|
| `/voice-invite <使用者>` | 房主 | 邀請使用者加入私人語音房 |
| `/setup-private` | 管理頻道 | 建立私人包廂分類與密碼輸入頻道 |

### 湯技角色系統（slash/skill_commands.py）

| 指令 | 權限需求 | 說明 |
|---|---|---|
| `/skill create <名稱> [emoji]` | 管理角色 | 建立湯技（自動生成角色、分類、頻道、語音觸發，並產生邀請碼） |
| `/skill delete <名稱>` | 管理角色 | 刪除湯技及所有相關資源 |
| `/skill join <邀請碼>` | — | 使用邀請碼加入湯技 |
| `/skill leave <名稱>` | — | 離開指定湯技 |
| `/skill regen <名稱>` | 管理角色 | 重新產生該湯技邀請碼 |
| `/skill list` | — | 列出所有湯技及成員數量 |
| `/skill setup` | 管理角色 | 修復現有湯技的缺失頻道 |
| `/skill panel` | 管理角色 | 發送互動按鈕面板（顯示湯技並可一鍵離開；加入需邀請碼） |

### 活躍值等級系統（slash/leveling.py）

| 指令 | 權限需求 | 說明 |
|---|---|---|
| `/daily` | — | 每日簽到領取活躍值（連續簽到有加成） |
| `/rank [使用者]` | — | 查看等級、排名、進度條 |
| `/leaderboard` | — | 查看活躍值排行榜 TOP 10 |
| `/level-preview` | 管理角色 | 預覽升級公告、等級卡、排行榜的顯示效果 |
| `/level-init` | 管理角色 | 為所有現有成員初始化等級資料並分配 LV1 身分組 |

> 💡 **提示：** 機器人會在 `#湯技` 頻道自動維護互動面板，每次啟動及湯技變更時自動刷新。

---

## 🎮 等級系統詳細說明

### 經驗值來源

| 方式 | XP | 條件 |
|---|---|---|
| 💬 文字聊天 | 15~25（隨機） | 60 秒冷卻，避免洗訊息 |
| 🎙️ 語音掛機 | 10 / 每 5 分鐘 | 頻道需 ≥2 人（不含 Bot） |
| 📅 每日簽到 | 50（基礎） | 連續 7 天 ×1.5、連續 30 天 ×2.0 |

### 等級里程碑

| 等級 | 稱號 | 累積 XP | 約需天數 |
|---|---|---|---|
| LV1 | 🌱 新手湯友 | 0 | — |
| LV5 | 🍵 泡湯常客 | 726 | ~1 天 |
| LV10 | ♨️ 溫泉達人 | 3,158 | ~5 天 |
| LV15 | 🔥 熱湯勇者 | 7,505 | ~13 天 |
| LV20 | 💎 湯中豪傑 | 13,925 | ~24 天 |
| LV25 | ⚡ 傳說湯師 | 22,538 | ~39 天 |
| LV30 | 🌟 湯界名人 | 33,443 | ~58 天 |
| LV35 | 👑 湯池霸主 | 46,725 | ~81 天 |
| LV40 | 🐉 神湯使者 | 62,457 | ~109 天 |
| LV50 | 🏆 湯神 | 101,526 | ~178 天 |

> 經驗曲線公式：`40 × LV^1.2`，以每日活躍 ~570 XP 估算。

---

## 🔧 管理員設定指南

第一次設定機器人？請依照以下步驟操作：

### 步驟一：邀請機器人

1. 前往 [Discord Developer Portal](https://discord.com/developers/applications) 建立應用程式。
2. 在 **Bot** 頁面啟用以下 Privileged Gateway Intents：
   - ✅ **Message Content Intent**
   - ✅ **Server Members Intent**
3. 使用 OAuth2 URL Generator 產生邀請連結，勾選所需權限（見下方權限需求）。
4. 將機器人邀請到你的伺服器。

### 步驟二：設定自動語音頻道

```
/setup-voice
```

執行此指令後，機器人會在伺服器的**所有分類**下建立「➕ 建立語音頻道」觸發頻道。成員加入觸發頻道後，機器人會自動建立專屬語音房。

### 步驟三：設定私人包廂

```
/setup-private
```

執行此指令後，機器人會建立：
- 🔒 **私人包廂**分類
- 📝 **➕ 開設私人包廂**觸發語音頻道
- 🔑 **#🔑｜輸入密碼**文字頻道

成員加入觸發頻道後，機器人會自動建立上鎖的私人語音房並私訊密碼給房主。

### 步驟四：建立湯技

```
/skill create 程式設計 💻
```

機器人會自動建立：
- 🏷️ 對應的 Discord 角色
- 📂 專屬分類
- 💬 文字頻道
- 🔊 語音觸發頻道
- 🔐 一組管理員可發放的湯技邀請碼

### 步驟五：發送湯技面板

```
/skill panel
```

在適當的頻道中執行此指令，機器人會發送一個帶有按鈕的互動面板，讓成員可以一鍵加入或離開湯技。
加入湯技改為邀請碼機制，成員請改用 `/skill join <邀請碼>`；按鈕面板可快速離開既有湯技。

### 步驟六：初始化等級系統

```
/level-init
```

如果伺服器已有成員，執行此指令可為所有現有成員初始化等級資料並分配 LV1 身分組。已有等級角色的成員會自動跳過。

### 步驟七：預覽等級系統

```
/level-preview
```

預覽升級公告、等級卡、排行榜的顯示效果，確認一切正常後即可開始使用。等級系統會自動運作，無需額外設定。

---

## 🤖 Bot 權限需求

### Gateway Intents

| Intent | 用途 |
|---|---|
| Message Content | 讀取前綴指令內容、處理密碼輸入 |
| Server Members | 追蹤成員加入/離開、湯技成員計數 |

### 伺服器權限

| 權限 | 用途 |
|---|---|
| Manage Channels | 建立/刪除語音頻道、湯技分類與頻道 |
| Manage Roles | 建立/刪除湯技角色、等級角色、指派角色給成員 |
| Manage Messages | 管理公告訊息、清理密碼訊息 |
| Connect | 連接語音頻道 |
| Move Members | 將成員移動到自動建立的語音房 |

---

## 📝 授權條款

本專案採用 [MIT License](LICENSE) 授權。
