#!/usr/bin/env python3
"""
AI Heartbeat v1 — Capture Pipeline
Steps: capturer → stage1 triage → stage2 judgment → archive noise → gc

Usage:
    python capture.py [YYYY-MM-DD]

Environment variables (via .env):
    ANTHROPIC_API_KEY       — required for Stage 1 & 2
    GOOGLE_CREDENTIALS      — path to Google OAuth credentials.json
    GOOGLE_CAL_TOKEN        — path to Google Calendar token.json (auto-created on first run)
    GOOGLE_GMAIL_TOKEN      — path to Gmail token.json (auto-created on first run)
"""
import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Load .env from repo root
REPO_ROOT = Path(__file__).resolve().parents[5]
_env_file = REPO_ROOT / ".env"
if _env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_file)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("heartbeat_v1_capture")

# Register package path
sys.path.insert(0, str(REPO_ROOT))

from infra.periodic_jobs.ai_heartbeat.src.v1.capturer import main as capturer_main
from infra.periodic_jobs.ai_heartbeat.src.v1.triage import stage1, stage2, archive as archive_mod


def main():
    parser = argparse.ArgumentParser(description="AI Heartbeat v1 — Capture Pipeline")
    parser.add_argument("date", nargs="?", default=datetime.now().strftime("%Y-%m-%d"),
                        help="Target date (YYYY-MM-DD), defaults to today")
    args = parser.parse_args()
    target_date = args.date

    logger.info("=== Capture pipeline starting for %s ===", target_date)

    # ── Env checks ────────────────────────────────────────────────────────
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set — aborting")
        sys.exit(1)

    credentials_path = os.environ.get("GOOGLE_CREDENTIALS", str(REPO_ROOT / "credentials.json"))
    cal_token_path = os.environ.get("GOOGLE_CAL_TOKEN", str(REPO_ROOT / ".google_cal_token.json"))
    gmail_token_path = os.environ.get("GOOGLE_GMAIL_TOKEN", str(REPO_ROOT / ".google_gmail_token.json"))

    # ── Step 1: Capture ───────────────────────────────────────────────────
    logger.info("Step 1: L0 capture")
    try:
        written = capturer_main.run(target_date, credentials_path, cal_token_path, gmail_token_path)
        logger.info("Step 1 done: %d new signals captured", written)
    except Exception as e:
        logger.error("Step 1 failed: %s — aborting pipeline", e)
        sys.exit(1)

    # ── Step 2: Stage 1 Triage (Haiku Batch) ─────────────────────────────
    logger.info("Step 2: Stage 1 triage (Haiku Batch)")
    try:
        s1_counts = stage1.run(target_date, api_key=api_key)
        logger.info("Step 2 done: %s", s1_counts)
    except Exception as e:
        logger.error("Step 2 failed: %s — continuing with remaining signals", e)

    # ── Step 3: Stage 2 Judgment (Sonnet) ────────────────────────────────
    logger.info("Step 3: Stage 2 judgment (Sonnet)")
    try:
        s2_counts = stage2.run(target_date, api_key=api_key)
        logger.info("Step 3 done: %s", s2_counts)
    except Exception as e:
        logger.error("Step 3 failed: %s — continuing", e)

    # ── Step 5: Archive noise signals ─────────────────────────────────────
    logger.info("Step 5: Archive noise signals")
    try:
        moved = archive_mod.archive(target_date)
        logger.info("Step 5 done: %d noise signals archived", moved)
    except Exception as e:
        logger.error("Step 5 failed: %s", e)

    # ── Step 6: GC stale archive entries ──────────────────────────────────
    logger.info("Step 6: GC old archive entries")
    try:
        deleted = archive_mod.gc()
        logger.info("Step 6 done: %d archive dirs deleted", deleted)
    except Exception as e:
        logger.error("Step 6 failed: %s", e)

    logger.info("=== Capture pipeline complete for %s ===", target_date)


if __name__ == "__main__":
    main()
