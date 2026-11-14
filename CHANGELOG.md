# Changes

每個非 merge commit 都必須更新最上方的最新紀錄；舊紀錄依時間由新到舊保留。
每筆紀錄使用 `## 日期 - NN`，標題下一行寫 description；同一天從 `00` 遞增，隔天重新從 `00`
開始，最新紀錄放最上方。編號跟隨更新紀錄，重跑 CI 不新增編號。
再依 `feature`、`bug`、`chore`、`docs`、
`refactor`、`test` 分類。分類使用 `### 分類`，只保留有內容的分類。

## 2026-11-14 - 03

修復 GitHub Actions 語法檢查路徑與優化驗證邏輯認知複雜度

### bug

- 修正 .github/workflows/build-image.yml 在 Check API Python Syntax 步驟中因 cogs/repository/*.py 與 cogs/service/*.py 路徑不存在導致的 CI/CD 建置失敗，改為統一使用 python -m compileall -q . 遞迴編譯 apps/bot 內所有模組。

### refactor

- 重構 apps/bot/service/guild_settings_service.py 的 _validate 方法，依領域拆分為 6 個單一職責驗證函式，將認知複雜度（Cognitive Complexity）由 22 驟降至 0；同步抽離 _parse_single_level_role 將 _validate_level_roles 複雜度由 19 降至 6，滿足 SonarLint 15 以下之靜態品質標準。
- 同步更新 nx.json 中的 pythonSources 輸入監聽路徑，納入 api、core、models、repository 與 service 等新建分層目錄。

## 2026-11-14 - 02

重構後端為 Clean Layered Architecture，解耦資料存取、業務服務、API 表現層與配置邊界

### refactor

- 重構 apps/bot 為標準分層架構（Clean Architecture），將資料存取（DAL）升格為 apps/bot/repository/，業務領域邏輯抽離為 apps/bot/service/，FastAPI 路由模組化為 apps/bot/api/，落實單一職責原則。
- 實作 ServiceContainer（apps/bot/core/container.py），統一組裝與管理 Repository 與 Service 單例生命週期，消除各模組各自初始化資料庫與服務的重複邏輯。
- 解耦配置與執行代碼：建立 apps/bot/core/enums.py（以 PEP 435 StrEnum 定義 FeatureModule 與 VoiceRoomType）、apps/bot/core/constants/limits.py（PEP 591 Final 邊界常數）與 apps/bot/models/guild_settings.py（PEP 557 原生不可變資料模型），徹底將設定字典與面板文字從業務方法中分離。
- 將 apps/bot/bot.py 瘦身為乾淨的 Composition Root，接入集中化日誌（core.logging）與全域錯誤防禦管線（core.error_handler）。
- 徹底清理 apps/bot/cogs 目錄，全面移除 cogs/api/、cogs/repository/ 與 cogs/service/ 舊有殘留，使 cogs 僅專注於 Discord 表現層控制器（cogs/prefix/ 與 cogs/slash/）。

### docs

- 建立 specs/clean-architecture-refactor.md，依據 SDD（Spec-Driven Development）流程依序記錄純模型抽離、資料存取升格、業務服務瘦身、DI 容器裝配、API 模組化與全面驗證之任務順序與驗收狀態。

## 2026-11-14 - 01

新增 Web Mock 環境、模組化後台介面與湯技／揪團通知管理功能

### feature

- 各大功能模組（自動語音、私人包廂、湯技系統、社群揪團、等級經驗值）新增 Enable Switch 功能開關（`auto_voice_enabled`、`private_rooms_enabled`、`skills_enabled`、`party_enabled`、`leveling_enabled`），Dashboard 卡片牆可直接以 Switch 一鍵開關，左側選單目錄自動動態顯示開啟之模組（未開啟則自動隱藏），各模組內頁亦提供開關與停用提示，Bot 端同步攔截已停用功能的觸發、經驗值發放與開房互動。
- Web 設定後台改為「左側模組導覽列（方案 A）＋ 模組總覽 Dashboard 卡片牆（方案 B）」雙模式架構，將設定拆分為「語音與私人包廂」、「湯技角色系統」、「社群與揪團面板」、「活躍值與等級」與「Slash 指令說明」，並支援各模組即時設定摘要與未儲存／驗證錯誤狀態提示。
- 等級身分組（`level_roles`）改用 VS Code 核心的 Monaco Editor（`@monaco-editor/react`），內建 JSON Schema 型別提示、格式化、深淺色主題同步，並提供「視覺化表格」與色票選色器雙向同步轉換十進位色碼。
- 湯技角色系統新增管理員專用「建立新湯技與已建立清單（`SkillsManager`）」介面（串接 `GET/POST/DELETE /api/guilds/{guild_id}/skills` 與 `POST .../regenerate-code`），支援直接建立湯技、檢視已建立湯技與成員數、複製與重設 `/skill join` 專屬邀請碼、一鍵切換面板直接加入，並移除無作用的「語音房預設類別」欄位。
- 社群與揪團面板（房間大廳）後台新增 `party_notification_channel` 下拉選單（透過 `GET /api/guilds/{guild_id}/channels` 載入伺服器文字頻道，支援儲存 Channel ID 或既有頻道名稱）：建房表單送出時若有選擇「通知身分」即直接發送通知至該頻道，若未選擇任何通知身分則不發送通知訊息。
- 新增 Web Mock 模式 `pnpm run web:mock`（Nx target `web:dev-mock`）：以記憶體假資料略過登入，直接進入伺服器設定編輯畫面；正式建置不含 Mock 程式碼。

## 2026-11-14 - 00

變更紀錄改用 CHANGELOG.md

### chore

- 將 `changes.md` 改名為 `CHANGELOG.md`，並合併舊版 Keep a Changelog 紀錄於檔案底部。
- 更新驗證腳本、測試、CI 流程、update-changes skill、AGENTS.md 與 README 改為使用 `CHANGELOG.md`。
- Discord 通知不支援標題語法，改將最新紀錄的 `##` 標題轉為粗體、`###` 分類轉為【分類】後再送出。
- 新增 `pnpm run docker:dev` / `docker:prod`（含 `:down`、`:logs`）操作 `docker/` 內的 Compose 檔，並以專案根目錄為基準解析路徑；Web 的 ignore 規則移至 `apps/web/Dockerfile.dockerignore`；同時在 Nx `bot` 專案加入 `docker-*` targets，讓 Nx Console 可直接點選執行。
- 更新紀錄標題改為 `## YYYY-MM-DD - NN`，說明文字另起一行；驗證腳本、測試、skill、AGENTS.md 與 README 同步調整，既有紀錄全部轉為新格式。

### docs

- README 更新為繁體中文（`README.md`）與英文（`README.en.md`）兩個版本，補上 `docker/` 目錄、docker 指令與專案結構說明。

## 2026-11-12 - 02

部署 Webhook 逾時不再判定失敗

### bug

- n8n 在 NAS 重啟完成前不回應時，部署步驟會因 curl 讀取逾時（exit 28）而失敗；已連線但未回應現在視為已送達，連線失敗仍會報錯。

## 2026-11-12 - 01

建房表單送出後直接通知

### feature

- 建立房間表單送出成功後，Bot 立即在揪團通知頻道公告並標記所選湯技，不再需要另按「分享房間」。
- 未選通知身分時仍會公告，只是不標記身分組。

### chore

- 移除分享按鈕與指定分享頻道選單；通知頻道缺失、Bot 權限不足或發送失敗時不影響建房，並在私人回覆提示原因。

### docs

- 更新房間大廳預設說明、表單提示、README 與環境變數範例。

### test

- 驗證建房後即時通知、身分標記限制，以及通知失敗時仍保留房間。

## 2026-11-12 - 00

簡化部署 Webhook 觸發流程不等待回應

### chore

- 移除部署工作流程對 Webhook 回傳內容的檢查與逾時等待，改為成功送出請求即完成。
- 部署執行失敗由 n8n 直接透過 Discord 通知，避免 Actions 因 NAS 重啟耗時逾時。

### docs

- 更新 README 部署說明，註記 Webhook 為非同步觸發與通知機制。

## 2026-11-11 - 03

網站可編輯 Discord 社群面板文案

### feature

- 後台新增房間大廳與湯技面板的標題、說明、操作說明、按鈕文字及邀請碼頁尾設定。
- 儲存後立即套用至既有社群面板，保留原本預設文案與即時湯技成員資訊。

### bug

- 面板改以固定按鈕 ID 辨識，避免自訂標題後重複發送或覆寫另一張面板。

### test

- 驗證文案持久化、Discord 長度限制、重新命名後重用訊息，以及 API 更新失敗後重試。

## 2026-11-11 - 02

修正更新紀錄格式與測試不同步

### bug

- 統一更新紀錄、測試資料與錯誤提示為「日期 - NN - 摘要」，移除測試中過時的 Build 前綴。
- 修正 CI 單元測試誤將合法每日編號紀錄判定為格式錯誤的問題。

### test

- 分類及編號的反向測試明確檢查拒絕原因，避免因標題格式錯誤而假通過。

### docs

- 同步專案規範、README 與 update-changes Skill 的標題格式。

## 2026-11-11 - 01

分開呈現 API 與 Web 建置部署節點

### chore

- 將 Actions matrix 群組改成 API Build → API Deploy 與 Web Build → Web Deploy 兩條分支。
- 將 Python CI 收進 API Build，沿用既有 Bot/API image，Web 不等待 API 建置或部署。
- 分別以共用 workflow 維護建置與部署，四個節點在主 workflow 明確連線。
- 通知匯整兩條分支的結果，未受影響的 skipped 分支不會被誤判為失敗。
- 通知會反映個別建置與部署結果，只列出成功推送的映像，不會把未建置的映像誤列為成功。
- 更新紀錄加入每日從 00 開始的流水號，CI 檢查日期排序與編號連續性。

### docs

- 說明 Actions 分支圖與共用 workflow，維持原有的 Secret 設定方式。

## 2026-11-11 - 00

CI/CD 部署與更新紀錄

### feature

- 新增映像推送成功後的部署 webhook，使用 Secret 保存網址，並驗證回應的狀態、專案及映像版本。

### chore

- 依 Bot 與 Web 的變更路徑選擇建置目標，純文件變更不建置映像。
- 將可共用的 pipeline 參數集中在全域 env，保留 matrix 與步驟輸出的必要作用域。
- CI 強制檢查每個新進的非 merge commit 是否更新 changes.md 最新紀錄及分類格式。
- Discord 通知直接讀取 changes.md 最上方的最新紀錄，保留分類標記。

### docs

- 新增 update-changes 專案 Skill，協助提交前撰寫紀錄與定位漏寫的 commit。

### test

- 新增最新紀錄、分類格式及逐 commit 檢查的測試。

---

## 2026-04-12 - 00

v1.1.0 活躍值等級系統與私人包廂重構

### feature

- 🎮 **活躍值等級系統** — 透過聊天、語音掛機、每日簽到賺取經驗值，自動升級並獲得稱號角色
  - `/daily` 每日簽到（連續簽到加成）
  - `/rank` 查看個人等級與進度
  - `/leaderboard` 活躍值排行榜 TOP 10
  - `/level-preview` 預覽升級公告與等級卡
  - `/level-init` 為現有成員初始化等級資料
- 🔧 **動態等級角色設定** — 支援透過 `LEVEL_ROLES` 環境變數自訂等級里程碑

### refactor

- 🔒 **私人包廂系統重構** — 新增密碼保護機制與自動語音頻道增強功能
- 🧹 移除未使用的 `hello` 和 `say` Slash 指令

## 2026-04-08 - 01

v1.0.2 自動語音頻道、私人包廂與湯技角色

### feature

- 🔊 **自動語音頻道系統** — 加入觸發頻道自動建立專屬語音房，離開後自動刪除
- 🔒 **私人包廂系統** — 上鎖語音房搭配密碼機制，支援房主管理指令
- 🏷️ **湯技角色系統** — 一鍵建立技能角色，自動生成分類、頻道與互動面板
- 📢 **公告 Embed** — `/announce` 發送格式化嵌入式公告
- 📝 密碼頻道規則 Embed 與使用說明

### bug

- 🐛 修正湯技角色名稱比對邏輯，支援前綴變體
- 🐛 修正密碼頻道主題顯示

### docs

- 📖 重寫 README 完整功能文件

### chore

- 🐳 改用 Docker Hub 映像部署

## 2026-04-08 - 00

v1.0.0 Discord 機器人核心架構

### feature

- 🤖 Discord 機器人核心架構，採用 Cogs 模組化設計
- ⚙️ 環境變數設定系統（`config.py`）
- 🎯 基本前綴指令：`!ping`、`!info`
- ⚡ Slash 指令支援：`/userinfo`
- 🐳 Docker 與 Docker Compose 部署支援
- 📝 `.env.example` 環境變數範例
