#!/usr/bin/env python3
"""
L2 Reflector Agent (Trigger Script)
Instructs OpenCode-Builder to perform memory garbage collection directly on the file.
"""
import os
import sys
from opencode_client import OpenCodeClient
from datetime import datetime

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
KNOWLEDGE_BASE = os.path.join(REPO_ROOT, "infra", "periodic_jobs", "ai_heartbeat", "docs", "KNOWLEDGE_BASE.md")

PROMPT_TEMPLATE = """
執行記憶系統的"反思與晉升"任務。

【根目錄】：{repo_root}
【SOP】：{kb_path}
【觀測檔案】：{observations_path}
【規則目錄】：{rules_dir}

步驟：
1. 讀取 {observations_path}，分析 🔴 和高優 🟡 條目
2. 將具有普適性的內容晉升到 {rules_dir}，按職責邊界分類：
   - {rules_dir}/SOUL.md: Agent 身份認同、核心價值觀、邊界原則（不含觸發式操作規則）
   - {rules_dir}/USER.md: 使用者畫像與人生哲學
   - {rules_dir}/ENVIRONMENT.md: 設備、帳號架構、工具與連線等環境事實（merge 更新，非 append）
   - {rules_dir}/COMMUNICATION.md: 溝通風格（僅限溝通，不含技術知識）
   - {rules_dir}/WORKSPACE.md: 目錄路由
   - {rules_dir}/skills/: 技術方法論、工作流、最佳實踐（可執行 SOP）
   - {rules_dir}/axioms/: 觸發式約束與決策原則——「當 X 情況出現時，做/不做 Y」。讀 {rules_dir}/axioms/INDEX.md 了解分類與命名慣例，每條公理建立獨立檔案（{rules_dir}/axioms/<id>_<name>.md）並更新 INDEX.md
3. GC：重寫 {observations_path}，刪除已晉升及過期 🟢 記錄
4. 個人事實 promote：識別 {observations_path} 中所有標籤以 `[PersonalFacts` 或 `[個人事實` 開頭的條目，將其內容以 merge 方式更新 {rules_dir}/ENVIRONMENT.md 對應類別區塊（同類別舊事實被新事實覆蓋），完成後將已處理的條目納入 GC

晉升門檻：跨專案通用 + 多次驗證 + 有明確適用場景
完成後回覆簡短晉升彙報。
"""

def main():
    import argparse
    parser = argparse.ArgumentParser(description='L2 Reflector Agent')
    parser.add_argument('--model', default='anthropic/claude-sonnet-4-6',
                        help='Model ID to use (e.g. anthropic/claude-sonnet-4-6, gemini-2.5-flash)')
    args = parser.parse_args()
    
    model_id = args.model
    target_date = datetime.now().strftime("%Y-%m-%d")

    print(f"Triggering Fully Agentic Reflector using model: {model_id}...")
    client = OpenCodeClient()
    
    session_id = client.create_session(f"Heartbeat L2 Reflector - {target_date}")
    if not session_id:
        return
        
    observations_path = os.path.join(REPO_ROOT, "memory", "OBSERVATIONS.md")
    rules_dir = os.path.join(REPO_ROOT, "rules")
    prompt = PROMPT_TEMPLATE.format(
        kb_path=KNOWLEDGE_BASE,
        repo_root=REPO_ROOT,
        observations_path=observations_path,
        rules_dir=rules_dir,
    )
    client.send_message(session_id, prompt, model_id=model_id)
    # If send_message timed out, agent may still be running; poll until done
    print("Waiting for session to complete (sync mode)...")
    client.wait_for_session_complete(session_id)
    print(f"Task complete (Session: {session_id}).")

if __name__ == "__main__":
    main()
