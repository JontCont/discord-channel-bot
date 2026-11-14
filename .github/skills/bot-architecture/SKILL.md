---
name: bot-architecture
description: Reference guide for Discord Channel Bot architecture, module enable switches, Python environment configuration, and party room conventions.
---

# Bot Architecture & Development Guide

## 1. Python 開發環境與直譯器設定（解決 Unresolved Import）

當編輯器（VS Code / Antigravity IDE）提示 `Warning: Import "discord.ext" could not be resolved` 或找不到 `config`、`cogs` 時，原因是專案根目錄缺少綁定套件的 `.venv` 以及 `apps/bot` 的搜尋路徑。

### 解決方案
1. 建立並同步虛擬環境：
   ```bash
   uv venv .venv
   uv pip install -r apps/bot/requirements.txt
   ```
2. 設定 [`.vscode/settings.json`](file:///D:/repository/discord-channel-bot/.vscode/settings.json)：
   ```json
   {
     "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
     "python.analysis.extraPaths": [
       "${workspaceFolder}/apps/bot"
     ]
   }
   ```
3. 在 VS Code 中按下 `Ctrl+Shift+P` 執行 `Python: Select Interpreter`，選取 `${workspaceFolder}/.venv/Scripts/python.exe`。

---

## 2. 模組功能開關架構（Enable Switches）

伺服器後台與資料庫提供 5 大功能開關，預設皆為 `True`：
- `auto_voice_enabled`: 自動動態語音頻道
- `private_rooms_enabled`: 私人包廂與密碼房
- `skills_enabled`: 湯技角色系統與領取面板
- `party_enabled`: 社群與揪團語音房大廳
- `leveling_enabled`: 活躍值經驗值計算與升級通知

### 規範與行為
1. **Dashboard 聯動**：
   - Dashboard 卡片牆上的 Switch 可一鍵啟閉任一模組。
   - 左側側邊欄目錄會**動態過濾**，未啟用的模組自動隱藏（Hide）。
2. **Bot 攔截**：
   - 各模組於 Voice State Update、Slash 指令或按鈕 Callback 時，先讀取 `settings.<module>_enabled`，停用時即時攔截並提示伺服器成員。

---

## 3. 揪團開房原則（Party System）

- **Global Member 自由使用**：揪團功能不綁定任何單一身分組，任何伺服器成員均可開房。
- **無預設類別限制**：移除 `party_category` 限制，成員開啟表單時，系統自動列出該成員與 Bot 共同可用的分類（預設選取第一個），開房者可隨意切換。

---

## 4. 後端分層架構規範（Clean Layered Architecture）

原本將 `repository/`（資料存取）與 `service/`（業務邏輯）塞在 `cogs/` 底下的方式混淆了控制器與領域層。重構後的標準架構將各層抽離為獨立一等公民：

```
apps/bot/
├── bot.py                  # 🚀 [主程式進入點] 僅做 bootstrap、註冊 error handler 與啟動
├── config.py               # ⚙️ [設定檔] 環境變數讀取與預設常數
│
├── core/                   # 🏛️ [基礎設施層] 生命週期管控、DI 容器、日誌管線、全域防禦
│   ├── container.py        # 服務註冊中心 (ServiceContainer)：集中組裝 Repository 與 Service
│   ├── logging.py          # 集中日誌配置與脫敏 (RotatingFileHandler / StreamHandler)
│   ├── error_handler.py    # 全域錯誤分類防禦 (Slash Tree / Events / FastAPI 500)
│   └── alerts.py           # 異常即時發報機 (Discord Embed 告警，含重複錯誤節流)
│
├── repository/             # 💾 [資料存取層 / Data Access Layer]
│   ├── guild_settings_db.py
│   ├── leveling_db.py
│   ├── introduction_db.py
│   └── skill_invite_repository.py
│
├── service/                # ⚙️ [業務邏輯層 / Application Layer]
│   ├── guild_settings_service.py
│   ├── leveling_service.py
│   ├── skill_service.py
│   ├── room_registry.py
│   └── alert_service.py
│
├── api/                    # 🌐 [Web 表現層 / Web Controller]
│   └── app.py              # FastAPI 路由，只依賴 service，不直連 repository
│
└── cogs/                   # 🎮 [Discord 表現層 / Discord Controller]
    ├── prefix/             # 一般文字前綴指令
    └── slash/              # Discord 斜線指令，只依賴 service，不直連 repository
```

### 依賴流向守則
1. **單向呼叫，嚴禁越級**：
   - `cogs/`（Discord）與 `api/`（Web）**只能呼叫 `service/`**，絕對不可直接 `import` 或實例化 `repository/`。
   - `service/` 只負責業務邏輯與驗證，對下呼叫 `repository/`，且**不得依賴 Discord UI 物件**（如 `Interaction`、`Message`），確保同一套 Service 可在 Web 與 Discord 共用。
2. **集中依賴注入（DI）**：
   - 所有的資料庫初始化與服務組裝統一在 `core/container.py`（`ServiceContainer.create()`）完成。
   - 表現層模組初始化時直接取得注入好的容器，禁止在模組內部私自 `new` 資料庫或服務。

---

## 5. 資源建立與功能開發守則（Feature Creation Rules）

開發新功能或建立資源（Create）時，必須遵守以下規範：

### 1. 開發順序（由下而上）
`repository/`（SQL 查詢與實體存取）➔ `service/`（業務驗證與邏輯邊界）➔ `core/container.py`（註冊注入）➔ `cogs/` 或 `api/`（介面控制器與錯誤回饋）➔ 單元測試與 `CHANGELOG.md`。

### 2. 防禦性建立原則
- **防重複與衝突**：1 位成員同時間只能擁有 1 個進行中房間；名稱類別比對一律先以 `casefold()` 與空白去除檢查。
- **權限預檢（Least Privilege）**：在呼叫 Discord API 建立頻道前，先確認 Bot 在目標分類具備 `view_channel` 與 `manage_channels` 權限；管理型功能驗證執行者權限。
- **資源孤島防範（Lifecycle Clean）**：動態建立的語音房必須立即註冊進 `RoomRegistry`，最後一人離開房間時必須全自動刪除，不留幽靈死房。
- **開關守衛（Feature Flag Guard）**：進入建立流程前，一律先驗證 `settings.<module>_enabled`，停用時即刻中斷並友善提示。

---

## 6. API 模組化切分規範（APIRouter 模式）

避免將所有端點堆疊在單一檔案中，`api/` 必須依照業務領域切分為獨立路由器（Routers）：

```
apps/bot/api/
├── __init__.py           # 🚀 create_api() 進入點：裝配 FastAPI、掛載 routers、lifespan 與全域錯誤處理
├── dependencies.py       # 🛡️ 注入相依（require_session, require_guild）
├── auth/                 # 🔐 驗證模組（SessionStore 與 DiscordOAuth 客戶端）
└── routers/              # 📂 業務路由器（相當於 Controllers）
    ├── auth.py           # /api/auth/*（登入、回傳、登出、/me）
    ├── guilds.py         # /api/guilds/*（伺服器、頻道、類別清單）
    ├── settings.py       # /api/guilds/{id}/settings（讀取與儲存設定）
    └── skills.py         # /api/guilds/{id}/skills（湯技 CRUD 與重設邀請碼）
```

---

## 7. 程式碼註解與 Docstrings 文檔規範（Documentation Standard）

為了讓未來的維護者（包括一段時間後回頭看程式碼的自己）能一眼看懂意圖，所有 Python 與 TypeScript 程式碼必須遵守以下註解準則（對標 C# 的 XML Doc 嚴謹度）：

### 1. 檔案頂部模組註解（File Header Docstring）
每個 `.py` 檔案開頭必須明確標註：
- **職責（Responsibility）**：此檔案所屬分層與核心功能。
- **依賴說明（Dependencies）**：呼叫哪些下層服務或模組。

```python
"""
Guild Settings Service (Domain Layer).

負責管理伺服器設定的業務規則校驗、快取與資料存取封裝。
相依層級：依賴 GuildSettingsDB（Repository Layer），不依賴任何表現層物件。
"""
```

### 2. 類別與方法 Docstrings（Google Style）
所有 Public 類別、方法與函式必須包含 Docstrings，說明參數意義、回傳值與可能拋出的例外：

```python
async def update(self, guild_id: int, changes: Mapping[str, Any]) -> GuildSettings:
    """更新伺服器設定並執行領域驗證。

    Args:
        guild_id: Discord 伺服器 Snowflake ID。
        changes: 欲更新的欄位字典鍵值對。

    Returns:
        更新並持久化後的 GuildSettings 實體。

    Raises:
        ValueError: 包含未知鍵值、格式不合、或違反排他唯一性（如觸發字重名）。
        TypeError: changes 參數非 Mapping 字典型別。
    """
```

### 3. 行內註解原則（"Why, not What"）
- ❌ **避免陳述廢話**：例如 `# 將 x 加 1`、`# 呼叫 db`。
- ✅ **記錄設計決策與業務原因（Why）**：
  - 例如：`# 避免同時建立多個同名分類：先透過 casefold 與 strip 排除假差異`
  - 例如：`# Discord 限制 Embed 總字數上限為 6,000 字元，故各面板欄位總和需預先約束`
  - 例如：`# 節流防灌爆：同類型例外於 60 秒內只發送一次 Webhook 告警`

### 4. FastAPI 端點標註（OpenAPI 文檔化）
每個 API Route 必須加上 `summary` 與 `description`，讓自動產生的 Swagger / OpenAPI 文件清晰可用：
```python
@router.put("/{guild_id}/settings", summary="更新伺服器後台設定", response_model=SettingsResponse)
```

---

## 8. 配置與執行程式碼徹底解耦規範（Separation of Config & Code）

為落實 Clean Code 與單一職責原則（SRP），嚴禁將靜態配置、UI 預設文字、字數限制字典與業務執行程式碼（Call Methods）綑綁在同一 `.py` 檔案中。

### 1. Python 原生 Enum 與參數字典架構
Python 標準庫提供完整的 `enum` 模組（自 Python 3.4 內建，Python 3.11+ 更提供原生 `StrEnum`）。
在專案中，統一採用「**原生 StrEnum + 型別標註字典（Typed Mapping）**」實現枚舉與參數映射：

```python
# apps/bot/core/enums.py
from enum import StrEnum

class FeatureModule(StrEnum):
    """5 大功能模組原生字串枚舉。
    繼承 StrEnum 可直接當成 str 使用（免 .value，零序列化成本）。
    """
    AUTO_VOICE = "auto_voice"
    PRIVATE_ROOMS = "private_rooms"
    SKILLS = "skills"
    PARTY = "party"
    LEVELING = "leveling"

class VoiceRoomType(StrEnum):
    """動態房間類型。"""
    AUTO = "auto"
    PRIVATE = "private"
    PARTY = "party"
```

當需要為 Enum 綁定專屬參數時，在 Python 中使用原生字典或唯讀 Mapping 進行常數級查詢：

```python
# apps/bot/config/modules.py
from typing import Final
from core.enums import FeatureModule

# 原生唯讀配置字典：O(1) 查找且享有 IDE 自動補全與型別檢查
DEFAULT_MODULE_LIMITS: Final[dict[FeatureModule, int]] = {
    FeatureModule.AUTO_VOICE: 6,
    FeatureModule.PRIVATE_ROOMS: 4,
    FeatureModule.PARTY: 10,
}
```

### 2. 責任區劃分：拒絕「綑綁包（Bundling）」
- ❌ **禁止做法**：在 `service/guild_settings_service.py` 或 `cogs/slash/party.py` 頂部寫死 `PANEL_TEXT_LIMITS = {...}`、大段繁體中文說明模板、預設數值字典，導致執行方法與設定硬編碼混在一起。
- ✅ **標準分工**：
  1. **靜態常數與邊界限制（Limits & Bounds）** ➔ 抽離至 `core/constants/limits.py` 或 `config/limits.py`。
  2. **面板文案與預設樣板（Templates & Defaults）** ➔ 抽離至 `config/templates.py` 或獨立語系配置檔。
  3. **資料結構與模型（Dataclasses / Models）** ➔ 抽離至 `models/settings.py`，使用 Python 原生 `@dataclass(frozen=True)` 或 Pydantic 定義純資料結構，只定義型別與欄位。
  4. **業務服務層（Service Layer）** ➔ 檔案內**只有純粹的方法呼叫（Methods）、業務流程驗證與 DB 呼叫**。

### 3. 解耦前後對照範例

**重構前（綑綁式，架構冗長）：**
```python
# ❌ service/guild_settings_service.py 裡面塞了 200 行設定
class GuildSettingsService:
    PANEL_TEXT_LIMITS = {"party_panel_title": 256, ...}  # 靜態限制
    DEFAULT_DESCRIPTION = "想聊天、玩遊戲或找同好？..."   # 大段文字
    
    def update(self, ...): ...  # 真正的方法只有幾行
```

**重構後（Clean Code，責任清楚）：**
```python
# ✅ service/guild_settings_service.py 專注於呼叫與驗證
from core.constants.limits import PANEL_TEXT_LIMITS
from models.settings import GuildSettings

class GuildSettingsService:
    """純業務邏輯：驗證資料邊界並委派持久化。"""
    def __init__(self, repository: GuildSettingsDB) -> None:
        self._repo = repository

    async def update(self, guild_id: int, changes: Mapping[str, Any]) -> GuildSettings:
        self._validate_limits(changes, limits=PANEL_TEXT_LIMITS)
        return await self._repo.update(guild_id, changes)
```

---

## 9. 架構決策與官方文檔依據規範（Documentation-Grounded Engineering）

為確保技術方案可溯源、嚴格遵守業界標準，並杜絕超出預期的過度設計與非標準自創語法，任何架構決策與說明必須具備明確的**官方文檔（Official Docs）與 PEP 標準依據**：

### 核心文檔依據參照表
1. **枚舉系統（Enums）**：
   - 官方依據：[Python 3.11 `enum.StrEnum` 官方文件](https://docs.python.org/3/library/enum.html#enum.StrEnum) & [PEP 435](https://peps.python.org/pep-0435/)。
   - 準則：純字串枚舉繼承 `StrEnum`，避免自創非標準字典常數替代。
2. **純資料容器（Data Contract）**：
   - 官方依據：[PEP 557 (Data Classes)](https://peps.python.org/pep-0557/) & [Python `dataclasses` 官方文件](https://docs.python.org/3/library/dataclasses.html)。
   - 準則：模型採用 `@dataclass(frozen=True, slots=True)`，確保不可變性與低記憶體開銷，純做資料載體，不塞入業務執行代碼。
3. **不可變常數（Constants & Typing）**：
   - 官方依據：[PEP 591 (Final Typing)](https://peps.python.org/pep-0591/) & [PEP 586 (Literal Types)](https://peps.python.org/pep-0586/)。
   - 準則：靜態常數使用 `typing.Final` 標記，防止執行時期被意外變更。
4. **依賴注入與服務容器（Dependency Inversion）**：
   - 架構依據：*Clean Architecture* (Robert C. Martin) 第 5 部分；FastAPI [Dependencies 官方引導規範](https://fastapi.tiangolo.com/tutorial/dependencies/)。
   - 準則：高層模組（Controllers / Cogs）不直接實例化底層模組（Repository），統一由組合根（Composition Root: `container.py`）提供。
5. **程式碼風格與註解（Documentation Standard）**：
   - 官方依據：[PEP 8 (Style Guide)](https://peps.python.org/pep-0008/) & [PEP 257 (Docstring Conventions)](https://peps.python.org/pep-0257/)。
   - 準則：公共方法一律附帶符合 PEP 257 規範的 Docstring，清楚界定 Args、Returns 與 Raises。


