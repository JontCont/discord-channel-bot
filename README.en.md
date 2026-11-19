# 🤖 Discord Channel Bot

[繁體中文](README.md) · **English**

A feature-rich Discord bot built with [discord.py](https://github.com/Rapptz/discord.py) and a modular Cogs architecture. It provides auto voice channels, private rooms, the "Skill" role system, an activity/leveling system, and more to make server management easier.

> **Python 3.10+** · **discord.py ≥ 2.7.1** · **React/Vite settings dashboard** · **Nx + pnpm** · **Docker ready**

> Note: the bot's in-server names (channels, roles, titles) default to Traditional Chinese. Set `BOT_LANGUAGE` (e.g. `en-US`) to use the matching defaults.

---

## ✨ Features

### 🎯 Basic commands

Prefix commands (default `!`) for quick interaction, such as latency and bot info.

### ⚡ Slash commands

Native Discord slash commands, including user info lookup.

### 📢 Announcement embeds

`/announce` posts a formatted embed announcement (requires Manage Messages).

### 🔊 Auto voice channels

- **Public voice rooms** — join the "➕ Create voice channel" trigger channel to get your own room; it is deleted when everyone leaves.
- **Private rooms** — join the "➕ Open private room" trigger channel to get a locked room. The bot DMs the password to the owner; others enter it in the `#🔑｜輸入密碼` (password) channel to get in.
- **Owner commands** — rename, set a member limit, invite or kick members.

### 📝 Self introductions

- Admins run `/setup-introduction` to create the `#📝｜自我介紹` channel, an info card and a form button under the "General" category (use the `category` option to pick an existing one).
- Members press "Fill in / update introduction" and enter a nickname, interests / games, and optional teammates and active hours.
- Introductions are posted publicly; each member keeps one post per server, and resubmitting updates the original. The post is only recreated if it was deleted.
- Message locations are stored in the SQLite database at `SETTINGS_DB_PATH`, so buttons and updates keep working after a restart. Re-running the setup command refreshes the existing card.
- The card is pinned automatically (and re-pinned at startup); in busy channels, find the form button under "Pinned messages".
- Voluntary: not tied to Skill membership or voice room eligibility, and not affected by the dynamic voice create/delete switches.
- The bot needs View Channel, Read Message History, Send Messages, Embed Links and Pin Messages. Creating the entry point also needs Manage Channels.

### 🎯 Community hub & room creation

- **Shared hub** — name a channel in the General category `🎯｜社群入口` and set the same name as the panel channel in the web dashboard (`SKILL_PANEL_CHANNEL` provides the default). The bot maintains two pinned panels there: Skill selection and room creation. Updating panels never deletes other messages.
- **Open to everyone** — any server member can use it in a text channel they can see and post in; no game Skill is required. `@Bot 開房`, `/party create` and `/party list` still work.
- **Category dropdown** — excludes "General" (`INTRODUCTION_CATEGORY`) and the configured private room category; lists only categories the member can view and the bot can view with Manage Channels, re-checked on submit. The dashboard's party category is only a preselected default. New rooms explicitly allow all members to view, connect and speak; the member limit still applies, and category permissions, existing rooms and private rooms are untouched.
- **Fixed panel** — admins use `/party setup` to refresh the pinned room panel and notification channel.
- **Five-field form** — category (dropdown) / room name / member limit / note / notify roles (multi-select). Notify roles list only the Skills the member has joined and may be left empty; if no Skill is available, a "no mention" option is offered. Discord dropdowns allow at most 25 options, so only the first 25 categories and Skills are shown.
- **Multi-select in the form** — on submit the bot re-checks that the owner still holds the selected Skill roles; it never asks again after the room is created. Requires discord.py 2.7.1+ so the Modal Label / Select optional state is sent correctly.
- **Instant notification** — after a successful submit the bot announces the room in the notification channel immediately (no "Share room" step). Without selected roles it still announces, just without mentions. A notification failure (channel missing or no permission) does not block room creation; the private reply explains why.
- **Notification channel** — the bot creates a default `📣｜揪團通知` in the hub's category (rename via `PARTY_NOTIFICATION_CHANNEL`). It checks View, Send and Embed Links permissions first, and only mentions Skills selected in the form that the member still holds — never arbitrary roles, `@everyone`, `@here` or users.
- **Switches respected** — with dynamic voice creation disabled locally the form still opens, but submitting neither creates a room nor sends a notification.
- **Live room list** — pick a party from the dropdown, join any voice channel, then press "Join party" and the bot moves you to the target room.
- **Permission safety** — the room list and confirmation re-check real view/connect permissions; rooms restricted by admins are never forced open by the bot.
- **Natural-language entry** — mention the bot and type `create server`, `建立房間` or `建立揪團` to get the create button.
- **Auto cleanup** — empty party rooms are deleted automatically and tracked through a persistent registry across restarts.

### 🏷️ Skill role system

One command creates a "Skill" role with its own category, text channel and voice trigger. Members can join or leave freely; admins can view a Skill's role name and invite code, post the interactive panel, and regenerate invite codes.

The Skill panel explains that Skills are interest groups: joining grants the role and channel access, you can join several, and clicking again leaves and hides the channels.

The web dashboard can edit the Skill panel's title, main text and invite-code footer, plus the room lobby panel's title, description, create/view instructions and button labels. Discord Markdown is supported, an empty footer hides it, and the original text is used if nothing is customized. Skill names, member counts and Skill buttons are always generated from the real roles.

Saving updates the configured hub panels immediately, with no restart; changing the title edits the original message instead of posting a new one. If no hub exists yet, run `/party setup` / `/skill panel` first. If the Discord update fails, the dashboard says "Saved, but the panel was not fully updated" and you can save again to retry. Field and total panel length are limited by Discord; the dynamic Skill list counts toward the limit, so shorten the text if it gets too long.

### 🎮 Leveling system

Earn XP from chatting, voice presence and daily check-ins, level up automatically and receive title roles.

- **XP sources** — 💬 chat (15–25 XP), 🎙️ voice presence (10 XP / 5 min), 📅 daily check-in (50 XP)
- **Streak bonus** — 7 days ×1.5, 30 days ×2.0
- **10 milestone titles** — from 🌱 LV1 Newcomer to 🏆 LV50 Bath God
- **Level-up announcements** — posted automatically in the `#等級公告` channel
- **Rank card & leaderboard** — `/rank` for your level, `/leaderboard` for the TOP 10

---

## 🚀 Quick start

### Run locally

```powershell
pnpm install
Copy-Item .env.example .env

# Bot and OAuth/Settings API (port 8000)
uv run --with-requirements apps/bot/requirements.txt python apps/bot/bot.py

# In another terminal, start the web dashboard (port 5173)
pnpm nx run web:dev
```

To tweak the web UI without logging in or running the bot, use mock mode (data lives in memory and resets on reload; `/` opens the feature landing page with a direct button into the mock settings console):

```powershell
pnpm run web:mock   # http://localhost:5173, opens the feature home page and mock server settings
```

For local development set `DISCORD_REDIRECT_URI` to `http://localhost:5173/api/auth/callback`. If your local bot connects to a shared Discord server, set `DYNAMIC_VOICE_CREATE_ENABLED=false` and `DYNAMIC_VOICE_DELETE_ENABLED=false` to avoid creating or deleting dynamic voice rooms.

```powershell
# Verify
pnpm nx run bot:test
pnpm nx run bot:compile
pnpm nx run web:typecheck
pnpm nx run web:build
```

### Docker commands (pnpm / Nx)

The Compose files live in [`docker/`](docker/). These commands run relative to the repository root:

```powershell
pnpm run docker:dev        # build from source and start locally (docker/docker-compose.local.yml)
pnpm run docker:dev:down   # stop and remove
pnpm run docker:dev:logs   # follow logs

pnpm run docker:prod       # start using docker/docker-compose.yml
pnpm run docker:prod:down
pnpm run docker:prod:logs
```

### Changelog records

Every non-merge commit must update the latest entry at the top of [`CHANGELOG.md`](CHANGELOG.md) (heading format `## YYYY-MM-DD - NN` with a summary line below it, grouped by `### feature`, `### bug`, `### chore`, `### docs`, `### refactor`, or `### test`). See [`AGENTS.md`](AGENTS.md) for full rules.

```powershell
python .github/scripts/changes.py latest
python -m unittest discover -s .github/scripts -p test_changes.py
```

---

## 📁 Project structure

```
discord-channel-bot/
├── .github/
│   ├── workflows/            # CI/CD workflows
│   ├── scripts/              # changelog validation (changes.py) and tests
│   └── skills/               # contributor helper skills
├── apps/
│   ├── bot/                  # Discord Bot and FastAPI backend (Clean Layered Architecture)
│   │   ├── bot.py            # Composition Root and entry point
│   │   ├── config.py         # environment variables and locale defaults
│   │   ├── api/              # FastAPI OAuth and Settings API routes
│   │   ├── cogs/             # Discord presentation layer (prefix/ and slash/ commands)
│   │   ├── core/             # DI container, constants, enums, logging and error handler
│   │   ├── models/           # domain data models (e.g. GuildSettings)
│   │   ├── repository/       # SQLite data access layer (DAL)
│   │   ├── service/          # business logic services
│   │   ├── tests/            # Bot/API unit tests
│   │   ├── requirements.txt  # Python dependencies
│   │   └── Dockerfile
│   └── web/                  # React/Vite feature home page & settings dashboard (modular UI & mock mode)
├── docs/
│   └── web-homepage.md       # Web homepage architecture, CSS animations & i18n documentation
├── docker/
│   ├── docker-compose.yml        # Compose file for image deployment
│   ├── docker-compose.local.yml  # local build from source
│   └── docker-compose.base.yml   # shared base config
├── data/                     # data directory (SQLite databases)
├── logs/                     # bot runtime logs
├── AGENTS.md                 # contributor and changelog rules
├── CHANGELOG.md              # per-commit change records
├── nx.json                   # Nx workspace config
├── package.json              # pnpm/Nx root package
├── pnpm-workspace.yaml
└── .env.example
```

---

## ⚙️ Environment variables

Copy [`.env.example`](.env.example) to `.env` and adjust as needed (never commit real tokens or secrets to version control):

| Variable | Required | Default | Description |
|---|---|---|---|
| `DISCORD_TOKEN` | ✅ | — | Discord bot token |
| `DISCORD_CLIENT_ID` | Web | — | Discord OAuth client ID |
| `DISCORD_CLIENT_SECRET` | Web | — | Discord OAuth client secret |
| `DISCORD_REDIRECT_URI` | Web | — | Discord OAuth callback URL |
| `WEB_BASE_URL` | — | `/` | Web URL to return to after OAuth |
| `SESSION_COOKIE_SECURE` | — | `false` | Set to `true` for HTTPS environments |
| `SETTINGS_DB_PATH` | — | `data/settings.db` | Per-guild dynamic settings SQLite path |
| `API_HOST` | — | `0.0.0.0` | Settings API listen host |
| `API_PORT` | — | `8000` | Settings API listen port |
| `BOT_PREFIX` | — | `!` | Prefix command symbol |
| `LOG_LEVEL` | — | `INFO` | Log level (`DEBUG` / `INFO` / `WARNING` / `ERROR`) |
| `BOT_LANGUAGE` | — | `zh-TW` | Default locale (`zh-TW` / `en-US`) |
| `GUILD_ID` | — | — | Development guild ID (instant slash command sync when set) |
| `DYNAMIC_VOICE_CREATE_ENABLED` | — | `true` | Allow creating dynamic voice rooms (`true` / `false`) |
| `DYNAMIC_VOICE_DELETE_ENABLED` | — | `true` | Allow deleting dynamic voice rooms (`true` / `false`) |
| `LEVELING_DB_PATH` | — | `data/leveling.db` | Leveling SQLite database path |

> Other channel names, member limits, and XP parameters have locale-based defaults and can be customized dynamically in the web dashboard; see [`.env.example`](.env.example) for the complete list.

---

## 📋 Commands

### Help and basic commands (slash/help.py, prefix/general.py)

| Command | Permission | Description |
|---|---|---|
| `/help [category]` | — | Show the bot's features and command manual (interactive dropdown) |
| `!help [category]` | — | Text version of the command help |
| `!ping` | — | Show bot latency |
| `!info` | — | Show bot info |

### Slash commands (slash/slash_commands.py)

| Command | Permission | Description |
|---|---|---|
| `/userinfo [user]` | — | Show detailed account and server info for a member or yourself |

### Embeds (slash/embeds.py)

| Command | Permission | Description |
|---|---|---|
| `/announce <title> <content>` | Manage Messages | Post a formatted embed announcement in the current channel |

### Auto voice channels (slash/auto_voice.py)

| Command | Permission | Description |
|---|---|---|
| `/voice-name <name>` | Room owner | Rename the dynamic voice channel you own |
| `/voice-limit <count>` | Room owner | Set your dynamic voice channel's member limit (0 = unlimited, max 99) |
| `/voice-kick <user>` | Room owner | Kick a member from your dynamic voice channel |
| `/setup-voice` | Manage Channels | Create auto-voice trigger channels under every category |

### Private rooms (slash/private_room.py)

| Command | Permission | Description |
|---|---|---|
| `/voice-invite <user>` | Room owner | Invite a member into your private voice room (no password needed) |
| `/setup-private` | Manage Channels | Create the private room category, password channel and room trigger voice channel |
| `/fix-private-perms` | Manage Channels | Repair permissions of all existing private rooms (owner control and isolation) |

### Game parties (slash/party.py)

| Command | Permission | Description |
|---|---|---|
| `/party setup` | Manage Channels | Create or update the pinned room panel and add the share-notification channel in the hub's category |
| `/party create` | — | Open the five-field room form with category and multi-select notify roles |
| `/party list` | — | View active parties and choose one to join |
| `@Bot create server` | — | Get the create-party button by mentioning the bot |

### Skill role system (slash/skill_commands.py)

| Command | Permission | Description |
|---|---|---|
| `/skill create <name> [emoji]` | Manage Roles | Create a Skill (role, category, forum, text and voice channels; DMs the creator an invite code and updates the panel) |
| `/skill delete <name>` | Manage Roles | Delete a Skill (role, category, all related channels and invite codes) |
| `/skill join <invite code>` | — | Join a Skill role and its channels with an invite code |
| `/skill leave <name>` | — | Leave a Skill role and lose access to its channels |
| `/skill info <name> [regenerate]` | Manage Roles | View Skill details (invite code, role, category) and optionally regenerate the code |
| `/skill regen <name>` | Manage Roles | Regenerate a Skill's invite code (the old one is invalidated) |
| `/skill list` | — | List all Skill roles in the server with member counts |
| `/skill setup` | Manage Roles | Check existing Skills, fill in missing channels (forum / chat / voice trigger) and sync role permissions |
| `/skill panel` | Manage Roles | Post the interactive Skill panel in the current channel (buttons to join or leave) |

### Leveling system (slash/leveling.py)

| Command | Permission | Description |
|---|---|---|
| `/daily` | — | Daily check-in for XP (streaks give a multiplier) |
| `/rank [user]` | — | View your or a member's level, title, rank and progress |
| `/leaderboard` | — | View the server's TOP 10 leaderboard |
| `/level-preview` | Manage Roles | Preview the level-up announcement, rank card and leaderboard |
| `/level-init` | Manage Roles | Initialize level data for all existing members and assign the LV1 role |

> 💡 **Tip:** the bot maintains the interactive panel in the `#湯技` channel, refreshing it on every start and whenever Skills change.

---

## 🎮 Leveling details

### XP sources

| Source | XP | Condition |
|---|---|---|
| 💬 Chat | 15–25 (random) | 60 s cooldown to prevent spam |
| 🎙️ Voice presence | 10 per 5 minutes | Channel needs ≥ 2 people (excluding bots) |
| 📅 Daily check-in | 50 (base) | 7-day streak ×1.5, 30-day streak ×2.0 |

### Level milestones

| Level | Title | Total XP | Approx. days |
|---|---|---|---|
| LV1 | 🌱 新手湯友 | 0 | — |
| LV5 | 🍵 泡湯常客 | 726 | ~1 day |
| LV10 | ♨️ 溫泉達人 | 3,158 | ~5 days |
| LV15 | 🔥 熱湯勇者 | 7,505 | ~13 days |
| LV20 | 💎 湯中豪傑 | 13,925 | ~24 days |
| LV25 | ⚡ 傳說湯師 | 22,538 | ~39 days |
| LV30 | 🌟 湯界名人 | 33,443 | ~58 days |
| LV35 | 👑 湯池霸主 | 46,725 | ~81 days |
| LV40 | 🐉 神湯使者 | 62,457 | ~109 days |
| LV50 | 🏆 湯神 | 101,526 | ~178 days |

> XP curve formula: `40 × LV^1.2`, estimated at ~570 XP of activity per day.

---

## 🔧 Admin setup guide

Setting up the bot for the first time? Follow these steps:

### Step 1: Invite the bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create an application.
2. On the **Bot** page enable these Privileged Gateway Intents:
   - ✅ **Message Content Intent**
   - ✅ **Server Members Intent**
3. Use the OAuth2 URL Generator to create an invite link with the required permissions (see below).
4. Invite the bot to your server.

### Step 2: Set up auto voice channels

```
/setup-voice
```

The bot creates a "➕ Create voice channel" trigger channel under **every category**. When members join it, the bot creates a personal voice room.

### Step 3: Set up private rooms

```
/setup-private
```

The bot creates:
- 🔒 a **private room** category
- 📝 a **➕ Open private room** trigger voice channel
- 🔑 a **#🔑｜輸入密碼** text channel

When members join the trigger channel, the bot creates a locked private room and DMs the password to the owner.

### Step 4: Create a Skill

```
/skill create Programming 💻
```

The bot creates:
- 🏷️ a Discord role
- 📂 a dedicated category
- 💬 a text channel
- 🔊 a voice trigger channel
- 🔐 a Skill invite code (DMed to the creator for admins to distribute)

### Step 5: Post the Skill panel

```
/skill panel
```

Run it in a suitable channel and the bot posts an interactive panel with buttons.
Joining a Skill uses invite codes: members run `/skill join <invite code>`; the button panel lets them quickly leave existing Skills. Admins can change a code with `/skill regen <name>`.

### Step 6: Initialize the leveling system

```
/level-init
```

If the server already has members, this initializes level data for all of them and assigns the LV1 role. Members who already have a level role are skipped.

### Step 7: Preview the leveling system

```
/level-preview
```

Preview the level-up announcement, rank card and leaderboard; once everything looks right you are done. The leveling system runs automatically with no further setup.

---

## 🤖 Bot permissions

### Gateway intents

| Intent | Purpose |
|---|---|
| Message Content | Read prefix command content and handle password entry |
| Server Members | Track member joins/leaves and Skill member counts |

### Server permissions

| Permission | Purpose |
|---|---|
| Manage Channels | Create/delete voice channels, Skill categories and channels |
| Manage Roles | Create/delete Skill and level roles, assign roles to members |
| Manage Messages | Manage announcements and clean up password messages |
| Connect | Connect to voice channels |
| Move Members | Move members into auto-created voice rooms |

---

## 📝 License

This project is licensed under the [MIT License](LICENSE).
