#!/usr/bin/env python3
"""
L0 Capturer: main entry point.
Reads cc_events_bridge as the sole triage source, merges results, and
idempotently writes to raw_signals/<date>/ directory.
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from . import cc_events_bridge

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[5]
RAW_SIGNALS_DIR = REPO_ROOT / "raw_signals"


def run(target_date: str) -> int:
    """
    Run cc_events_bridge for target_date.
    Returns number of new signals written.

    Also exposes per-source stats via `last_run_stats` module attribute so
    capture.py can include it in capture role's last_run_summary.
    """
    date_dir = RAW_SIGNALS_DIR / target_date
    date_dir.mkdir(parents=True, exist_ok=True)

    # Load existing signal IDs for idempotency
    existing_ids = _load_existing_ids(date_dir)

    all_signals: list[dict] = []
    stats: dict[str, dict[str, int]] = {}

    # CC hook events (bridge from inbox/captured/cc_events/) — sole triage source
    try:
        cc_signals = cc_events_bridge.capture(target_date)
        all_signals.extend(cc_signals)
        stats["cc_events"] = {"captured": len(cc_signals), "failed": 0}
    except Exception as e:
        logger.warning("cc_events_bridge failed, continuing: %s", e)
        stats["cc_events"] = {"captured": 0, "failed": 1}

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
    # Stash stats on module so capture.py can pick it up for last_run_summary.
    global last_run_stats
    last_run_stats = stats
    return written


# Per-source stats from the most recent run (consumed by capture.py).
last_run_stats: dict[str, dict[str, int]] = {}


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
