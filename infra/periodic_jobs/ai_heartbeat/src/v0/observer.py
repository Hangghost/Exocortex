#!/usr/bin/env python3
"""
L1 Observer Agent (Trigger Script)
Instructs OpenCode-Builder to autonomously scan, filter, and write to memory.
"""
import os
import sys
import time
from datetime import datetime
from opencode_client import OpenCodeClient

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
KNOWLEDGE_BASE = os.path.join(REPO_ROOT, "infra", "periodic_jobs", "ai_heartbeat", "docs", "KNOWLEDGE_BASE.md")
OBSERVATIONS_PATH = os.path.join(REPO_ROOT, "memory", "OBSERVATIONS.md")

PROMPT_TEMPLATE = """
【目標】：執行觀測記憶提取並直接持久化到磁碟。
【基準日期】：{target_date}

【冪等性約束】：在執行任何寫入前，**必須先**執行以下指令精確檢查：
```
grep -c "^Date: {target_date}$" {observations_path}
```
若輸出 > 0，代表條目已存在，**不要進行任何檔案修改**，直接回復「Entry for {target_date} already exists, skipping」即可。注意：檔名或內文中出現 `{target_date}` 不算，只有行首完整符合 `Date: {target_date}` 才算已存在。

【SOP 路徑】：
{kb_path}

【任務內容】：
1. **獲取 Context**：請閱讀上述 SOP 以及其中引用的 L3 約束檔案。
2. **冪等性檢查**：執行 `grep -c "^Date: {target_date}$" {observations_path}`，若輸出 > 0 則跳過後續步驟。
3. **掃描與過濾**：自主掃描根目錄（{repo_root}）下的變動。
4. **寫入記憶**：將針對 {target_date} 的 🔴 🟡 🟢 觀測結果直接寫入或追加到 `{observations_path}`。**鼓勵使用命令列 append**（如 `echo "..." >> OBSERVATIONS.md` 或 `tee -a`），避免對大檔案做全文編輯。
5. **範圍約束**：**僅執行 L1 Observer 任務**。不要執行 SOP 中提到的 L2 Reflector 任務（即不要修改 `rules/` 下的任何檔案，不要進行規則晉升或垃圾回收）。
6. **格式規範**：
   - 日期 Header 必須嚴格使用 `Date: YYYY-MM-DD` 格式（Date 首字母大寫，冒號後空格，日期為 ISO 格式）。
   - 在結果檔案中提到任何檔案或目錄時，**必須使用相對於根目錄的完整路徑**（例如：`rules/skills/workflow_deep_research_survey.md`），不要只寫檔名。
7. **彙報**：完成後，在此回覆一個簡短的 Walkthrough。
"""

def main():
    os.environ.setdefault("OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX", "16000")
    import argparse
    parser = argparse.ArgumentParser(description='L1 Observer Agent')
    parser.add_argument('date', nargs='?', default=datetime.now().strftime("%Y-%m-%d"),
                        help='Target date (YYYY-MM-DD)')
    parser.add_argument('--model', default='anthropic/claude-haiku-4-5-20251001',
                        help='Model ID to use (e.g. gemini-3-flash-preview, anthropic/claude-haiku-4-5-20251001, openai/gpt-4o-mini)')
    parser.add_argument('--no-delete', action='store_true',
                        help='Keep session after completion (default: delete)')
    args = parser.parse_args()

    target_date = args.date
    model_id = args.model
    delete_after = not args.no_delete

    # Idempotency: skip if entry for target_date already exists
    if os.path.exists(OBSERVATIONS_PATH):
        with open(OBSERVATIONS_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        if f"Date: {target_date}" in content:
            print(f"Idempotent skip: entry for {target_date} already exists in OBSERVATIONS.md")
            return

    print(f"Triggering Fully Agentic Observer for date: {target_date} using model: {model_id}...")
    client = OpenCodeClient()
    
    session_id = client.create_session(f"Heartbeat L1 - Persistence Mode - {target_date}")
    if not session_id:
        return
        
    prompt = PROMPT_TEMPLATE.format(kb_path=KNOWLEDGE_BASE, target_date=target_date, repo_root=REPO_ROOT, observations_path=OBSERVATIONS_PATH)
    client.send_message(session_id, prompt, model_id=model_id)
    # If send_message timed out, agent may still be running; poll until done
    print("Waiting for session to complete (sync mode)...")
    client.wait_for_session_complete(session_id)
    # Ephemeral: delete session by default (--no-delete to keep)
    if delete_after:
        if client.delete_session(session_id):
            print(f"Task complete (session {session_id} deleted).")
        else:
            print(f"Task complete (Session: {session_id}).")
    else:
        print(f"Task complete (Session: {session_id}).")

    # Post-process: collapse extra blank lines between observation items
    if os.path.exists(OBSERVATIONS_PATH):
        import re
        with open(OBSERVATIONS_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        prev = None
        while prev != content:
            prev = content
            content = re.sub(r'(\n(🔴|🟡|🟢)[^\n]+)\n\n(🔴|🟡|🟢)', r'\1\n\3', content)
        with open(OBSERVATIONS_PATH, "w", encoding="utf-8") as f:
            f.write(content)

if __name__ == "__main__":
    main()
