# project-worktree-flow Specification

## Purpose

定義 `project/<name>` 分支的 git worktree 機制——所有機器永遠啟用、worktree 物理位置統一為 repo-relative `<repo>/.claude/worktrees/<name>/`，搭配短壽容器生命週期（resume 時 spawn、EOD 時收尾後 hard delete），確保多機同步下的並行專案工作不會互相污染共享路徑（contexts/、infra/state/、memory/、rules/）。落腳於 `.claude/worktrees/` 是為了符合 Claude Code background session 的 isolation 規則（bg session 在此路徑可正常編輯）。本能力與 `ctx:project` / `ctx:eod` / `ctx:onboard` 命令的對應 worktree-aware 行為共同構成完整工作流，並由 `git-multi-machine` skill 文件化使用者操作面。
## Requirements
### Requirement: Worktree mode 啟用偵測

系統 SHALL 永遠啟用 worktree 模式，無偵測動作。所有機器（Mac mini、MacBook Pro、Windows 筆電）使用同一套行為，不再依賴外部 marker 目錄判定。

設計依據：worktree 物理位置改為 repo-relative（`<repo>/.claude/worktrees/<name>/`），無 home-anchored 路徑導致的 user-specific 顧慮，因此不再需要 marker-based opt-in 模型。

#### Scenario: 任何機器執行 /ctx:project resume

- **WHEN** 任一機器上執行 `/ctx:project resume <name>`
- **THEN** 系統 SHALL 直接進入 worktree spawn / 重用流程，不檢查任何 marker 目錄

#### Scenario: 不存在 marker 目錄無影響

- **WHEN** 機器上 `~/Documents/Projects/Exocortex-worktrees/` 不存在
- **THEN** 行為與本變更後的標準流程一致，不 fallback、不警告

---

### Requirement: Worktree 物理位置與命名約定

`project/<name>` 分支的 worktree SHALL 位於 `<repo>/.claude/worktrees/<name>/`（其中 `<repo>` 為 main repo 根目錄，例如 `~/Documents/Projects/Exocortex-personal/`）。Worktree 目錄名 SHALL 與 project name 一致（1:1 mapping，無歧義）。採 flat layout，不嵌套 `project/` 或其他子目錄。

設計依據：此路徑落在 Claude Code background session 認可的 isolation namespace（`.claude/worktrees/`）下，bg session 在此路徑可正常使用 Edit/Write 工具。

`.gitignore` SHALL 含 `.claude/worktrees/**`，避免 worktree 內容污染 main repo 的 `git status`。

#### Scenario: Worktree 路徑符合約定

- **WHEN** `/ctx:project resume wwpf-qd` spawn worktree
- **THEN** 系統 SHALL 執行 `git worktree add .claude/worktrees/wwpf-qd project/wwpf-qd`，cwd 為 main repo 根目錄

#### Scenario: Worktree 在 .claude/worktrees/ 下且非 nested

- **WHEN** 任何 project worktree 被 spawn
- **THEN** 路徑 SHALL 為 `<main-repo-root>/.claude/worktrees/<name>/`，不得有其他子目錄前綴

#### Scenario: Background session 在 worktree 內可編輯

- **WHEN** Claude Code background session cwd 進入 `<repo>/.claude/worktrees/<name>/`
- **THEN** Edit / Write 工具 SHALL 正常運作，不被 harness 規則攔截

---

### Requirement: Worktree 機制應用範圍限定 project/*

Worktree 機制 SHALL 僅應用於 `project/<name>` 分支。`feature/<name>` 與 `content/<date>` 分支 SHALL 永遠在 main worktree 操作。

#### Scenario: feature 分支不 spawn worktree

- **WHEN** 使用者執行 `/ctx:arch` 建立 `feature/<name>` 分支
- **THEN** 系統 SHALL 在 main worktree 內 `git checkout -b feature/<name> main`，不 spawn 獨立 worktree

#### Scenario: content 分支不 spawn worktree

- **WHEN** `/ctx:eod` 或 `/ctx:content` 建立 `content/<date>`
- **THEN** 系統 SHALL 在 main worktree 內建立分支，不 spawn 獨立 worktree

---

### Requirement: 短壽容器生命週期

Project worktree 採短壽容器模型：`/ctx:project resume <name>` 偵測無對應 worktree 時自動 spawn 並透過 Bash tool 將當前 Claude Code session 的 cwd 切入該 worktree；`/ctx:eod` 對所有活著的 project worktree 跑收尾流程後 hard delete。`project/<name>` 分支本身 SHALL 保留在 origin 與本地（不被本機制刪除）。

resume 流程的最後兩步 SHALL 拆成獨立 step：先執行 `cd` via Bash tool 切入 worktree（失敗 SHALL 中斷），再顯示專案摘要 + worktree boundary 提示。Boundary 提示 SHALL 明示 Claude Code session cwd 與外部 terminal shell prompt 解耦（cd 只影響當前 session 內後續 Bash tool call 的 cwd，不影響使用者外部 terminal）。

#### Scenario: resume 自動 spawn 並切入

- **WHEN** 使用者執行 `/ctx:project resume <name>`，且 `git worktree list` 中無 `.claude/worktrees/<name>` 對應條目
- **THEN** 系統 SHALL 執行 `git worktree add .claude/worktrees/<name> project/<name>`
- **AND** 系統 SHALL 透過 Bash tool 執行 `cd <repo>/.claude/worktrees/<name>`，使當前 Claude Code session 內後續 Bash tool call 的 cwd 落在 worktree
- **AND** 系統 SHALL 顯示專案摘要與 boundary 提示（含外部 terminal 解耦警示）

#### Scenario: resume 偵測既存 worktree 不重 spawn 但仍切入

- **WHEN** 使用者執行 `/ctx:project resume <name>` 且對應 worktree 已存在於 `.claude/worktrees/<name>/`
- **THEN** 系統 SHALL 略過 `git worktree add` 步驟
- **AND** 系統 SHALL 透過 Bash tool 執行 `cd <repo>/.claude/worktrees/<name>`，使當前 session 後續操作落在 worktree
- **AND** 系統 SHALL 顯示專案摘要與 boundary 提示

#### Scenario: cd 失敗中斷

- **WHEN** Bash tool 執行 `cd <repo>/.claude/worktrees/<name>` 回傳非零 exit code（例如路徑不存在）
- **THEN** 系統 SHALL 中斷 resume 流程，不繼續顯示專案摘要
- **AND** 系統 SHALL 提示使用者「cd 失敗，通常代表 Step 4 worktree spawn 出錯，請檢查 `git worktree list` 結果」

#### Scenario: 外部 terminal cwd 不被影響

- **WHEN** 使用者在外部 terminal（非 Claude Code session）執行 `/ctx:project resume <name>` 後檢查 shell prompt
- **THEN** 外部 terminal 的 cwd SHALL 維持原狀（不會被自動切到 worktree）
- **AND** resume 的 boundary 提示 SHALL 顯式告知此解耦，並提供使用者手動 `cd` 命令文字

#### Scenario: EOD hard delete worktree

- **WHEN** `/ctx:eod` 對某 project worktree 完成收尾流程（變更已 commit + push 或為類別 2 已搬移、無類別 3/4 警報）
- **THEN** 系統 SHALL 執行 `git worktree remove .claude/worktrees/<name>`，分支保留

#### Scenario: 分支被保留可重 spawn

- **WHEN** EOD 後使用者隔天執行 `/ctx:project resume <name>`
- **THEN** 系統 SHALL 重新 spawn worktree 至 `.claude/worktrees/<name>/`，內容為 origin 上 `project/<name>` 最新狀態

### Requirement: EOD 對 worktree 的四類變更處理規則

`/ctx:eod` 對每個活著的 project worktree 跑收尾流程時 SHALL 依檔案路徑分類處理：

- **類別 1**：`projects/<X>/...` 下的變更 → commit + push to `project/<X>`
- **類別 2**：`contexts/`、`inbox/ideas.md`、`inbox/reading_list.md`、`contexts/blog/`、`contexts/work_logs/`、`contexts/thought_review/`、`contexts/survey_sessions/` 等跨 project 共享路徑 → 提示使用者「這些檔案應在 main worktree 透過 `content/<date>` 分支提交」，並列出檔案清單
- **類別 3**：`infra/state/`、`memory/`、`inbox/captured/`、`projects/INDEX.md` → 警報「此檔案為 system-singleton，不應在 project worktree 內修改」並列出
- **類別 4**：`rules/`、`openspec/`、`.claude/` → 警報「此為架構層變更，應走 `feature/*` 分支」並列出

類別 1 SHALL 自動處理（commit + push）。類別 2/3/4 SHALL 不自動處理；EOD 仍會繼續處理其他 worktree 與 main worktree 流程，但結尾報告 SHALL 列出未處理項目。

#### Scenario: 類別 1 自動 commit + push

- **WHEN** project worktree 內 `projects/wwpf-qd/PROJECT.md` 有變更
- **THEN** 系統 SHALL 在該 worktree 內執行 `git add projects/wwpf-qd/ && git commit -m "<msg>" && git push`，commit message 由使用者輸入或採預設格式

#### Scenario: 類別 2 提示搬移

- **WHEN** project worktree 內 `contexts/blog/<draft>.md` 或 `inbox/ideas.md` 有變更
- **THEN** 系統 SHALL 顯示提示「以下檔案屬跨 project 共享範疇，建議搬到 main worktree 走 content/<date>」並列出檔案；SHALL NOT 自動搬移；使用者可選擇手動搬移後重跑 `/ctx:eod`，或留待下次處理

#### Scenario: 類別 3 警報

- **WHEN** project worktree 內偵測到 `infra/state/system_state.json`、`memory/OBSERVATIONS.md`、`inbox/captured/<...>`、或 `projects/INDEX.md` 有變更
- **THEN** 系統 SHALL 顯示警報「⚠️ 偵測 system-singleton 檔案在 project worktree 內被修改，幾乎一定是誤動」並列出；SHALL 不自動 revert，由使用者決定是否 `git restore` 或保留

#### Scenario: 類別 4 警報

- **WHEN** project worktree 內偵測到 `rules/`、`openspec/`、或 `.claude/` 路徑有變更
- **THEN** 系統 SHALL 顯示警報「⚠️ 此為架構層變更，應走 feature/* 分支」並列出；SHALL 不自動處理

#### Scenario: 多類別變更同時存在

- **WHEN** 一個 project worktree 內同時包含類別 1（已自動處理）、類別 2（提示）、類別 3（警報）變更
- **THEN** 系統 SHALL 全部呈現於該 worktree 的收尾報告中，類別 1 已處理、類別 2/3 列入未處理項目，繼續處理下一個 worktree

---

### Requirement: 多機同步 skill 文件化 worktree 約定

`personal-skills/git-multi-machine/SKILL.md` SHALL 包含一節說明：

1. Worktree 模式所有機器一致啟用，無 opt-in / opt-out
2. Worktree 物理位置：`<repo>/.claude/worktrees/<name>/`
3. 短壽容器生命週期摘要（spawn on resume、hard delete on EOD）
4. `.gitignore` 已排除 `.claude/worktrees/**`，跨機 git 操作不會傳輸 worktree 內容（worktree 為各機器 local-only state）

#### Scenario: Skill 文件包含 worktree 章節

- **WHEN** 查閱 `personal-skills/git-multi-machine/SKILL.md`
- **THEN** 文件 SHALL 包含「Worktree 約定」或等義章節，涵蓋上述四點

