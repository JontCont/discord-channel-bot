# Spec: Bot Clean Architecture Refactoring (SDD)

本規格書遵循 **Spec-Driven Development (SDD)** 流程，嚴格對標 [`.github/skills/bot-architecture/SKILL.md`](file:///D:/repository/discord-channel-bot/.github/skills/bot-architecture/SKILL.md) 規範與 Python 官方標準（PEP 435, PEP 557, PEP 591, PEP 257），逐步將 `apps/bot` 重構為標準的 Clean Layered Architecture。

---

## 1. 重構目標與分層架構 (Target Architecture)

徹底打破原先將 Repository、Service、API 塞在 `cogs/` 內的「綑綁包」現況，重整為五大獨立層級：

```
apps/bot/
├── bot.py                  # 🚀 [Composition Root] 系統開機、載入 container、掛載路由與 Cogs
├── config.py               # ⚙️ [全域環境變數] 讀取 .env
│
├── core/                   # 🏛️ [基礎設施層] 生命週期、容器、全域防禦、常數與枚舉
│   ├── container.py        # 服務註冊中心 (ServiceContainer)：組裝 Repository 與 Service
│   ├── enums.py            # 原生 StrEnum (FeatureModule, VoiceRoomType) (PEP 435)
│   ├── constants/          # 不可變常數與邊界定義 (typing.Final) (PEP 591)
│   │   └── limits.py       # PANEL_TEXT_LIMITS 等字數上限
│   ├── logging.py          # 集中日誌管線
│   └── error_handler.py    # 全域錯誤分類防禦
│
├── models/                 # 📦 [領域模型 / 純資料容器] (PEP 557 dataclass)
│   └── guild_settings.py   # GuildSettings 純資料模型（無驗證字典混雜）
│
├── repository/             # 💾 [資料存取層 / DAL] 純 SQLite 操作
│   ├── guild_settings_db.py
│   ├── leveling_db.py
│   ├── introduction_db.py
│   └── skill_invite_repository.py
│
├── service/                # ⚙️ [業務邏輯層 / Application Layer] 純方法呼叫與驗證
│   ├── guild_settings_service.py
│   ├── leveling_service.py
│   ├── skill_service.py
│   ├── room_registry.py
│   └── alert_service.py
│
├── api/                    # 🌐 [Web 表現層 / Controller] FastAPI APIRouter 模組化
│   ├── __init__.py         # create_api(container) 工廠
│   ├── dependencies.py     # 依賴提供器 (require_session, get_service)
│   ├── auth/               # SessionStore & DiscordOAuth
│   └── routers/            # 業務路由器
│       ├── auth.py
│       ├── guilds.py
│       ├── settings.py
│       └── skills.py
│
└── cogs/                   # 🎮 [Discord 表現層 / Controller] Discord 事件與指令
    ├── prefix/             # 一般前綴指令
    └── slash/              # 斜線指令 (auto_voice, private_room, party, leveling, skill)
```

---

## 2. 執行任務清單 (Task Sequence)

每個步驟完成後皆需通過相應的單元測試，嚴禁越級或跳步執行：

- [x] **Task 1: 純資料模型、常量與枚舉抽離 (Models, Constants & Enums)**
  - 建立 `apps/bot/core/enums.py`：以 `enum.StrEnum` 定義 `FeatureModule`、`VoiceRoomType`。
  - 建立 `apps/bot/core/constants/limits.py`：抽離 `PANEL_TEXT_LIMITS` 等靜態常數（`typing.Final`）。
  - 建立 `apps/bot/models/guild_settings.py`：以 `@dataclass(frozen=True, slots=True)` 建立純數據容器，移除大篇幅文案與限制字典。
  - **驗證**：模型與常數可獨立導入與實例化，無循環依賴（74 項單元測試全數通過）。

- [x] **Task 2: 資料存取層搬遷 (Repository Layer Migration)**
  - 將 `apps/bot/cogs/repository/*` 搬移至 `apps/bot/repository/*`。
  - 建立 `apps/bot/repository/__init__.py` 統一匯出。
  - 在舊目錄建立相容層 Stub，確保舊有引用平滑過渡。
  - **驗證**：74 項單元測試全數通過。

- [x] **Task 3: 業務邏輯層抽離與 Clean Code 瘦身 (Service Layer Refactor)**
  - 將 `apps/bot/cogs/service/*` 搬移至 `apps/bot/service/*`。
  - 建立 `apps/bot/service/__init__.py` 統一匯出。
  - 重構 `apps/bot/service/guild_settings_service.py`：純方法執行，靜態限制引用 `core.constants.limits`，模型引用 `models.guild_settings`。
  - 在舊目錄建立相容層 Stub，更新 `test_room_registry.py`。
  - **驗證**：74 項單元測試全數通過。

- [x] **Task 4: 服務註冊容器與生命週期管控 (DI Container & Infrastructure)**
  - 建立 `apps/bot/core/container.py`：實作 `ServiceContainer`，統一在 `create()` 時初始化 Repository 並注入 Service。
  - 建立 `apps/bot/core/logging.py`：整合 logging 設定與日誌格式。
  - 建立 `apps/bot/core/error_handler.py`：統一處理 Discord CommandError 與全域未攔截例外。
  - 避免 `core/__init__.py` 循環依賴。
  - **驗證**：容器可成功組裝並提供所有 Service 單例（74 項單元測試全數通過）。

- [x] **Task 5: Web API 表現層搬遷與模組化 (FastAPI Presentation Layer)**
  - 將 `apps/bot/cogs/api/` 抽離升格為 `apps/bot/api/`。
  - 修正內部對 `repository/` 與 `service/` 之引用，嚴禁跨層違規。
  - 在舊目錄建立相容層 Stub，更新 `test_api.py`。
  - **驗證**：74 項單元測試全數通過。

- [x] **Task 6: Discord Cogs 控制器適配與 Composition Root (Cogs & bot.py)**
  - 調整 `apps/bot/bot.py`，作為唯一的 Composition Root，統一透過 `ServiceContainer.create()` 初始化並在退出時 `close()`。
  - 接入 `core.logging.setup_logging()` 與 `core.error_handler.handle_command_error()`。
  - 全面更新 `cogs/slash/*` 與各測試對 `repository`、`service`、`models` 的引用，徹底刪除 `cogs/api/`、`cogs/repository/`、`cogs/service/` 舊目錄，`cogs/` 僅保留 `prefix/` 與 `slash/`。
  - 更新 `apps/bot/project.json` 的 compileall 涵蓋全模組。
  - **驗證**：`python -m compileall -q apps/bot` 無錯誤，74 項單元測試全數通過。

- [x] **Task 7: 全面自動化驗證與變更記錄 (Final Verification & CHANGELOG)**
  - 執行 `apps/bot/tests` 全部 74 項單元測試（全數通過）。
  - 執行前端 `pnpm --dir apps/web typecheck` 與 `pnpm --dir apps/web build`（0 錯誤通過）。
  - 執行 `.github/scripts/test_changes.py` 驗證 CHANGELOG 符合 CI 規則（13 項測試通過）。
  - 更新 `CHANGELOG.md` 紀錄（`2026-11-14 - 02`）。
