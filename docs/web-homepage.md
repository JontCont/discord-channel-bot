# Web 首頁（Home / Landing Page）與前端導覽文件

本文件說明 `apps/web` 的產品功能介紹首頁（`/`）架構、視覺與 CSS 動畫設計、多語系資源以及與管理控制台（Console）的路由串接方式。

---

## 1. 路由架構（Routing）

前端採用 `@tanstack/react-router` 管理路由（定義於 [`apps/web/src/router.tsx`](../apps/web/src/router.tsx)）：

| 路由路徑 | 元件 | 權限需求 | 說明 |
|---|---|---|---|
| `/` | `HomePage` ([`apps/web/src/ui/HomePage.tsx`](../apps/web/src/ui/HomePage.tsx)) | 公開 | 產品功能介紹首頁，展示 6 大核心模組、互動式 Discord 面板預覽、3 步驟導入流程與 Slash 指令速覽 |
| `/login` | `LoginScreen` ([`apps/web/src/ui/LoginScreen.tsx`](../apps/web/src/ui/LoginScreen.tsx)) | 公開 | Discord OAuth2 登入入口 |
| `/privacy` | `PrivacyPolicyPage` ([`apps/web/src/ui/LegalPages.tsx`](../apps/web/src/ui/LegalPages.tsx)) | 公開 | 隱私權政策 |
| `/terms` | `TermsOfServicePage` ([`apps/web/src/ui/LegalPages.tsx`](../apps/web/src/ui/LegalPages.tsx)) | 公開 | 服務條款 |
| `/guilds` | `GuildPicker` ([`apps/web/src/ui/GuildPicker.tsx`](../apps/web/src/ui/GuildPicker.tsx)) | 需登入 (`AuthenticatedLayout`) | 選擇要管理的 Discord 伺服器（未登入時自動導向 `/login`） |
| `/guilds/$guildId/settings` | `SettingsPage` ([`apps/web/src/ui/SettingsPage.tsx`](../apps/web/src/ui/SettingsPage.tsx)) | 需登入 (`AuthenticatedLayout`) | 單一伺服器的模組化設定後台（Mock 模式下可直接點擊首頁按鈕進入） |

---

## 2. 首頁區塊設計（HomePage Sections）

[`HomePage.tsx`](../apps/web/src/ui/HomePage.tsx) 採用現代化 SaaS 視覺風格，支援亮色／深色主題（`data-theme="dark"`）與響應式排版（RWD）：

1. **置頂毛玻璃導覽列（Glassmorphism Sticky Navbar）**
   - 品牌標誌（點擊返回首頁 `/`）。
   - 頁內錨點跳轉（`#features` 核心功能、`#workflow` 運作流程、`#commands` 指令總覽）。
   - `DisplayControls`（語系切換器 `zh-Hant` / `en` / `ja` 與深淺色主題切換）及「進入控制台」主行動按鈕（Mock 模式下自動切換為「體驗 Mock 預覽後台」直達 `/guilds/$guildId/settings`）。
2. **Hero 主視覺與動態 Discord 預覽視窗（Hero & Interactive Discord Mockup）**
   - 左側：動態狀態膠囊、流動漸層主標題、功能亮點摘要與雙 CTA 按鈕（開啟管理控制台 `/guilds`、邀請機器人 `/api/bot/invite`）。
   - 右側：擬真 Discord 伺服器視窗，展示 `#🎯｜社群入口`、`#📣｜揪團通知`、動態語音聲波動畫、置頂互動面板卡片，以及兩張上下浮動的即時同步與等級晉升提示卡。
3. **核心數據指標列（Stats Bar）**
   - 展示 `6 大` 模組化核心系統、`25+` 原生 Slash 指令、`10 階` 活躍值等級里程碑與 `零延遲` Web 後台面板同步。
4. **六大功能 Bento Grid（Feature Bento Cards）**
   - 以 6 張不同主題色（Indigo、Teal、Violet、Amber、Rose、Sky）的卡片完整介紹：
     - **自動語音頻道 & 私人包廂**（Dynamic Voice）
     - **社群入口 & 遊戲揪團大廳**（Matchmaking）
     - **湯技角色與專屬頻道系統**（Interest Groups）
     - **活躍值經驗 & 等級稱號系統**（Engagement）
     - **置頂自我介紹互動卡**（Onboarding）
     - **即時同步 Web 管理控制台**（Web Dashboard）
5. **三步驟快速導入流程（3-Step Onboarding Workflow）**
   - 依序說明「邀請機器人並登入後台」→「一鍵初始化頻道與面板」→「Web 視覺化即時客製」。
6. **互動式 Slash 指令瀏覽器（Interactive Slash Commands Showcase）**
   - 支援切換「語音與私人包廂」、「遊戲揪團」、「湯技系統」、「等級與活躍值」、「一般與公告」五個頁籤，即時檢視各指令語法與權限用途。
7. **底部行動呼籲與頁尾（CTA Banner & Footer）**
   - 提供快速進入控制台、登入、隱私權政策與服務條款連結。

---

## 3. CSS Animation 與無障礙減敏設計

所有動畫定義於 [`apps/web/src/styles.css`](../apps/web/src/styles.css) 的 `Home / Landing Page & CSS Animations` 區塊，僅對 `transform`、`opacity` 與 `background-position` 進行硬體加速動畫：

| Keyframes 名稱 | 用途與視覺效果 |
|---|---|
| `@keyframes homeFloatOrb` | 背景三顆柔和光暈球（Primary / Teal / Violet）的慢速漂浮與呼吸縮放（14s 循環） |
| `@keyframes homeFloatCard` | Hero 右側 Discord 預覽視窗與兩張浮動提示卡（Instant Sync / +25 XP）的錯位懸浮效果 |
| `@keyframes homeRevealUp` | 首頁區塊與 6 張功能卡片依序（`animationDelay: index * 90ms`）由下往上淡入進場 |
| `@keyframes homeGradientShift` | 主標題強調字（`.home-gradient-text`）的多色漸層流動效果 |
| `@keyframes homePulseDot` | 機器人線上狀態綠點（`.home-status-dot`、`.pulse-ring`）的向外擴散波紋脈衝 |
| `@keyframes homeVoiceWave` | Discord 預覽視窗左下角語音頻道連線中的 5 軌動態聲波跳動（`.preview-voice-wave`） |

### 無障礙支援（`prefers-reduced-motion`）
在 [`apps/web/src/styles.css`](../apps/web/src/styles.css) 底部保留全域 `@media (prefers-reduced-motion: reduce)` 規則：當使用者作業系統開啟「減少動態效果」時，所有 CSS Keyframe 動畫會自動收斂為靜態呈現，兼顧視覺體驗與無障礙規範。

---

## 4. 多語系支援（i18n）

首頁所有文案皆收納於 [`apps/web/src/i18n.ts`](../apps/web/src/i18n.ts) 的 `translation.home` 命名空間下，完整支援三種語系：
- **繁體中文（`zh-Hant`）**
- **英文（`en`）**
- **日文（`ja`）**

指令速覽區塊則直接複用 `translation.settings.slash.groups` 與 `translation.settings.slash.commands`，確保首頁與設定後台內的 Slash 指令說明保持單一事實來源（Single Source of Truth）。
