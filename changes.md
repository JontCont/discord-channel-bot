# Changes

每個非 merge commit 都必須更新最上方的最新紀錄；舊紀錄依時間由新到舊保留。
每筆紀錄使用 `## 日期 - 摘要`，再依 `feature`、`bug`、`chore`、`docs`、
`refactor`、`test` 分類。分類使用 `### 分類`，只保留有內容的分類。

## 2026-11-11 - CI/CD 部署與更新紀錄

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
