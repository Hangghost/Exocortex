# Project Branch Flow

## Purpose

規範本 repo 的三類工作分支（content/、project/、feature/）的拓樸結構、生命週期、資料範疇與合併策略。定義 project 分支 long-lived 且不自動 rebase 的核心原則，防止多機同步時 SHA 改寫破壞 DAG 完整性。
## Requirements
### Requirement: 分支拓樸三類劃分

本 repo 的工作分支 SHALL 限定為三類，各自對應明確的資料範疇與生命週期：

- `content/YYYY-MM-DD`：每日內容分支，short-lived，涵蓋 `contexts/`、`memory/`、`inbox/` 等 event-shaped 變更
- `project/<name>`：專案分支，long-lived，涵蓋 `projects/<name>/` 下的 state-shaped 變更
- `feature/<change-name>`：架構變更分支，short-lived，涵蓋 `rules/`、`.claude/`、`openspec/` 等架構層變更

#### Scenario: 分支命名約定被記錄於 WORKSPACE.md
- **WHEN** 使用者查閱 `rules/WORKSPACE.md`
- **THEN** 文件 SHALL 包含「分支命名約定」一節，說明三類分支的命名 pattern、資料範疇、生命週期

#### Scenario: 分支類型由 slash 前綴決定
- **WHEN** 任何 skill 偵測當前分支類型
- **THEN** 系統 SHALL 以 `content/`、`project/`、`feature/` 前綴判定，其他前綴視為未知類型並詢問使用者

---

### Requirement: `project/<name>` 分支 long-lived 並不與 main 自動同步

`project/<name>` 分支 SHALL 從專案 create 建立直到 complete 才刪除；期間里程碑 merge 進 main 後，分支 SHALL 續命而非刪除。系統 SHALL NOT 自動對 `project/*` 執行 rebase 或 merge main。

#### Scenario: 里程碑合併後分支保留
- **WHEN** `project/<name>` 透過 `/ctx:content merge` 以 milestone 合併進 main
- **THEN** 系統 SHALL 執行 `git checkout main && git merge --no-ff project/<name> -m "<milestone>"`，並**保留** `project/<name>` 分支

#### Scenario: 專案完結時分支刪除
- **WHEN** 使用者執行 `/ctx:project complete <name>`
- **THEN** 系統 SHALL 以 `--no-ff` 做最終 milestone merge（message 格式 `project complete: <name>`）後執行 `git branch -d project/<name>`

#### Scenario: main 更新不主動傳播到 project 分支
- **WHEN** main 有新 commit 但使用者未手動觸發
- **THEN** 系統 SHALL NOT 自動在 `project/*` 分支上執行任何 rebase 或 merge

#### Scenario: 使用者手動拉取 main 變更
- **WHEN** 使用者在 `project/<name>` 分支上手動執行 `git merge main`
- **THEN** git 行為 SHALL 為原生 merge，系統不介入也不修改 message

---

### Requirement: Merge 策略二分：content squash，project no-ff

合併到 main 的操作 SHALL 依來源分支類型採用不同策略：

- `content/YYYY-MM-DD` → main：使用 `--squash`，單一壓縮 commit
- `project/<name>` → main：使用 `--no-ff`，保留分支內部 commit 軌跡並加上 milestone message

#### Scenario: content 分支 squash merge
- **WHEN** 系統合併 `content/YYYY-MM-DD` 進 main
- **THEN** 系統 SHALL 執行 `git checkout main && git merge --squash content/YYYY-MM-DD && git commit -m "content: <YYYY-MM-DD> daily snapshot"`

#### Scenario: project 分支 milestone merge
- **WHEN** 系統合併 `project/<name>` 進 main 作為里程碑
- **THEN** 系統 SHALL 執行 `git checkout main && git merge --no-ff project/<name> -m "project(<name>): <milestone>"`，保留該分支的完整 commit DAG

#### Scenario: 使用者未提供 milestone message
- **WHEN** `/ctx:content merge` 偵測到當前在 `project/<name>` 且使用者未提供 milestone
- **THEN** 系統 SHALL 詢問「請輸入 milestone name（留空取消）」，留空時取消合併不執行任何操作

---

### Requirement: `projects/INDEX.md` 作為活躍專案分支 SSOT

活躍的 `project/*` 分支集合 SHALL 對應 `projects/INDEX.md` 中 `status: active` 或 `status: paused` 的專案。系統 SHALL 保持兩者一致。

`projects/INDEX.md` 本身在 commit 路由上 SHALL 採 **rider** 行為：commit 時跟著同次變更內任一 `projects/<X>/` 檔案進入 `project/<X>` 分支；若無 sibling project 變更，則 fallback 進 `content/YYYY-MM-DD`。詳細路由規則見 `ctx-content-command` spec 的「`projects/INDEX.md` 採 rider 分類規則」Requirement。Rider 行為 SHALL NOT 改變本 SSOT 性質——INDEX.md 仍是活躍分支集合的單一真相來源，rider 只規範 commit 落點。

#### Scenario: 建立專案時更新 INDEX
- **WHEN** `/ctx:project new <name>` 完成
- **THEN** `projects/INDEX.md` SHALL 新增該專案條目（status: active），且 `project/<name>` 分支 SHALL 存在於本地

#### Scenario: 專案暫停分支保留
- **WHEN** `/ctx:project pause <name>` 執行
- **THEN** INDEX 中該專案 status SHALL 更新為 `paused`，`project/<name>` 分支 SHALL 保留

#### Scenario: 專案完結分支刪除
- **WHEN** `/ctx:project complete <name>` 執行
- **THEN** INDEX 中該專案 status SHALL 更新為 `completed`，`project/<name>` 分支 SHALL 被刪除

#### Scenario: 多機同步查詢活躍分支
- **WHEN** 使用者在另一台機器需要列出活躍專案分支
- **THEN** 使用者 SHALL 優先查 `projects/INDEX.md`（SSOT），次要手段為 `git branch -a | grep project/`

#### Scenario: INDEX.md commit 落點不破壞 SSOT 性質
- **WHEN** `projects/INDEX.md` 因 rider 規則 commit 到 `project/<X>` 分支
- **THEN** 該 commit 進 main 後（透過 milestone merge 或 daily snapshot），`projects/INDEX.md` 在 main 上的內容 SHALL 仍為活躍分支集合的 SSOT，不因 commit 來源分支不同而有歧義

### Requirement: 多機同步涵蓋 long-lived project 分支

`rules/skills/git-multi-machine/SKILL.md` SHALL 包含一節說明 long-lived `project/*` 分支的多機同步流程。

#### Scenario: skill 包含 project 分支同步節
- **WHEN** 查閱 `rules/skills/git-multi-machine/SKILL.md`
- **THEN** 文件 SHALL 包含一節（如「Long-lived project branches 同步」）涵蓋：
  1. 如何列出活躍專案分支（查 INDEX 或 `git branch -a`）
  2. 首次 push 需用 `git push -u origin project/<name>`
  3. 切換機器接手專案的標準流程（fetch → checkout → pull）

#### Scenario: 首次 push 策略
- **WHEN** 使用者在 `project/<name>` 上首次執行 push
- **THEN** SKILL.md SHALL 指示使用 `git push -u origin project/<name>`，使後續 `git push` 無需參數

---

### Requirement: Observer 邊界保留，不掃 projects/

本變更 SHALL NOT 修改 observer 掃描行為。`projects/` 仍不屬於 observer 的直接觀察對象；專案事件流透過 `contexts/work_logs/` 橋樑進入觀察。

#### Scenario: Observer 不因本變更修改掃描範圍
- **WHEN** observer 執行每日掃描
- **THEN** 系統 SHALL NOT 將 `projects/` 納入 observer 輸入來源（與 `ARCHITECTURE.md` 行 120 定義一致）

#### Scenario: 專案事件透過 work_log 進入觀察
- **WHEN** 使用者在 `project/<name>` 分支上有重要產出
- **THEN** 使用者 SHALL 透過 `/ctx:project update` 產生 `contexts/work_logs/` 條目；此條目隨 `content/YYYY-MM-DD` merge 進 main 後，observer 可觀察到

### Requirement: 開分支 SHALL 顯式指定 base

任何在本 repo 創建分支的程式（slash command、skill、helper script）SHALL 使用一行式語法 `git checkout -b <name> <base>`，其中 `<base>` 顯式寫成 `main`（或其他明確 ref，如 origin/main、tag）。SHALL NOT 使用 raw `git checkout -b <name>`（隱式繼承當前 HEAD）。

兩步式 `git checkout main; git checkout -b <name>` 雖 effective safe 但**非正規形式**，新增程式 SHALL 採用一行式。既有兩步式可在文件 sweep 時 normalize 為一行式（idiom 一致性）。

依據：`rules/axioms/a09_explicit_branch_base.md`。

#### Scenario: ctx 命令建立 feature 分支

- **WHEN** `/ctx:arch` 在 propose 完成、Step 1.5 guard 通過後執行 git checkout -b
- **THEN** 命令文件 SHALL 寫成 `git checkout -b feature/<change-name> main`，不寫成 raw `git checkout -b feature/<change-name>`

#### Scenario: ctx 命令建立 content 分支

- **WHEN** `/ctx:content` 或 `/ctx:eod` 需要建立 `content/YYYY-MM-DD`
- **THEN** SHALL 寫成 `git checkout -b content/YYYY-MM-DD main`

#### Scenario: ctx 命令建立 project 分支

- **WHEN** `/ctx:project new` 或復原異常分支
- **THEN** SHALL 寫成 `git checkout -b project/<name> main`

#### Scenario: ctx 命令建立 experiment 分支

- **WHEN** `/ctx:experiment start`
- **THEN** SHALL 寫成 `git checkout -b experiment/<YYYY-MM-DD>-<name> main`

#### Scenario: 兩步式遺留可被 normalize 但不違規

- **WHEN** 既有命令仍使用 `git checkout main; git checkout -b X` 兩步式
- **THEN** 違反正規形式但**不是錯誤**（effective safe），sweep 時 SHALL 重寫為一行式以維持 idiom 一致

#### Scenario: hint message 中的 `git checkout -b` 不適用

- **WHEN** 命令文件中的字串是給使用者的引導訊息（例如 content.md 中「請先執行 `git checkout -b project/<X>`」），非實際執行的命令
- **THEN** 該字串不適用本 requirement，可保留現狀

