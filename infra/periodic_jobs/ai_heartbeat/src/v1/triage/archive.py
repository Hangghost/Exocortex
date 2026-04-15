#!/usr/bin/env python3
"""
Noise Archive + GC.
- archive(): moves triage="noise" signals into raw_signals/archive/<date>/
- gc(): deletes archive subdirectories older than 30 days
"""
import json
import logging
import shutil
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[5]
RAW_SIGNALS_DIR = REPO_ROOT / "raw_signals"
ARCHIVE_DIR = RAW_SIGNALS_DIR / "archive"
GC_RETENTION_DAYS = 30


def archive(target_date: str) -> int:
    """
    Move all triage="noise" signals for target_date into archive/<date>/.
    Returns number of files moved.
    """
    date_dir = RAW_SIGNALS_DIR / target_date
    if not date_dir.exists():
        return 0

    archive_date_dir = ARCHIVE_DIR / target_date
    moved = 0

    for f in sorted(date_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("triage") == "noise":
                archive_date_dir.mkdir(parents=True, exist_ok=True)
                dest = archive_date_dir / f.name
                shutil.move(str(f), str(dest))
                moved += 1
                logger.debug("Archived noise signal: %s → %s", f.name, dest)
        except Exception as e:
            logger.warning("Archive: failed to process %s: %s", f, e)

    if moved:
        logger.info("Archive: moved %d noise signals for %s", moved, target_date)
    return moved


def gc() -> int:
    """
    Delete archive subdirectories older than GC_RETENTION_DAYS.
    Returns number of directories deleted.
    """
    if not ARCHIVE_DIR.exists():
        return 0

    cutoff = date.today() - timedelta(days=GC_RETENTION_DAYS)
    deleted = 0

    for subdir in sorted(ARCHIVE_DIR.iterdir()):
        if not subdir.is_dir():
            continue
        try:
            dir_date = date.fromisoformat(subdir.name)
            if dir_date < cutoff:
                shutil.rmtree(subdir)
                deleted += 1
                logger.info("GC: deleted archive/%s (older than %d days)", subdir.name, GC_RETENTION_DAYS)
        except ValueError:
            # Non-date directory name, skip
            pass
        except Exception as e:
            logger.warning("GC: failed to delete %s: %s", subdir, e)

    if deleted:
        logger.info("GC: removed %d archive directories", deleted)
    return deleted
