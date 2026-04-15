# Spec: Active State Tracker

## Requirement: State updates are conversation-driven
`projects/<name>/PROJECT.md` 中的現況、下一步等欄位 SHALL 可透過對話指示 AI 更新。

### Scenario: User reports progress in conversation
- **WHEN** 使用者在對話中說明某項目的進度變化（如「WWPF API auth 完成了」）
- **THEN** AI 應相應更新 `projects/<name>/PROJECT.md` 中的現況欄位與 `last_updated`，並同步更新 `projects/INDEX.md` 的 `last_updated`

### Scenario: User completes a project
- **WHEN** 使用者表示某個 active 專案已完成或放棄
- **THEN** AI 應將 `projects/INDEX.md` 中該條目的 status 改為 `done`，並在對話中確認

## Requirement: Observer validates state freshness
Observer SOP SHALL 包含對 `projects/INDEX.md` 的一致性檢查，識別超過閾值天數未更新的 active 專案。

### Scenario: Stale active project detected
- **WHEN** Observer 執行每日掃描，發現 `projects/INDEX.md` 中某 active 專案的 `last_updated` 超過 14 天
- **THEN** Observer 應在 `OBSERVATIONS.md` 寫入一條 🟡 Medium 觀測，提醒使用者確認該專案狀態
