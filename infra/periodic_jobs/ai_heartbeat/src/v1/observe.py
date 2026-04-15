#!/usr/bin/env python3
"""
AI Heartbeat v1 — Observer
Based on v0/observer.py (OpenCode Client). Additionally reads triage="high"
signals from raw_signals/<date>/ and appends them to the observer prompt.

Usage:
    python observe.py [YYYY-MM-DD] [--model MODEL_ID]

Environment variables (via .env):
    OPENCODE_API_URL   — OpenCode Server endpoint
"""
import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Load .env from repo root
REPO_ROOT = Path(__file__).resolve().parents[5]
_env_file = REPO_ROOT / ".env"
if _env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_file)

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "infra/periodic_jobs/ai_heartbeat/src/v0"))

from opencode_client import OpenCodeClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("heartbeat_v1_observe")

KNOWLEDGE_BASE = REPO_ROOT / "infra" / "periodic_jobs" / "ai_heartbeat" / "docs" / "KNOWLEDGE_BASE.md"
OBSERVATIONS_PATH = REPO_ROOT / "memory" / "OBSERVATIONS.md"
RAW_SIGNALS_DIR = REPO_ROOT / "raw_signals"

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
{high_signals_section}"""

HIGH_SIGNALS_SECTION = """
【L0 高相關信號（已通過 Haiku + Sonnet 兩輪篩選，triage="high"）】：
請將以下信號納入觀察範疇，結合 contexts/ 脈絡判斷實際意義：
{signal_list}
"""


def _load_high_signals(target_date: str) -> list[dict]:
    date_dir = RAW_SIGNALS_DIR / target_date
    if not date_dir.exists():
        return []
    signals = []
    for f in sorted(date_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("triage") == "high":
                signals.append(data)
        except Exception as e:
            logger.warning("Failed to read signal %s: %s", f, e)
    return signals


def _already_observed(target_date: str) -> bool:
    if not OBSERVATIONS_PATH.exists():
        return False
    content = OBSERVATIONS_PATH.read_text(encoding="utf-8")
    return f"Date: {target_date}" in content


def _collapse_blank_lines(path: Path) -> None:
    if not path.exists():
        return
    content = path.read_text(encoding="utf-8")
    prev = None
    while prev != content:
        prev = content
        content = re.sub(r'(\n(🔴|🟡|🟢)[^\n]+)\n\n(🔴|🟡|🟢)', r'\1\n\3', content)
    path.write_text(content, encoding="utf-8")


def main():
    os.environ.setdefault("OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX", "16000")

    parser = argparse.ArgumentParser(description="AI Heartbeat v1 — Observer")
    parser.add_argument("date", nargs="?", default=datetime.now().strftime("%Y-%m-%d"),
                        help="Target date (YYYY-MM-DD), defaults to today")
    parser.add_argument("--model", default="anthropic/claude-haiku-4-5-20251001",
                        help="Model ID to use (e.g. anthropic/claude-haiku-4-5-20251001, anthropic/claude-opus-4-6)")
    parser.add_argument("--no-delete", action="store_true",
                        help="Keep session after completion (default: delete)")
    args = parser.parse_args()

    target_date = args.date
    model_id = args.model
    delete_after = not args.no_delete

    # Idempotency check
    if _already_observed(target_date):
        print(f"Idempotent skip: entry for {target_date} already exists in OBSERVATIONS.md")
        return

    # Load high-priority signals (gracefully empty if not available)
    high_signals = _load_high_signals(target_date)
    if high_signals:
        signal_list = "\n".join(f"- {s.get('content', json.dumps(s))}" for s in high_signals)
        high_signals_section = HIGH_SIGNALS_SECTION.format(signal_list=signal_list)
        logger.info("Loaded %d high-priority signals for %s", len(high_signals), target_date)
    else:
        high_signals_section = ""
        logger.info("No high-priority signals found for %s — proceeding without", target_date)

    prompt = PROMPT_TEMPLATE.format(
        kb_path=str(KNOWLEDGE_BASE),
        target_date=target_date,
        repo_root=str(REPO_ROOT),
        observations_path=str(OBSERVATIONS_PATH),
        high_signals_section=high_signals_section,
    )

    print(f"Triggering Observer for date: {target_date} using model: {model_id}...")
    client = OpenCodeClient()

    session_id = client.create_session(f"Heartbeat v1 Observer - {target_date}")
    if not session_id:
        sys.exit(1)

    client.send_message(session_id, prompt, model_id=model_id)
    print("Waiting for session to complete (sync mode)...")
    client.wait_for_session_complete(session_id)

    if delete_after:
        if client.delete_session(session_id):
            print(f"Task complete (session {session_id} deleted).")
        else:
            print(f"Task complete (Session: {session_id}).")
    else:
        print(f"Task complete (Session: {session_id}).")

    _collapse_blank_lines(OBSERVATIONS_PATH)


if __name__ == "__main__":
    main()
