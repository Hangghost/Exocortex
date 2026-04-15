# Spec: Reflector Promotion Framework

## Requirements

### Requirement: Reflector defines its target audience

Reflector 的 SOP SHALL 明確定義晉升目標受眾為**未來的 AI agent**。rules/ 作為每個 session 開始時被動載入的行動指南，每一條晉升內容都 MUST 讓 AI 在執行任務時能立即應用，而非作為歷史記錄或背景知識。

#### Scenario: 判斷一條觀測是否值得晉升
- **WHEN** Reflector 評估一條 🔴 High 觀測
- **THEN** 核心問題 MUST 是「未來的 AI agent 讀到這條，能做出不同的（更好的）行動嗎？」，而非「這條知識值得記錄嗎？」

#### Scenario: rationale-only 觀測不晉升
- **WHEN** 一條觀測描述的是設計決策的理由（為什麼這樣做），而非可操作的指令
- **THEN** Reflector SHALL 將其 GC，標記為 `rationale-only`，不晉升到任何 rules/ 檔案

---

### Requirement: Two-phase promotion judgment

Reflector MUST 對每條 🔴/🟡 觀測執行兩階段判斷，Phase 1 在 Phase 2 之前完成。

#### Scenario: Phase 1 - 判斷是否晉升
- **WHEN** Reflector 處理一條觀測
- **THEN** SHALL 先分類為以下四類之一，再決定是否進入 Phase 2：
  - `PROMOTE`：AI 讀到後能做出更好的行動 → 進入 Phase 2
  - `NOT_YET`：只出現一次，尚未跨情境驗證 → 保留到下次 Reflector
  - `ALREADY_IN_RULES`：對照現有 rules/ 確認已涵蓋 → 直接 GC
  - `DISCARD`：過於情境特定或 rationale-only → GC 並記錄原因

#### Scenario: Phase 2 - 落點與知識模式判斷
- **WHEN** 一條觀測被分類為 `PROMOTE`
- **THEN** Reflector SHALL 判斷其知識模式，並對應到目標檔案：
  - 模式 A（觸發式約束：「當 X 出現時，做 Y」）→ `rules/axioms/` 或 skill guardrails
  - 模式 B（環境事實：「系統的 X 是 Y」）→ `rules/ENVIRONMENT.md`
  - 模式 C（設計原則：「做 X 類決策時，優先 Y」）→ `rules/COMMUNICATION.md` Agentic Principles 或 `rules/skills/` 設計指南
  - 不確定模式 → 預設放 `rules/axioms/`（最中性的位置）

---

### Requirement: Purpose Statement and Reader Test per target file

每個 rules/ 目標檔案 SHALL 在 Reflector SOP 中有對應的 Purpose Statement 和 Reader Test，作為 Phase 2 落點判斷的依據。

#### Scenario: 落點判斷通過 Reader Test
- **WHEN** Reflector 決定將知識放入某個 rules/ 檔案
- **THEN** MUST 驗證：「未來的 AI agent 讀完這個檔案，能直觀理解為什麼這條知識在這裡」

#### Scenario: Reader Test 失敗時不強行晉升
- **WHEN** 某條知識無法自然符合任何目標檔案的 Reader Test
- **THEN** Reflector SHALL 優先使用 `rules/axioms/` 作為 fallback，而非強行放入語意不符的檔案

---

### Requirement: Justified GC for High priority observations

任何被 GC 的 🔴 High 觀測 MUST 記錄不晉升原因，使用標準分類標籤。

#### Scenario: 記錄 GC 原因
- **WHEN** Reflector 決定 GC 一條 🔴 High 觀測
- **THEN** SHALL 在 GC 動作的彙報中標記原因：
  - `already-derivable`：可從當前 rules/ 或系統結構直接推導
  - `rationale-only`：只是設計理由，不含行動指令
  - `one-time-event`：只出現一次，留 `NOT_YET` 更適合
  - `promoted`：已晉升（標記目標檔案）

---

### Requirement: Content transformation from event to instruction

Reflector 在晉升內容時 MUST 將觀測文字（過去式事件記錄）轉換為行動指令（現在式可操作規則）。

#### Scenario: 轉換觀測為行動指令
- **WHEN** Reflector 晉升一條觀測到 rules/
- **THEN** 晉升後的文字 SHALL 使用現在式，描述 AI 應執行的行動或判斷，而非描述過去發生的事件

#### Scenario: 避免直接複製觀測文字
- **WHEN** 觀測文字以「完成」「確認」「發現」等過去式動詞描述事件
- **THEN** Reflector MUST 將其改寫為對應的行動指令，而非直接複製貼上
