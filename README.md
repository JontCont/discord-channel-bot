# 🤖 Discord Channel Bot

一個功能豐富的 Discord 機器人，使用 [discord.py](https://github.com/Rapptz/discord.py) 建立，採用 Cogs 模組化架構。支援自動語音頻道、私人包廂、湯技角色系統、活躍值等級系統等實用功能，讓你的伺服器管理更輕鬆！

> **Python 3.10+** · **discord.py ≥ 2.7.1** · **支援 Docker 部署**

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

### 📝 自我介紹

- 管理員執行 `/setup-introduction`，在「一般」分類建立 `#📝｜自我介紹` 與說明卡、表單按鈕；可透過 `category` 參數選擇既有分類。
- 成員按「填寫／更新自我介紹」，填寫稱呼、興趣／常玩遊戲，以及選填的同好與出沒時間。
- 介紹會公開發布；同一伺服器每位成員只維護一篇，再次提交更新原文。原文已被刪除時才重建。
- 訊息位置保存在 `SETTINGS_DB_PATH` 的 SQLite 資料庫；Bot 重啟後按鈕與更新功能仍有效。重跑設定指令會更新既有說明卡。
- 說明卡會自動置頂，Bot 啟動時也會補上既有說明卡的置頂；留言多時可從頻道「置頂訊息」找到表單按鈕。
- 自願填寫，不綁定湯技或語音房資格，也不受動態語音房建立／刪除開關影響。
- Bot 需具備檢視頻道、讀取訊息歷史、傳送訊息、嵌入連結及釘選訊息權限；建立入口時還需要管理頻道權限。

### 🎯 社群入口與開房

- **共用入口** — 將一般分類中的入口命名為 `🎯｜社群入口`，並將 Web 後台的面板頻道設為相同名稱（`SKILL_PANEL_CHANNEL` 提供預設值）。Bot 啟動後會維護湯技選擇與開房兩張置頂面板；更新面板不會刪除其他訊息。
- **不限湯技** — 所有伺服器成員都可在自己看得到且能發文的文字頻道操作，不必加入遊戲湯技。原本的 `@Bot 開房`、`/party create`、`/party list` 皆保留。
- **分類下拉選擇** — 排除「一般」（`INTRODUCTION_CATEGORY`）與伺服器設定的私人包廂分類；只列成員可檢視、Bot 可檢視且有管理頻道權限的 Discord 分類，送出時重新檢查。後台的揪團類別只作為可用時的預選值。新房明確開放所有成員檢視、連線與發言，人數上限仍有效，不改動分類本身、既有房間或私人包廂的權限。
- **固定面板** — 管理員可用 `/party setup` 更新置頂開房面板與通知頻道。
- **五欄表單** — 僅包含「建立分類（下拉）／房名／人數／備註／通知身分（下拉多選）」。通知身分僅列已加入的湯技，可不選；沒有可通知湯技時提供不標記選項。Discord 下拉選單最多 25 個選項，分類與湯技最多顯示前 25 個。
- **表單內多選通知身分** — 建立時保存所選湯技，分享前重新確認房主仍擁有這些身分；不會在建房後再要求選一次通知身分。使用 discord.py 2.7.1+，以確保 Modal Label／Select 正確傳送選填狀態。
- **自願分享** — 建立成功的私人回覆提供「分享房間」按鈕；只有房主選擇分享才會發布，不分享並不代表私人房。分享入口有效五分鐘。
- **可指定分享位置** — Bot 在社群入口同一分類建立預設的 `📣｜揪團通知`（可由 `PARTY_NOTIFICATION_CHANNEL` 改名）。分享時可另選同一伺服器的文字頻道；送出前檢查房主的檢視、發文權限，以及 Bot 的檢視、發文與嵌入連結權限。未指定時使用預設通知頻道；只標記表單中選取且目前仍擁有的湯技，不允許任意角色、`@everyone`、`@here` 或使用者標記。
- **開關維持有效** — 本機停用動態語音房建立時仍可開啟表單，但送出不會建房或發通知。
- **即時房間列表** — 從下拉選單挑選揪團後，成員先加入任一語音頻道，再按下「進入揪團」，Bot 才會移入目標房間。
- **既有權限保護** — 房間列表與確認加入仍會檢查實際檢視及連線權限；管理員另行限制的房間不會被 Bot 強制移入。
- **自然語句入口** — 提及 Bot 並輸入 `create server`、`建立房間` 或 `建立揪團`，即可取得建立按鈕。
- **自動清理** — 揪團房沒人後自動刪除，並透過持久化 registry 在 Bot 重啟後繼續追蹤。

### 🏷️ 湯技角色系統

一鍵建立「湯技」技能角色，自動生成對應的分類、文字頻道和語音觸發器。成員可自由加入/離開；管理員可查看湯技角色名稱與邀請碼、發送互動面板，並可視需求重新產生邀請碼。

湯技面板會說明這是興趣分組：加入即可取得身分組與對應頻道存取權，可同時加入多個；再次點擊按鈕則離開並收起專屬頻道。

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

```powershell
pnpm install
Copy-Item .env.example .env

# Bot 與 OAuth/Settings API（port 8000）
uv run --with-requirements apps/bot/requirements.txt python apps/bot/bot.py

# 另一個終端啟動 Web（port 5173）
pnpm nx run web:dev
```

本機開發時，將 `DISCORD_REDIRECT_URI` 設為
`http://localhost:5173/api/auth/callback`。正式環境必須使用 HTTPS，並設定
`SESSION_COOKIE_SECURE=true`。

本機若連到共用 Discord 伺服器，請將 `DYNAMIC_VOICE_CREATE_ENABLED=false`
及 `DYNAMIC_VOICE_DELETE_ENABLED=false`，避免建立或刪除動態語音房。
兩個開關獨立控制公開自動房、私人包廂及揪團房；刪除開關也涵蓋空房事件、
每分鐘清理及遺失登記的私人空房清理。停用建立時，揪團表單會顯示停用提示。
未設定時兩者預設為 `true`；修改後需重啟 Bot，且 Web 後台不能覆寫這些開關。
這不是完整唯讀模式：設定用入口頻道的建立、既有房間管理及其他 Bot 功能不受影響。

```powershell
# 驗證
pnpm nx run bot:test
pnpm nx run bot:compile
pnpm nx run web:typecheck
pnpm nx run web:build
```

### NAS Docker 啟動

NAS 只需要 `docker-compose.yml` 與 `.env`，不需要上傳 source code。先建立
`data`、`logs` 目錄，再拉取 GHCR images 並啟動：

```bash
mkdir -p data logs
docker compose pull
docker compose up -d
docker compose logs -f
```

若 GHCR package 設為 private，請先登入：

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

更新版本時再次執行 `docker compose pull` 與 `docker compose up -d`。預設使用
`latest`，也可在 `.env` 以 `BOT_IMAGE`、`WEB_IMAGE` 指定固定版本。

在 GitHub 儲存庫的 **Settings → Secrets and variables → Actions → New repository secret**
新增 `DEPLOY_WEBHOOK_URL`，值為正式部署 webhook 的基底網址（不含 `/:project`）。
網址不存入原始碼；未設定此 Secret 時，部署步驟會明確失敗。

Pipeline 依變更檔案選擇建置目標：

- `apps/web/**` 或 Web 共用建置設定（`package.json`、pnpm lockfile/workspace、
  `nx.json`、`tsconfig.base.json`、`.dockerignore`）：只建置 Web，不執行 Bot CI。
- `apps/bot/**`：只執行 Bot CI 並建置 Bot。
- 兩邊都有變更或修改 `.github/workflows/cicd.yml`：建置兩個 image。
- 純文件等不影響上述路徑的變更：略過 Bot CI、image 建置與部署，仍檢查更新紀錄。
- 手動執行與版本標籤：保留完整建置兩個 image 的行為。

CI/CD 在預設分支的 `latest` image 成功推送至 GHCR 後，會分別 POST 至
`${DEPLOY_WEBHOOK_URL}/:project`（自動處理基底網址末尾的 `/`）：

| Project | Image | Tag |
|---|---|---|
| `discord-channel-bot` | `ghcr.io/jontcont/discord-channel-bot-bot` | `latest` |
| `discord-channel-bot-web` | `ghcr.io/jontcont/discord-channel-bot-web` | `latest` |

Pull Request 與版本標籤建置不會觸發部署 webhook；手動執行預設分支的 workflow
則會觸發。Webhook 連線失敗、逾時或回傳 HTTP 錯誤時，對應的建置 job 會失敗。
回應必須是單一 JSON 物件，且 `status` 為 `success`、`project` 與 `image`（含
`:latest`）符合本次部署目標，否則 job 也會失敗。回應會保留在 Actions 日誌中，
包含 webhook 提供的 `timestamp`。
原有的 Discord webhook 通知保持不變。

### 每次提交的更新紀錄

每個新進的非 merge commit（包含純文件修改）都必須更新
[`changes.md`](changes.md) 最上方的最新紀錄。使用 `## YYYY-MM-DD - 摘要`
作為標題，再用 `### feature`、`### bug`、`### chore`、`### docs`、
`### refactor`、`### test` 分組。只保留有內容的分類，每個分類至少一個非空的
`- ` 項目，不能重複分類；舊紀錄保留在下方。
原有的 [`CHANGELOG.md`](CHANGELOG.md) 保留為歷史版本日誌。

CI 會逐一檢查 push／Pull Request 範圍內的非 merge commit；沒有更新檔案、
刪除檔案或只修改舊紀錄都會阻擋建置。新分支首次 push（沒有前一個 SHA）只檢查
最新的非 merge commit；手動執行與版本標籤只驗證最新紀錄格式。
Discord 通知直接讀取最上方的最新紀錄，不再從 commit 訊息組合更新內容。

可請 Copilot 使用專案內的
[`update-changes` Skill](.github/skills/update-changes/SKILL.md) 協助補寫；
規範也記錄在 [`AGENTS.md`](AGENTS.md)。這不需要 CI 呼叫 Copilot 或其他 AI 服務。
若既有 commit 漏寫，單純追加一個紀錄 commit 仍不會通過；需要先確認是否允許修改
該 commit 的歷史，Skill 不會自行 amend、rebase 或 force-push。

```powershell
python .github/scripts/changes.py latest
python -m unittest discover -s .github/scripts -p test_changes.py
python .github/scripts/changes.py check --base BASE_SHA --head HEAD_SHA
```

### 本機 Docker 建置

完整 source code 環境可使用本機 Compose 自行建置 images：

```powershell
docker compose -f docker-compose.local.yml up -d --build
```

---

## 📁 專案結構

```
discord-channel-bot/
├── apps/
│   ├── bot/
│   │   ├── bot.py            # Bot 與 API 主程式入口
│   │   ├── config.py         # Python 環境變數設定
│   │   ├── cogs/             # Discord、API、資料與服務模組
│   │   ├── tests/            # Bot/API 單元測試
│   │   ├── requirements.txt  # Python dependencies
│   │   ├── Dockerfile
│   │   └── project.json      # Nx bot project
│   └── web/                  # React/Vite 設定後台
├── data/                     # 資料目錄（等級資料庫）
├── logs/                     # Bot runtime logs
├── docker-compose.yml        # Docker Compose 設定
├── nx.json                   # Nx workspace 設定
├── package.json              # pnpm/Nx root package
├── pnpm-workspace.yaml
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
| `DISCORD_CLIENT_ID` | Web 必填 | — | Discord OAuth client ID |
| `DISCORD_CLIENT_SECRET` | Web 必填 | — | Discord OAuth client secret |
| `DISCORD_REDIRECT_URI` | Web 必填 | — | Discord OAuth callback URL |
| `WEB_BASE_URL` | — | `/` | OAuth 完成後導回的 Web URL |
| `SESSION_COOKIE_SECURE` | — | `false` | HTTPS 正式環境應設為 `true` |
| `SETTINGS_DB_PATH` | — | `data/settings.db` | Guild 動態設定資料庫 |
| `API_HOST` | — | `0.0.0.0` | Settings API listen host |
| `API_PORT` | — | `8000` | Settings API listen port |
| `BOT_IMAGE` | — | `ghcr.io/jontcont/discord-channel-bot-bot:latest` | NAS 使用的 Bot image |
| `WEB_IMAGE` | — | `ghcr.io/jontcont/discord-channel-bot-web:latest` | NAS 使用的 Web image |
| `BOT_PREFIX` | — | `!` | 前綴指令符號 |
| `LOG_LEVEL` | — | `INFO` | 日誌等級（DEBUG / INFO / WARNING / ERROR） |
| `BOT_LANGUAGE` | — | `zh-TW` | 語系預設（如 `zh-TW` / `en-US`）。未自訂名稱時會套用對應語言預設值 |
| `GUILD_ID` | — | — | 開發用伺服器 ID，設定後 Slash 指令會即時同步到該伺服器 |
| `INTRODUCTION_CATEGORY` | — | 依語系 | 自我介紹分類名稱（繁中預設「一般」） |
| `INTRODUCTION_CHANNEL` | — | 依語系 | 自我介紹文字頻道名稱（繁中預設「📝｜自我介紹」） |
| `AUTO_VOICE_TRIGGER` | — | 依語系 | 公開語音房觸發頻道名稱 |
| `DYNAMIC_VOICE_CREATE_ENABLED` | — | `true` | 是否允許建立動態語音房，只接受 `true` / `false` |
| `DYNAMIC_VOICE_DELETE_ENABLED` | — | `true` | 是否允許刪除動態語音房，只接受 `true` / `false` |
| `AUTO_VOICE_SUFFIX` | — | 依語系 | 自動建立的語音頻道後綴名 |
| `AUTO_VOICE_LIMIT` | — | `6` | 公開語音房預設人數上限 |
| `PRIVATE_CATEGORY` | — | 依語系 | 私人包廂分類名稱 |
| `PRIVATE_TRIGGER` | — | 依語系 | 私人包廂觸發頻道名稱 |
| `PRIVATE_SUFFIX` | — | 依語系 | 私人包廂頻道後綴名 |
| `PRIVATE_LIMIT` | — | `4` | 私人包廂預設人數上限 |
| `PASSWORD_CHANNEL` | — | 依語系 | 密碼輸入頻道名稱 |
| `SKILL_PREFIX` | — | 依語系 | 湯技分類前綴 |
| `SKILL_PANEL_CHANNEL` | — | 依語系 | 湯技與開房共用入口名稱，繁中預設「🎯｜社群入口」 |
| `PARTY_NOTIFICATION_CHANNEL` | — | 依語系 | 共用入口同分類的分享通知頻道，繁中預設「📣｜揪團通知」 |
| `SKILL_PANEL_DIRECT_JOIN_SKILLS` | — | `鍛造術,遊戲術,墨繪術,幻想術` | `/skill panel` 未指定 direct_join_skills 時，預設可按鈕直接加入的湯技清單 |
| `LEVELING_DB_PATH` | — | `data/leveling.db` | 等級資料庫檔案路徑 |
| `XP_PER_MESSAGE_MIN` | — | `15` | 每則訊息最低 XP |
| `XP_PER_MESSAGE_MAX` | — | `25` | 每則訊息最高 XP |
| `XP_MESSAGE_COOLDOWN` | — | `60` | 訊息 XP 冷卻時間（秒） |
| `XP_PER_VOICE_TICK` | — | `10` | 語音掛機每次獲得的 XP |
| `XP_VOICE_INTERVAL` | — | `300` | 語音 XP 計算間隔（秒） |
| `XP_DAILY_BASE` | — | `50` | 每日簽到基礎 XP |
| `LEVELUP_CHANNEL` | — | 依語系 | 升級公告頻道名稱 |
| `LEVEL_ROLES` | — | （內建 10 階，依語系） | 等級里程碑角色，格式：`[lv,"名稱","#HEX"],...` |

---

## 📋 指令一覽

### 說明與基本指令（slash/help.py, prefix/general.py）

| 指令 | 權限需求 | 說明 |
|---|---|---|
| `/help [類別]` | — | 顯示機器人各項功能與指令使用手冊（支援互動下拉選單切換） |
| `!help [類別]` | — | 顯示文字版指令說明 |
| `!ping` | — | 查看機器人延遲 |
| `!info` | — | 顯示機器人資訊 |

### Slash 指令（slash/slash_commands.py）

| 指令 | 權限需求 | 說明 |
|---|---|---|
| `/userinfo [使用者]` | — | 查看指定成員或自己的詳細帳號與伺服器資訊 |

### Embed 訊息（slash/embeds.py）

| 指令 | 權限需求 | 說明 |
|---|---|---|
| `/announce <標題> <內容>` | 管理訊息 | 在當前頻道發送格式化的嵌入式 (Embed) 公告訊息 |

### 自動語音頻道（slash/auto_voice.py）

| 指令 | 權限需求 | 說明 |
|---|---|---|
| `/voice-name <名稱>` | 房主 | 重新命名你目前所擁有的動態語音頻道 |
| `/voice-limit <人數>` | 房主 | 設定你的動態語音頻道人數上限（0 為無限制，最大 99） |
| `/voice-kick <使用者>` | 房主 | 將指定成員踢出你的動態語音頻道 |
| `/setup-voice` | 管理頻道 | 在伺服器各分類下批次建立自動語音觸發頻道 |

### 私人包廂（slash/private_room.py）

| 指令 | 權限需求 | 說明 |
|---|---|---|
| `/voice-invite <使用者>` | 房主 | 邀請指定成員進入你目前所屬的私人語音包廂（免輸密碼） |
| `/setup-private` | 管理頻道 | 建立私人包廂分類、密碼驗證頻道與包廂觸發語音頻道 |
| `/fix-private-perms` | 管理頻道 | 修復所有現有私人包廂的權限（確保房主管理權與隔離設定） |

### 遊戲揪團（slash/party.py）

| 指令 | 權限需求 | 說明 |
|---|---|---|
| `/party setup` | 管理頻道 | 建立或更新置頂開房面板，並在共用入口同分類補建分享通知頻道 |
| `/party create` | — | 開啟五欄開房表單，可選分類與多選通知身分 |
| `/party list` | — | 查看進行中的揪團並選擇加入 |
| `@Bot create server` | — | 以提及方式取得建立揪團按鈕 |

### 湯技角色系統（slash/skill_commands.py）

| 指令 | 權限需求 | 說明 |
|---|---|---|
| `/skill create <名稱> [emoji]` | 管理角色 | 建立新湯技（包含專屬身分組、分類、論壇討論區、文字聊天、語音頻道、生成邀請碼私訊建立者並更新面板） |
| `/skill delete <名稱>` | 管理角色 | 刪除指定湯技（包含身分組、分類、所有相關頻道與邀請碼） |
| `/skill join <邀請碼>` | — | 輸入邀請碼加入指定湯技身分組與專屬頻道 |
| `/skill leave <名稱>` | — | 離開指定湯技身分組並移除專屬頻道存取權 |
| `/skill info <名稱> [regenerate]` | 管理角色 | 查看湯技詳細資訊（邀請碼、身分組、分類）並可選擇重新產生邀請碼 |
| `/skill regen <名稱>` | 管理角色 | 為指定湯技重新產生新的邀請碼（舊碼作廢） |
| `/skill list` | — | 列出伺服器中所有的湯技身分組與目前成員人數 |
| `/skill setup` | 管理角色 | 檢查既有湯技並自動補齊缺失的頻道（論壇/聊天/語音觸發）與同步身分組權限 |
| `/skill panel` | 管理角色 | 在當前頻道發送湯技互動選單面板（可點擊按鈕直接加入或離開湯技） |

### 活躍值等級系統（slash/leveling.py）

| 指令 | 權限需求 | 說明 |
|---|---|---|
| `/daily` | — | 每日簽到領取活躍值 XP（累積連續天數享倍率加成） |
| `/rank [使用者]` | — | 查看個人或指定成員的等級、稱號、排名與升級進度 |
| `/leaderboard` | — | 查看伺服器活躍值排行榜 TOP 10 |
| `/level-preview` | 管理角色 | 預覽升級公告、等級卡與排行榜的顯示效果 |
| `/level-init` | 管理角色 | 為伺服器所有現有成員初始化等級資料並分配 LV1 身分組 |

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
- 🔐 一組湯技邀請碼（會私訊建立者，供管理員發放）

### 步驟五：發送湯技面板

```
/skill panel
```

在適當的頻道中執行此指令，機器人會發送一個帶有按鈕的互動面板。
加入湯技採邀請碼機制，成員請使用 `/skill join <邀請碼>`；按鈕面板可快速離開既有湯技。管理員如需更換邀請碼，可使用 `/skill regen <名稱>`。

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
