# Spec: ctx:publish Command

## Purpose

規範 `/ctx:publish` 指令，將 private repo 的架構變更發布到 public template repo（Exocortex）。定義檔案分類 taxonomy（pure-arch / structural / personal）及各類型的處理策略，確保個人資料不會洩漏至公開 repo。

## Requirements

### Requirement: Publish Command 入口
系統 SHALL 提供 `ctx:publish` command，讓使用者從 private repo 將架構變更發布到 public template repo。

#### Scenario: 基本調用
- **WHEN** 使用者執行 `ctx:publish`
- **THEN** command 掃描 `openspec/changes/archive/`，列出尚未 publish（無 `published.md`）的 changes，供使用者選擇

#### Scenario: 無未 publish changes
- **WHEN** 所有 archive entries 都已有 `published.md`
- **THEN** command 告知「無待發布的 changes」並結束

---

### Requirement: 檔案分類 Taxonomy
Command SHALL 依據以下 taxonomy 對每個待 publish 的檔案做分類：

| 類型 | 策略 | Patterns |
|------|------|---------|
| `pure-arch` | copy verbatim | `.claude/skills/**`, `rules/skills/**`, `infra/tools/**`, `infra/periodic_jobs/**` |
| `structural` | AI semantic merge | `CLAUDE.md`, `rules/CORE.md`, `rules/WORKSPACE.md`, `rules/ARCHITECTURE.md`, `rules/COMMUNICATION.md`, `.gitignore`, `pyproject.toml` |
| `personal-struct` | skip | `rules/USER.md`, `rules/ENVIRONMENT.md`, `rules/SOUL.md`, `registry/**`, `inbox/**` |
| `never` | skip | `openspec/changes/**`, `memory/**`, `contexts/**`, `projects/**`, `library/**` |

#### Scenario: Pure-arch 檔案處理
- **WHEN** 一個被修改的檔案符合 `pure-arch` pattern
- **THEN** 該檔案被納入 copy list，無需 AI 判斷

#### Scenario: Structural 檔案處理
- **WHEN** 一個被修改的檔案符合 `structural` pattern
- **THEN** AI 讀取 private diff + template 現有版本 + openspec proposal，產出 merged content 展示在 PUBLISH PLAN 中

#### Scenario: Personal 或 Never 類檔案
- **WHEN** 一個被修改的檔案符合 `personal-struct` 或 `never` pattern
- **THEN** 該檔案被標記為 skip，不出現在 PUBLISH PLAN 的 apply 清單中

---

### Requirement: PUBLISH PLAN 產出與確認
Command SHALL 在執行任何 apply 動作之前，產出完整的 PUBLISH PLAN 供使用者審閱。

#### Scenario: Plan 格式
- **WHEN** PUBLISH PLAN 產出
- **THEN** 包含三個區塊：(1) COPY 清單（pure-arch 檔案），(2) MERGE PREVIEW（structural 檔案的 proposed content），(3) SKIP 清單（personal/never 檔案，標明原因）

#### Scenario: 使用者確認後執行
- **WHEN** 使用者確認 PUBLISH PLAN
- **THEN** command apply 所有 copy 操作到 `~/Documents/Projects/Exocortex/`，寫入 structural 檔案的 merged content，然後在 template clone 執行 `git add` + `git commit`（不自動 push）

#### Scenario: 使用者拒絕 Plan
- **WHEN** 使用者拒絕 PUBLISH PLAN（或要求修改）
- **THEN** command 停止，不執行任何 apply 操作；使用者可調整後重新執行

---

### Requirement: Published Marker 追蹤
Command SHALL 在每個成功發布的 change archive 目錄建立 `published.md` marker。

#### Scenario: Marker 建立時機
- **WHEN** publish 成功完成（commit 產生）
- **THEN** 在 `openspec/changes/archive/<change-name>/published.md` 建立檔案，記錄 `published_at`（日期）與 `template_commit`（commit hash）

#### Scenario: 多 change 批次 publish
- **WHEN** 使用者選擇多個 changes 一起 publish
- **THEN** 所有 changes 的檔案合併處理，產出單一 PUBLISH PLAN；成功後每個 change 各自建立 `published.md`

---

### Requirement: Template Clone 前置同步
Command SHALL 在 apply 前確保 template local clone 與 remote 同步。

#### Scenario: 執行前 pull
- **WHEN** command 準備執行 apply
- **THEN** 先對 `~/Documents/Projects/Exocortex/` 執行 `git pull`，確認無衝突後再繼續
