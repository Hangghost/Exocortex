#!/usr/bin/env python3
"""
Stage 1 Triage: Haiku via Anthropic Batch API + Prompt Cache.
Reads raw_signals/<date>/ where triage is null, submits a batch,
polls until done, and writes triage results back to each JSON file.
"""
import json
import logging
import os
import time
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[5]
RAW_SIGNALS_DIR = REPO_ROOT / "raw_signals"
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"

MODEL = "claude-haiku-4-5-20251001"
POLL_INTERVAL = 10  # seconds between polls
POLL_TIMEOUT = 600  # 10 minutes max wait
PENDING_BATCH_FILE = RAW_SIGNALS_DIR / ".pending_stage1_batch"

VALID_TRIAGE = {"high", "uncertain", "noise"}


def _load_system_prompt() -> str:
    return (PROMPTS_DIR / "stage1_system.md").read_text(encoding="utf-8")


def _load_pending_signals(date_dir: Path) -> list[tuple[Path, dict]]:
    """Return list of (path, signal) where triage is null."""
    results = []
    for f in sorted(date_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("triage") is None:
                results.append((f, data))
        except Exception as e:
            logger.warning("Failed to read signal file %s: %s", f, e)
    return results


def _write_triage(path: Path, triage: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["triage"] = triage
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run(target_date: str, api_key: str | None = None) -> dict:
    """
    Run Stage 1 triage for target_date.
    Returns dict with counts: {processed, high, uncertain, noise, skipped}.
    """
    client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
    date_dir = RAW_SIGNALS_DIR / target_date

    if not date_dir.exists():
        logger.info("Stage 1: no signal directory for %s, skipping", target_date)
        return {"processed": 0, "high": 0, "uncertain": 0, "noise": 0, "skipped": 0}

    # Check for a pending batch from a previous interrupted run
    pending = _check_pending_batch(client, target_date)
    if pending:
        logger.info("Stage 1: found pending batch %s, retrieving results", pending["batch_id"])
        counts = _retrieve_and_apply(client, pending["batch_id"], pending["id_to_path"], date_dir)
        _clear_pending()
        return counts

    pending_signals = _load_pending_signals(date_dir)
    if not pending_signals:
        logger.info("Stage 1: no untriaged signals for %s", target_date)
        return {"processed": 0, "high": 0, "uncertain": 0, "noise": 0, "skipped": 0}

    logger.info("Stage 1: sending batch for %d signals", len(pending_signals))
    system_prompt = _load_system_prompt()

    # Build batch requests
    requests = []
    id_to_path: dict[str, Path] = {}
    for path, signal in pending_signals:
        custom_id = signal["id"]
        id_to_path[custom_id] = path
        requests.append(
            anthropic.types.message_create_params.MessageCreateParamsNonStreaming(
                custom_id=custom_id,
                params={
                    "model": MODEL,
                    "max_tokens": 10,
                    "system": [
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Classify this signal:\n\n{signal['content']}",
                        }
                    ],
                },
            )
        )

    batch = client.messages.batches.create(requests=requests)
    batch_id = batch.id
    logger.info("Stage 1: batch %s submitted (%d requests)", batch_id, len(requests))

    # Save pending state in case we time out
    _save_pending(batch_id, id_to_path, target_date)

    counts = _poll_and_apply(client, batch_id, id_to_path, date_dir)
    _clear_pending()
    return counts


def _poll_and_apply(
    client: anthropic.Anthropic,
    batch_id: str,
    id_to_path: dict[str, Path],
    date_dir: Path,
) -> dict:
    start = time.time()
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        status = batch.processing_status

        if status == "ended":
            logger.info("Stage 1: batch %s complete", batch_id)
            return _retrieve_and_apply(client, batch_id, id_to_path, date_dir)

        elapsed = time.time() - start
        if elapsed > POLL_TIMEOUT:
            logger.warning(
                "Stage 1: batch %s still processing after %.0fs, will retry on next run",
                batch_id, elapsed,
            )
            return {"processed": 0, "high": 0, "uncertain": 0, "noise": 0, "skipped": len(id_to_path)}

        logger.info(
            "Stage 1: batch %s status=%s (%.0fs elapsed), polling again in %ds",
            batch_id, status, elapsed, POLL_INTERVAL,
        )
        time.sleep(POLL_INTERVAL)


def _retrieve_and_apply(
    client: anthropic.Anthropic,
    batch_id: str,
    id_to_path: dict[str, Path],
    date_dir: Path,
) -> dict:
    counts = {"processed": 0, "high": 0, "uncertain": 0, "noise": 0, "skipped": 0}

    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id
        path = id_to_path.get(custom_id)
        if path is None:
            logger.warning("Stage 1: unknown custom_id in batch result: %s", custom_id)
            continue

        if result.result.type == "succeeded":
            raw = result.result.message.content[0].text.strip().lower()
            triage = raw if raw in VALID_TRIAGE else "uncertain"
            if raw not in VALID_TRIAGE:
                logger.warning("Stage 1: unexpected triage value '%s' for %s, defaulting to uncertain", raw, custom_id)
            _write_triage(path, triage)
            counts["processed"] += 1
            counts[triage] += 1
        else:
            logger.warning("Stage 1: request %s failed: %s", custom_id, result.result.type)
            # Default to uncertain on failure (safer than noise)
            _write_triage(path, "uncertain")
            counts["processed"] += 1
            counts["uncertain"] += 1

    logger.info("Stage 1: results — %s", counts)
    return counts


def _pending_path() -> Path:
    return PENDING_BATCH_FILE


def _save_pending(batch_id: str, id_to_path: dict[str, Path], target_date: str) -> None:
    data = {
        "batch_id": batch_id,
        "target_date": target_date,
        "id_to_path": {k: str(v) for k, v in id_to_path.items()},
    }
    _pending_path().parent.mkdir(parents=True, exist_ok=True)
    _pending_path().write_text(json.dumps(data), encoding="utf-8")


def _check_pending_batch(client: anthropic.Anthropic, target_date: str) -> dict | None:
    p = _pending_path()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("target_date") != target_date:
            # Stale pending from a different date
            _clear_pending()
            return None
        batch = client.messages.batches.retrieve(data["batch_id"])
        if batch.processing_status != "ended":
            logger.info("Stage 1: pending batch %s not yet complete (status=%s)",
                        data["batch_id"], batch.processing_status)
            return None
        return {
            "batch_id": data["batch_id"],
            "id_to_path": {k: Path(v) for k, v in data["id_to_path"].items()},
        }
    except Exception as e:
        logger.warning("Stage 1: failed to check pending batch: %s", e)
        _clear_pending()
        return None


def _clear_pending() -> None:
    p = _pending_path()
    if p.exists():
        p.unlink()
