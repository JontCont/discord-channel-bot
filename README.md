# Discord Channel Bot

使用 discord.py 建立的 Discord 機器人，採用 Cogs 模組化架構。

## 功能

- **基本指令** — `!ping`、`!info`
- **Slash Commands** — `/hello`、`/say`、`/userinfo`
- **Embed 訊息** — `/announce`、`/poll`
- **錯誤處理與日誌** — 統一錯誤回應 + logging

## 快速開始

```bash
# 1. 建立虛擬環境
python -m venv venv
venv\Scripts\activate

# 2. 安裝套件
pip install -r requirements.txt

# 3. 設定 Token
copy .env.example .env
# 編輯 .env 填入你的 Bot Token

# 4. 啟動機器人
python bot.py
```

## Docker 啟動

使用 Docker Compose 快速啟動機器人：

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

## 專案結構

```
discord-channel-bot/
├── bot.py              # 主程式入口
├── config.py           # 設定檔
├── cogs/
│   ├── general.py      # 基本指令 (ping, info)
│   ├── slash_commands.py  # Slash 指令
│   └── embeds.py       # Embed 訊息指令
├── Dockerfile          # Docker 映像定義
├── docker-compose.yml  # Docker Compose 設定
├── requirements.txt
├── .env.example
├── .dockerignore
└── .gitignore
```

## 環境變數

機器人所需的環境變數請在 `.env` 檔案中設定：

- **DISCORD_TOKEN** — 你的 Discord Bot Token (必須)
- **BOT_PREFIX** — 指令前綴符號，預設為 `!` (可選)
- **LOG_LEVEL** — 日誌等級，預設為 `INFO` (可選)
