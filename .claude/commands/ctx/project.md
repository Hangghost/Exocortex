---
name: ctx:project
description: 專案脈絡管理。`new` 建立、`load` 載入、`update` 更新進度、`complete` 完成歸檔、`pause` 暫停、`resume` 恢復。
---

專案脈絡管理指令。支援六個子命令：`new`、`load`、`update`、`complete`、`pause`、`resume`。

**Input**: `$ARGUMENTS`
- `new` → 互動式建立新專案
- `load <name>` → 載入指定專案的脈絡
- `update <name>` → 結構化更新專案進度，產出 work_log
- `complete <name>` → 觸發回顧問答，將專案標記為已完成
- `pause <name>` → 將專案狀態改為 paused
- `resume <name>` → 將 paused 專案恢復為 active
- `rename <old> <new>` → 重新命名專案（更新目錄、INDEX.md、所有 contexts frontmatter）
- 空白或其他 → 顯示使用說明與現有專案列表

---

## 子命令：new

互動式引導使用者建立新專案。

### 步驟

1. **詢問基本資訊**

   用 AskUserQuestion 詢問：
   - 專案名稱（kebab-case，例：`my-project`）
   - 一句話描述

2. **建立目錄結構**

   ```bash
   mkdir -p projects/<name>/context
   ```

3. **收集專案資訊（6 個問題）**

   逐一詢問（使用者可跳過，稍後填入）：
   1. 這個專案的目標是什麼？
   2. 現在進展到哪裡？什麼已經 work，什麼還沒？
   3. 最近的下一步是什麼？
   4. 有哪些資料來源要追蹤？（Codebase 路徑、Jira ticket/project、OpenSpec change 名稱、其他文件）

      OpenSpec 條目支援狀態子格式，可選擇性使用：
      ```
      - **OpenSpec** (<label>):
        - ✅ `<change-name>` — archived <YYYY-MM-DD>, commit `<sha>`
        - 🔄 `<change-name>` — started <YYYY-MM-DD>, last commit `<sha>` (<YYYY-MM-DD>)
        - ⬜ `<change-name>` — planned
      ```
      若暫不確定狀態，可先用簡單格式：`- **OpenSpec** (<label>): <change-name>, ...`（視為未知狀態）
   5. 有沒有已經決定不要再討論的事？（關鍵決策）
   6. 有沒有特殊的環境設定要記錄？（帳號、endpoints 等）

4. **建立 PROJECT.md**

   根據使用者回答填入 `projects/<name>/PROJECT.md`，未填的區塊保留佔位符（`<!-- 待填入 -->`）。問題 4 的資料來源回答解析為 `## 資料來源` 的結構化列表；若使用者跳過問題 4，僅保留 Work Logs 預設條目：

   ```markdown
   ---
   last_updated: YYYY-MM-DD
   status: active
   ---

   # <Project Name>

   ## 目標 / 動機

   <使用者回答，或 <!-- 待填入 -->>

   ## 現況

   <使用者回答，或 <!-- 待填入 -->>

   ## 下一步

   <使用者回答，或 <!-- 待填入 -->>

   ## 關鍵決策（已定案，不再討論）

   <使用者回答，或 <!-- 待填入 -->>

   ## 材料地圖

   <使用者回答，或 <!-- 待填入 -->>

   **Work Logs**：`contexts/work_logs/` 中 `project: <name>` 的條目

   ## 資料來源

   <使用者回答解析為列表，或以下預設>
   - **Work Logs**: 自動（`project: <name>`）
   ```

5. **更新 projects/INDEX.md**

   在 table 中新增一行：
   ```
   | <name> | active | YYYY-MM-DD | <描述> |
   ```

6. **回報完成**

   告知使用者已建立：
   - `projects/<name>/PROJECT.md`
   - `projects/<name>/context/`（空目錄，按需使用）
   - `projects/INDEX.md` 已更新

---

## 子命令：load \<name\>

將指定專案的脈絡帶入目前 session。

### 步驟

1. **確認專案存在**

   檢查 `projects/<name>/PROJECT.md` 是否存在。

   - **若不存在**：告知使用者，並讀取 `projects/INDEX.md` 列出現有專案
   - **若存在**：繼續

2. **讀取 PROJECT.md**

   讀取 `projects/<name>/PROJECT.md` 的完整內容。

3. **搜尋相關 work logs**

   搜尋 `contexts/work_logs/` 中包含 `project: <name>` 的檔案：

   ```bash
   grep -rl "project: <name>" contexts/work_logs/
   ```

   若有結果，列出最近 5 筆（依檔名日期排序，最新在前），顯示在摘要中。

4. **回報現況摘要**

   以簡短的格式回報（3 個要點）：
   - **目標**：<一句話>
   - **現況**：<key points>
   - **下一步**：<具體行動>

   若有相關 work logs，附加：
   - **相關 Work Logs**（最近 5 筆）：
     - `contexts/work_logs/YYYY-MM-DD_<name>_update.md`
     - …

   結尾補充：「如需深度技術細節，可讀取 `projects/<name>/context/` 下的文件。」

   若專案 status 為 `paused`，在摘要末尾附加提醒：「此專案目前為暫停狀態。如果你準備繼續工作，可以用 `/ctx:project resume <name>` 重新啟動。」

### 隱式 load

當使用者在對話中提到已知專案名稱（如「繼續做 WWPF」、「看一下 exocortex 的狀態」），AI SHOULD 主動讀取對應的 PROJECT.md，即使使用者未明確執行 load 指令。

---

## 子命令：update \<name\>

結構化更新專案進度。先主動蒐集已知資料來源的進展資料，呈現查詢結果，再以確認性問題引導使用者補充，最終同步 PROJECT.md 並產出 work_log。

### 步驟

1. **確認專案存在**

   檢查 `projects/<name>/PROJECT.md` 是否存在。

   - **若不存在**：告知使用者，並讀取 `projects/INDEX.md` 列出現有專案，停止
   - **若存在**：繼續

2. **讀取 PROJECT.md**

   讀取完整 `projects/<name>/PROJECT.md`，取得「現況」、「下一步」、`## 資料來源`。

3. **Smart-Gather 階段（自動查詢，不需使用者確認）**

   依序執行以下查詢：

   a. **Work Logs**（永遠查）：掃描 `contexts/work_logs/` 中包含 `project: <name>` 的檔案，取最近 5 筆（依檔名日期排序）

   b. **Git 主線查詢**（若 `## 資料來源` 有 Git path）：
      - 依序嘗試 `## 資料來源` 中列出的每個 Git path
      - 執行 `git -C <path> log --oneline -20`，第一個成功回傳結果的路徑即採用
      - 路徑不可達時繼續嘗試下一個，不中斷流程
      - **Git 查詢永遠執行，不因 OpenSpec 存在而跳過**

   c. **Local OpenSpec 補充**（若 `## 資料來源` 有 OpenSpec 條目）：
      - 對每個 OpenSpec change name，檢查 `openspec/changes/<change-name>/` 是否在本地存在
      - 若存在：讀取 `tasks.md`，以任務完成度補充 Git 查詢結果（不替代 Git log）
      - 若不存在（外部 repo 或已 archive）：不嘗試讀取，視為狀態參考欄位
      - **格式解析**：OpenSpec 條目支援新舊兩種格式：
        - 新格式（含 ✅/🔄/⬜ 狀態標記）：按狀態呈現
        - 舊格式（無狀態標記，純 change name 列表）：視為未知狀態，不嘗試解析狀態

   d. **Archive commit 偵測**（若已執行 Git 查詢）：
      - 掃描 Git log 中符合 `docs(openspec): archive` pattern 的 commit
      - 解析每個符合 commit 的 change name（支援單一或多個）及 commit SHA 與日期
      - 暫存偵測結果，於步驟 5 呈現

   e. **無 `## 資料來源` 的舊專案**：
      - 僅執行 Work Logs 查詢
      - 嘗試 best-effort 解析 `## 材料地圖` 中是否含有 git/jira/openspec 路徑，若有則使用
      - 查詢完成後在末尾提示：「此專案尚未設定 `## 資料來源`，要建立嗎？[y/N]」（不阻斷流程）

4. **外部來源確認（需使用者同意才查詢）**

   若 `## 資料來源` 包含 Jira 或其他外部 API 來源：
   - 詢問：「偵測到 Jira 來源（<tickets>），要查詢嗎？[y/N]」
   - 使用者確認後才執行 MCP 查詢

5. **呈現查詢結果（含 archive 偵測確認）**

   以清單格式顯示：
   ```
   已查詢的來源：
     ✓ Work Logs  — <N> 筆（最近：YYYY-MM-DD）
     ✓ Git        — <path>（最近：<sha> <message>）
     ✓ OpenSpec   — <change-name>（<N>/<M> tasks done）[補充]
     ✗ OpenSpec   — <change-name>（外部 repo，狀態參考欄位）
     ✓ Jira       — PROJ-123（Done）、PROJ-124（In Progress）
     ✗ Jira       — 未查詢（使用者跳過）
   ```

   接著提供初步進展摘要（synthesis）：根據蒐集資料合成一段描述，盡力而為。

   **Archive 偵測確認**（若步驟 3d 偵測到 archive commit）：
   - 顯示：
     ```
     偵測到以下 changes 已 archived：
       - `<change-name>` — archived <YYYY-MM-DD>, commit `<sha>`
       ...
     要更新 ## 資料來源 嗎？[y/N]
     ```
   - 使用者確認（y）：更新 PROJECT.md 對應 OpenSpec 條目，將該 change 標記為 `✅ <change-name> — archived <date>, commit <sha>`（若條目為舊格式，以新格式覆寫）
   - 使用者拒絕（N）：不修改 PROJECT.md，繼續流程

   最後詢問：「以上有沒有遺漏的來源？」

6. **確認性問題（可跳過）**

   逐一詢問，使用者可直接 Enter 跳過：

   1. **進展確認**：「根據資料，整理的進展如下：\n[synthesis 草稿]\n有要補充或修正嗎？」
   2. **經驗觀察**（開放式）：「有學到什麼或踩到什麼坑？」
   3. **下一步**（開放式）：「下一步有改變嗎？」

7. **來源偵測（從使用者回答中識別新來源）**

   若使用者在問題 1-3 的回答中提到未登錄的來源（路徑、Jira key 如 `PROJ-\d+`、openspec change 名稱）：
   - 詢問：「偵測到新來源 `<value>`，要加入 `## 資料來源` 嗎？[y/N]」
   - 使用者確認後：在 PROJECT.md 的 `## 資料來源` 追加 `- **<type>**: <value>`

8. **更新 PROJECT.md**

   - 根據使用者回答更新「現況」與「下一步」section
   - 更新 frontmatter 的 `last_updated` 為今天日期（格式：YYYY-MM-DD）

9. **同步 INDEX.md**

   更新 `projects/INDEX.md` 對應行的 `last_updated` 為今天日期。

10. **產出 work_log（至少一個確認性問題有回答才產出）**

    建立 `contexts/work_logs/YYYY-MM-DD_<project-name>_update.md`：
    ```markdown
    ---
    project: <name>
    date: YYYY-MM-DD
    type: update
    ---

    # <Project Name> — 進度更新

    ## 進展
    <整合 smart-gather 資料與使用者補充後的完整進展，或（未提供）>

    ## 經驗與觀察
    <使用者回答，或（未提供）>

    ## 下一步
    <更新後的下一步，或（未提供）>
    ```

    - 若三個問題全部跳過：僅更新 `last_updated`，**不產出** work_log
    - 若同天已有 work_log：檔名加序號後綴（如 `_update_2.md`）

11. **若專案 status 為 `paused`**：在完成後附加提醒：「此專案目前為暫停狀態，但你剛更新了進度。要改回 active 嗎？」並等待使用者確認。

---

## 子命令：complete \<name\>

引導使用者做專案回顧，產出 retrospective work_log，將專案標記為已完成。

### 步驟

1. **確認專案存在且可完成**

   - 若不存在：告知使用者，列出現有專案，停止
   - 若 status 已為 `completed` 或 `archived`：告知使用者該專案已完成，停止

2. **顯示專案摘要**

   讀取 `projects/<name>/PROJECT.md`，顯示目標與主要成果。

3. **詢問五個回顧問題（可跳過）**

   逐一詢問，使用者可直接 Enter 跳過：
   1. 這個專案最終達成了什麼？
   2. 什麼做得好、值得未來重複？
   3. 什麼做得不好或可以改進？
   4. 有哪些意外的發現或學習？
   5. 如果重來一次，會有什麼不同的做法？

4. **產出 retrospective work_log（無論是否回答都產出）**

   建立 `contexts/work_logs/YYYY-MM-DD_<project-name>_retrospective.md`：
   ```markdown
   ---
   project: <name>
   date: YYYY-MM-DD
   type: retrospective
   ---

   # <Project Name> — 專案回顧

   ## 達成成果
   <使用者回答，或（未提供）>

   ## 成功經驗
   <使用者回答，或（未提供）>

   ## 改進空間
   <使用者回答，或（未提供）>

   ## 意外發現
   <使用者回答，或（未提供）>

   ## 如果重來
   <使用者回答，或（未提供）>
   ```

5. **更新 PROJECT.md**

   - frontmatter：`status` → `completed`，新增 `completed_date: YYYY-MM-DD`，更新 `last_updated`

6. **更新 INDEX.md**

   - 對應行：`status` → `completed`，`last_updated` → 今天

7. **回報完成**

   告知使用者專案已標記為已完成，retrospective work_log 已寫入 `contexts/work_logs/`。

---

## 子命令：pause \<name\>

將進行中的專案暫停，staleness check 將不再觸發。

### 步驟

1. **確認專案存在且狀態為 active**

   - 若不存在：告知使用者，列出現有專案，停止
   - 若 status 不是 `active`：告知使用者目前狀態，建議適當操作，停止

2. **更新 PROJECT.md**

   - frontmatter：`status` → `paused`，`last_updated` → 今天

3. **更新 INDEX.md**

   - 對應行：`status` → `paused`，`last_updated` → 今天

4. **回報完成**

   告知使用者專案已暫停，staleness check 將不再觸發。如需恢復，使用 `/ctx:project resume <name>`。

---

## 子命令：resume \<name\>

將暫停的專案恢復為 active 狀態。

### 步驟

1. **確認專案存在且狀態為 paused**

   - 若不存在：告知使用者，列出現有專案，停止
   - 若 status 不是 `paused`：告知使用者目前狀態，建議適當操作，停止

2. **更新 PROJECT.md**

   - frontmatter：`status` → `active`，`last_updated` → 今天

3. **更新 INDEX.md**

   - 對應行：`status` → `active`，`last_updated` → 今天

4. **顯示現況摘要**

   讀取 PROJECT.md 顯示簡短摘要（目標、現況、下一步），協助使用者回到工作狀態。

---

## 子命令：rename \<old\> \<new\>

確定性地重新命名專案：移動目錄、更新 INDEX.md、batch-replace 所有 contexts frontmatter。

### 步驟

1. **確認參數格式**

   - `<old>` 和 `<new>` 都必須是 kebab-case
   - 若格式不符，提示使用者修正

2. **執行腳本**

   ```bash
   python infra/tools/rename_project.py <old> <new>
   ```

   腳本會依序：
   - `mv projects/<old>/ → projects/<new>/`（保留 git history）
   - 更新 `projects/INDEX.md` 中的名稱欄位
   - Batch-replace `contexts/work_logs/`、`contexts/thought_review/`、`contexts/blog/` 中所有 `project: <old>` frontmatter

3. **確認輸出**

   讀取腳本輸出，確認各步驟完成狀態。若腳本報錯（`<old>` 不存在、`<new>` 已存在），直接回報錯誤給使用者，不繼續。

4. **回報完成**

   顯示：
   - 哪些目錄和檔案被更新
   - 受影響的 context 檔案數量
   - 提醒使用者：openspec/changes/ 僅連結 change 名稱，無需更新

---

## 無子命令 / 使用說明

若 `$ARGUMENTS` 為空白或不認識的子命令：

1. 顯示使用說明（new / load / update / complete / pause / resume）
2. 讀取 `projects/INDEX.md` 列出現有專案

---

## Guardrails

- 專案名稱必須是 kebab-case，建立前若使用者輸入非 kebab-case 格式，提示修正
- `context/` 下的文件 **不** 在 load 時自動載入——按需由 AI 自行判斷讀取
- `load` 只讀 PROJECT.md，不掃描 context/
- 建立新專案後，`projects/INDEX.md` 必須同步更新
