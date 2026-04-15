# contexts/MANIFEST.md

此文件定義 `contexts/` 下每個子資料夾的觀察 schema，是 observer 掃描前的設定來源，也是新增子資料夾時的設計參考。

## 如何使用

**Observer**：掃描 `contexts/` 前必須讀取此文件，依各資料夾的 `observation_mode` 決定處理方式。未在此定義的資料夾，執行預設 fallback（見下方說明）。

**新增子資料夾**：在此文件新增一個條目，定義以下兩個欄位：
- `observation_mode`：觀察模式，必須為合法值之一（見下方）
- `extraction_focus`：提取重點，描述 observer 應關注的內容類型

**合法的 `observation_mode` 值**：
- `ignore`：不掃描此資料夾（高重複、低資訊密度）
- `read_content`：讀取近期修改檔案的全文，提取觀察條目
- `read_content+personal_facts`：讀全文且額外執行 PersonalFacts 提取（見 KNOWLEDGE_BASE.md Section 8）
- `skip`：此資料夾是 observer 的輸出目標，不作為輸入來源

**未定義資料夾的 fallback 行為**：以 `read_content` 模式處理，標記 🟢 Low，並在觀察條目中記錄「此資料夾尚未在 MANIFEST.md 定義 schema」。

---

## 子資料夾 Schema

### `blog/`

```
observation_mode: read_content+personal_facts
extraction_focus: 使用者主動思考的文章草稿、觀點立場、方法論提煉、個人事實（設備、工具選擇、環境變化）
```

### `work_logs/`

```
observation_mode: read_content
extraction_focus: 任務執行過程、進度里程碑、產出結果
```

### `survey_sessions/`

```
observation_mode: read_content+personal_facts
extraction_focus: 研究發現、個人環境事實（設備、帳號、工具、工作流限制）
frontmatter_schema:
  date: YYYY-MM-DD        # 必填
  topic: <主題描述>        # 必填
  tags: [tag1, tag2]      # 必填
```

### `thought_review/`

```
observation_mode: read_content+personal_facts
extraction_focus: 個人環境事實（設備、帳號、工具、工作流限制）；方法論提煉不在此範疇
special_types:
  - type: eval（frontmatter type: eval）→ 識別操作評估紀錄，提取決策結論與實作建議，可晉升為 axioms 或 skill
```

<!-- TODO: Add entries for any additional context subdirectories you create.
     Example:
     ### `reading_notes/`
     ```
     observation_mode: read_content
     extraction_focus: key insights from books/articles, emerging themes
     ```
-->
