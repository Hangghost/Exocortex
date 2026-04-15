# Spec: Architecture Map

## Requirement: ARCHITECTURE.md 作為系統架構地圖存在於 rules/
`rules/ARCHITECTURE.md` SHALL 存在並包含以下區塊：頂層架構圖（ASCII diagram）、各頂層目錄的設計意圖與邊界說明、區塊間關係與資料流、擴展點說明。

### Scenario: 查閱頂層目錄設計意圖
- **WHEN** 開發者或 AI agent 需要了解某個頂層目錄（如 `contexts/`、`rules/`、`infra/`）為什麼存在、邊界在哪裡
- **THEN** 在 `rules/ARCHITECTURE.md` 中能找到對應區塊的設計意圖說明，而不是只有路徑資訊

### Scenario: 查閱資料流
- **WHEN** 開發者需要了解資料如何在系統中流動（如 observer.py → memory/OBSERVATIONS.md）
- **THEN** `rules/ARCHITECTURE.md` 中有明確的資料流圖或描述

## Requirement: ARCHITECTURE.md 反映當前頂層目錄結構
`rules/ARCHITECTURE.md` 中的頂層架構圖 SHALL 包含以下頂層目錄，不含已解散的 `docs/` 目錄：
- `rules/`、`memory/`、`contexts/`、`registry/`、`projects/`、`inbox/`、`openspec/`、`infra/`、`_reference/`

### Scenario: 架構圖包含 memory/ 頂層目錄
- **WHEN** 查看 `rules/ARCHITECTURE.md` 的頂層架構圖
- **THEN** 圖中包含 `memory/` 作為獨立頂層目錄，標注其為「系統記憶（observer/reflector 產出）」

### Scenario: 架構圖包含 inbox/ 頂層目錄
- **WHEN** 查看 `rules/ARCHITECTURE.md` 的頂層架構圖
- **THEN** 圖中包含 `inbox/` 作為獨立頂層目錄，標注其為「快速捕獲區」，含 `todos.md`、`reading_list.md`、`ideas.md`、`captured/`

### Scenario: 架構圖包含 infra/ 命名空間
- **WHEN** 查看 `rules/ARCHITECTURE.md` 的頂層架構圖
- **THEN** 圖中包含 `infra/` 頂層目錄，其下展示 `tools/`、`periodic_jobs/`、`adhoc_jobs/` 三個子目錄；不出現舊的頂層 `tools/`、`periodic_jobs/`、`adhoc_jobs/`

### Scenario: 架構圖不含 docs/ 目錄
- **WHEN** 查看 `rules/ARCHITECTURE.md` 的頂層架構圖
- **THEN** 圖中不出現 `docs/` 目錄；原 `docs/CRONTAB.md` 對應位置為 `infra/periodic_jobs/CRONTAB.md`，原 `docs/experiments/` 對應位置為 `openspec/experiments/`

## Requirement: ARCHITECTURE.md 各區塊設計意圖與資料流路徑正確
`rules/ARCHITECTURE.md` 中所有路徑引用 SHALL 使用當前正確路徑，不含已廢棄的舊路徑（`contexts/memory/`、`^tools/`、`^periodic_jobs/`、`^adhoc_jobs/`、`^docs/`）。

### Scenario: observer 資料流路徑正確
- **WHEN** 查看 `rules/ARCHITECTURE.md` 的資料流圖
- **THEN** observer 的輸出路徑為 `memory/OBSERVATIONS.md`，而非 `contexts/memory/OBSERVATIONS.md`

### Scenario: infra 區塊的路徑正確
- **WHEN** 查看 `rules/ARCHITECTURE.md` 中 infra/ 的設計意圖說明
- **THEN** 排程設定參考路徑為 `infra/periodic_jobs/CRONTAB.md`

## Requirement: ARCHITECTURE.md 隨架構級變更更新
`rules/ARCHITECTURE.md` SHALL 在每次「新增或刪除頂層目錄、改變資料流向」的架構變更後更新，以反映最新的系統結構。

### Scenario: 新增頂層目錄後的更新
- **WHEN** 使用者透過 ctx:arch 或 ctx:merge 完成了新增頂層目錄的變更
- **THEN** 工作流提示使用者確認是否需要更新 ARCHITECTURE.md，若是則更新對應區塊

## Requirement: Agent 知道何時應主動查閱 ARCHITECTURE.md
`rules/WORKSPACE.md` SHALL 包含一行指引，說明查閱 ARCHITECTURE.md 的時機（架構變更前、設計新功能前）。

### Scenario: Agent 設計新功能前
- **WHEN** AI agent 收到「設計新功能」或「架構變更」類型的任務
- **THEN** agent 在 WORKSPACE.md 中找到指引，主動讀取 ARCHITECTURE.md 取得全局視角後再開始設計
