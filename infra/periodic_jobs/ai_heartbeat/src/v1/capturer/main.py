#!/usr/bin/env python3
"""
L0 Capturer: main entry point.
Calls calendar + email capturers, merges results, and idempotently writes
to raw_signals/<date>/ directory.
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from . import calendar as cal_capturer
from . import email as email_capturer

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[5]
RAW_SIGNALS_DIR = REPO_ROOT / "raw_signals"


def run(target_date: str, credentials_path: str, cal_token_path: str, gmail_token_path: str) -> int:
    """
    Run all capturers for target_date.
    Returns number of new signals written.
    """
    date_dir = RAW_SIGNALS_DIR / target_date
    date_dir.mkdir(parents=True, exist_ok=True)

    # Load existing signal IDs for idempotency
    existing_ids = _load_existing_ids(date_dir)

    all_signals: list[dict] = []

    # Calendar
    try:
        cal_signals = cal_capturer.capture(target_date, credentials_path, cal_token_path)
        all_signals.extend(cal_signals)
    except Exception as e:
        logger.warning("Calendar capturer failed, continuing: %s", e)

    # Email
    try:
        email_signals = email_capturer.capture(target_date, credentials_path, gmail_token_path)
        all_signals.extend(email_signals)
    except Exception as e:
        logger.warning("Email capturer failed, continuing: %s", e)

    # Write new signals (skip duplicates by id)
    written = 0
    for signal in all_signals:
        if not _validate_signal(signal):
            logger.error("Signal validation failed, skipping: %s", signal)
            continue
        if signal["id"] in existing_ids:
            logger.debug("Signal %s already exists, skipping (idempotent)", signal["id"])
            continue
        _write_signal(date_dir, signal)
        written += 1

    logger.info("Capturer: wrote %d new signals for %s (total existing: %d)",
                written, target_date, len(existing_ids))
    return written


def _load_existing_ids(date_dir: Path) -> set[str]:
    ids = set()
    for f in date_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if "id" in data:
                ids.add(data["id"])
        except Exception:
            pass
    return ids


def _validate_signal(signal: dict) -> bool:
    required = {"id", "source", "captured_at", "content", "triage"}
    return required.issubset(signal.keys())


def _write_signal(date_dir: Path, signal: dict) -> None:
    source = signal["source"]
    sig_id = signal["id"]
    filename = f"{source}_{sig_id}.json"
    path = date_dir / filename
    path.write_text(json.dumps(signal, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.debug("Written signal: %s", path)
