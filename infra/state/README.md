# infra/state — 系統執行狀態紀錄

兩層 state 結構，給 periodic jobs 與互動命令（如 `opsx:archive`）協調用。

```
infra/state/
├── README.md           ← 本檔（schema 說明）
├── lib.py              ← 共用 helper（read/update state、write run log）
├── system_state.json   ← 全域 high-water mark cache（git-tracked）
└── test_lib.py         ← 單元測試
```

## 兩層 state 的職責分離

| 層 | 路徑 | git | 用途 |
|---|---|---|---|
| **State cache** | `infra/state/system_state.json` | ✅ tracked | 全域 high-water mark；consumer 讀取「上次成功跑到哪」；跨機器共享 |
| **Run log** | `raw_signals/<date>/<role>_run.json` | ❌ ignored | 當日 audit log；事後審計、state_audit 偵測 missed-run |

**為什麼分兩層**：跨機器協調必須用 git（cache 進 git）；但完整歷史進 git 會產生大量 commit noise（每天 ~6 元件 × 365 天）→ 折衷：當前狀態進 git，歷史審計留 local。

## `system_state.json` schema

```json
{
  "version": 1,
  "roles": {
    "observer": {
      "last_started_at": "2026-05-01T20:00:00+08:00",
      "last_finished_at": "2026-05-01T20:01:42+08:00",
      "last_target_date": "2026-05-01",
      "last_status": "ok"
    },
    "reflector":     { "...": "..." },
    "state_audit":   { "...": "..." },
    "capture":       { "...": "..." },
    "triage_stage1": { "...": "..." },
    "triage_stage2": { "...": "..." }
  }
}
```

欄位語意：

- `version`: 整數，目前為 `1`。Consumer 遇到未知版本 SHALL fallback 至原啟發式策略。
- `roles.<role>.last_started_at`: ISO 8601 timestamp（含 timezone），最近一次進入主流程的時間。
- `roles.<role>.last_finished_at`: ISO 8601 timestamp 或 `null`（若 `last_status=running`）。
- `roles.<role>.last_target_date`: `YYYY-MM-DD` 字串，該次執行的目標日期。
- `roles.<role>.last_status`: `"running"` / `"ok"` / `"failed"` 之一。

## Run log schema (`raw_signals/<date>/<role>_run.json`)

```json
{
  "kind": "observer_run",
  "role": "observer",
  "started_at": "2026-05-01T20:00:00+08:00",
  "finished_at": "2026-05-01T20:01:42+08:00",
  "target_date": "2026-05-01",
  "status": "ok",
  "session_id": "<observer/reflector only>"
}
```

失敗時可加 `error_summary` 欄位記錄例外摘要。

## 寫入時機（每個 role 三段論）

1. **進入主流程前**：寫 `last_status: "running"` + `last_started_at`
2. **成功完成**：寫 `last_status: "ok"` + `last_finished_at`，並寫 run log
3. **例外**：寫 `last_status: "failed"` + `last_finished_at`，並寫含 `error_summary` 的 run log

所有寫入 SHALL 採用 atomic write（先寫 `.tmp` 後 `os.replace`）。

## Consumer fallback 行為

讀 state 失敗（檔案不存在 / JSON parse 失敗 / 缺角色 / 未知版本）時 SHALL 降級至原啟發式策略，並 log 一條 🟢 提示。詳見各 spec：
- `openspec/specs/v1-observer/spec.md`
- `openspec/specs/observer-openspec-scanning/spec.md`
- `openspec/specs/system-state-coordination/spec.md`

## 跨機器同步

`system_state.json` 進 git；`raw_signals/` 進 `.gitignore`。多台機器 pull 後讀同一份 state；conflict 極罕見（同時間單機跑某 role），發生時手動 resolve（取較新者覆蓋）。
