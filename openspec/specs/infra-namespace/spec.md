# Spec: Infra Namespace

## Requirement: infra/ 頂層目錄收納所有基礎設施子目錄
repo 根目錄 SHALL 包含 `infra/` 目錄，其中包含 `tools/`、`periodic_jobs/`、`adhoc_jobs/` 三個子目錄，這三者 SHALL 不再出現在 repo 頂層。

### Scenario: infra 目錄結構
- **WHEN** 查看 repo 頂層目錄
- **THEN** `tools/`、`periodic_jobs/`、`adhoc_jobs/` 不出現在頂層；所有基礎設施內容位於 `infra/` 下

### Scenario: 基礎設施子目錄路徑
- **WHEN** 需要定位工具指令碼、定時任務或一次性專案
- **THEN** 路徑分別為 `infra/tools/`、`infra/periodic_jobs/`、`infra/adhoc_jobs/`

## Requirement: infra/ 子目錄職責清晰分離
`infra/` 下三個子目錄 SHALL 各有明確職責，不相互混用：

- `periodic_jobs/`：自動化排程腳本，按時執行，產出流向 `memory/`
- `tools/`：可複用的工具指令碼，按需手動執行
- `adhoc_jobs/`：一次性專案與指令碼，任務完成後歸檔

### Scenario: 新增定時任務
- **WHEN** 需要新增一個定期自動執行的腳本
- **THEN** 腳本放入 `infra/periodic_jobs/` 下，並更新 `infra/periodic_jobs/CRONTAB.md`

### Scenario: 新增可複用工具
- **WHEN** 需要新增一個可跨任務複用的工具指令碼
- **THEN** 工具放入 `infra/tools/`

### Scenario: 新增一次性專案
- **WHEN** 需要執行一次性的研究或資料處理任務
- **THEN** 在 `infra/adhoc_jobs/<project>/` 下建立專案目錄

## Requirement: CRONTAB.md 隨 periodic_jobs 移入 infra/
排程設定文件 SHALL 位於 `infra/periodic_jobs/CRONTAB.md`，不再存在於 `docs/CRONTAB.md`。

### Scenario: 查閱排程設定
- **WHEN** 使用者或 AI 需要查看定時任務的排程設定
- **THEN** 在 `infra/periodic_jobs/CRONTAB.md` 找到設定，`docs/CRONTAB.md` 不存在

## Requirement: WORKSPACE.md 路由指向 infra/ 路徑
`rules/WORKSPACE.md` SHALL 在路由規則中使用 `infra/adhoc_jobs/`、`infra/tools/`、`infra/periodic_jobs/` 路徑，不再引用舊的頂層路徑。

### Scenario: AI 路由一次性專案到 infra/adhoc_jobs
- **WHEN** AI 需要建立一次性分析任務
- **THEN** AI 在 WORKSPACE.md 中找到路由指引，將專案建立在 `infra/adhoc_jobs/<project>/`

## Requirement: Python module 路徑與 infra/ 結構一致
`infra/periodic_jobs/` 下的 Python 腳本 SHALL 可以 `python -m infra.periodic_jobs.<module>` 的形式執行，`pyproject.toml` 中的 packages 配置 SHALL 反映 `infra/` 命名空間。

### Scenario: 執行 observer 腳本
- **WHEN** 手動執行 observer
- **THEN** 指令為 `python -m infra.periodic_jobs.ai_heartbeat.src.v1.observe`，而非舊的 `python -m periodic_jobs.ai_heartbeat...`
