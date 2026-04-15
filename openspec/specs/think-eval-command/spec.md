## ADDED Requirements

### Requirement: think:eval 提供結構化操作評估流程
`.claude/commands/think/eval.md` SHALL guide the agent through a structured evaluation of whether and how to automate an operation, covering side-effect analysis, implementation form decision, and structured output to `contexts/thought_review/`.

#### Scenario: 顯式觸發完整評估
- **WHEN** user invokes `/think:eval` with an operation topic
- **THEN** agent runs the full evaluation flow: side-effect investigation → script vs agent judgment → implementation form decision → outputs a structured record to `contexts/thought_review/YYYY-MM-DD_<topic>.md`

#### Scenario: 評估涵蓋四個維度
- **WHEN** agent runs the evaluation
- **THEN** evaluation MUST cover: (1) side effects and impact scope, (2) script vs agent judgment matrix, (3) implementation form decision (script / agent instruction / skill / docs / hybrid), (4) namespace/category assessment if a new command is proposed

#### Scenario: 輸出格式統一
- **WHEN** evaluation concludes
- **THEN** agent writes a file with frontmatter `type: eval` and sections: 問題背景 / 副作用調查 / 判斷框架 / 決策結論 / 實作建議

### Requirement: think:eval 支援隱式觸發
`eval.md` SHALL define implicit trigger patterns so the agent can proactively suggest running the evaluation when the conversation signals an automation decision.

#### Scenario: 偵測到評估訊號時主動建議
- **WHEN** conversation contains signals like「要不要寫成腳本」「適合自動化嗎」「建 skill 嗎」「這樣做有副作用嗎」
- **THEN** agent SHOULD suggest「這個問題適合用 /think:eval 評估，要跑嗎？」before proceeding with ad-hoc advice

#### Scenario: 隱式觸發不強制
- **WHEN** agent detects trigger signals
- **THEN** agent suggests but does NOT force the evaluation — user can decline and continue the conversation normally
