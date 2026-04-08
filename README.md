# 🤖 Discord Channel Bot

一個功能豐富的 Discord 機器人，使用 [discord.py](https://github.com/Rapptz/discord.py) 建立，採用 Cogs 模組化架構。支援自動語音頻道、私人包廂、湯技角色系統等實用功能，讓你的伺服器管理更輕鬆！

> **Python 3.10+** · **discord.py ≥ 2.3.0** · **支援 Docker 部署**

---

## ✨ 功能總覽

### 🎯 基本指令

使用前綴指令（預設 `!`）快速互動，例如查看延遲與機器人資訊。

### ⚡ Slash 指令

支援 Discord 原生 Slash 指令，包括打招呼、代發訊息、查詢使用者資訊等。

### 📢 公告 Embed

透過 `/announce` 指令發送格式化的嵌入式公告訊息（需要管理訊息權限）。

### 🔊 自動語音頻道系統

- **公開語音房** — 加入「➕ 建立語音頻道」觸發頻道，自動建立專屬語音房，所有人離開後自動刪除。
- **私人包廂** — 加入「➕ 開設私人包廂」觸發頻道，自動建立上鎖的私人語音房。機器人會私訊密碼給房主，其他人需要在 `#🔑｜輸入密碼` 頻道輸入密碼才能進入。
- **房主管理指令** — 改名、設人數上限、邀請或踢出成員。

### 🏷️ 湯技角色系統

一鍵建立「湯技」技能角色，自動生成對應的分類、文字頻道和語音觸發器。成員可自由加入/離開，管理員可發送互動按鈕面板，方便成員一鍵選擇。

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
│   ├── general.py            # 基本指令 (ping, info)
│   ├── slash_commands.py     # Slash 指令
│   ├── embeds.py             # Embed 訊息指令
│   ├── auto_voice.py         # 自動語音頻道 & 私人包廂
│   └── skill_commands.py     # 湯技角色系統
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

---

## 📋 指令一覽

### 基本指令（general.py）

| 指令 | 說明 |
|---|---|
| `!ping` | 查看機器人延遲 |
| `!info` | 顯示機器人資訊 |

### Slash 指令（slash_commands.py）

| 指令 | 說明 |
|---|---|
| `/hello` | 機器人向你打招呼 |
| `/say <訊息>` | 讓機器人代你發送訊息 |
| `/userinfo [使用者]` | 查詢使用者資訊 |

### Embed 訊息（embeds.py）

| 指令 | 權限需求 | 說明 |
|---|---|---|
| `/announce <標題> <內容>` | 管理訊息 | 發送格式化的嵌入式公告 |

### 自動語音頻道（auto_voice.py）

| 指令 | 權限需求 | 說明 |
|---|---|---|
| `/voice-name <名稱>` | 房主 | 修改自己語音房的名稱 |
| `/voice-limit <人數>` | 房主 | 設定語音房人數上限 |
| `/voice-invite <使用者>` | 房主 | 邀請使用者加入私人語音房 |
| `/voice-kick <使用者>` | 房主 | 將使用者踢出語音房 |
| `/setup-voice` | 管理員 | 在所有分類中新增語音觸發頻道 |
| `/setup-private` | 管理員 | 建立私人包廂分類與密碼輸入頻道 |

### 湯技角色系統（skill_commands.py）

| 指令 | 權限需求 | 說明 |
|---|---|---|
| `/skill create <名稱> [emoji]` | 管理角色 | 建立湯技（自動生成角色、分類、頻道、語音觸發） |
| `/skill delete <名稱>` | 管理角色 | 刪除湯技及所有相關資源 |
| `/skill join <名稱>` | — | 加入指定湯技 |
| `/skill leave <名稱>` | — | 離開指定湯技 |
| `/skill list` | — | 列出所有湯技及成員數量 |
| `/skill setup` | 管理角色 | 修復現有湯技的缺失頻道 |
| `/skill panel` | 管理角色 | 發送互動按鈕面板，讓成員一鍵加入/離開湯技 |

> 💡 **提示：** 機器人會在 `#湯技` 頻道自動維護互動面板，每次啟動及湯技變更時自動刷新。

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

### 步驟五：發送湯技面板

```
/skill panel
```

在適當的頻道中執行此指令，機器人會發送一個帶有按鈕的互動面板，讓成員可以一鍵加入或離開湯技。

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
| Manage Roles | 建立/刪除湯技角色、指派角色給成員 |
| Manage Messages | 管理公告訊息、清理密碼訊息 |
| Connect | 連接語音頻道 |
| Move Members | 將成員移動到自動建立的語音房 |

---

## 📝 授權條款

本專案採用 [MIT License](LICENSE) 授權。
