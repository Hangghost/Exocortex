## ADDED Requirements

### Requirement: think: 命名空間定義與歸屬規則
`ARCHITECTURE.md` 的擴展點表格 SHALL include `think:` namespace definition as a distinct category for daily-use thinking tools, separate from `ctx:` (architecture development) and `opsx:` (design workflow).

#### Scenario: 新工具歸屬判斷
- **WHEN** a new command is being created and the category is unclear
- **THEN** agent SHALL ask: is this tool used during (a) architecture development → `ctx:`, (b) OpenSpec design flow → `opsx:`, (c) daily framework usage / thinking aid → `think:`, (d) global utility → no namespace
