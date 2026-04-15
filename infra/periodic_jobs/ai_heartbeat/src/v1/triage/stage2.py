#!/usr/bin/env python3
"""
Stage 2 Triage: Sonnet via Anthropic Raw API + Prompt Cache.
Reads signals where triage == "uncertain", calls Sonnet once per signal,
and updates triage to "high" or "noise".
"""
import json
import logging
import os
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[5]
RAW_SIGNALS_DIR = REPO_ROOT / "raw_signals"
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"

MODEL = "claude-sonnet-4-6"
VALID_TRIAGE = {"high", "noise"}


def _load_system_prompt() -> str:
    return (PROMPTS_DIR / "stage2_system.md").read_text(encoding="utf-8")


def _load_uncertain_signals(date_dir: Path) -> list[tuple[Path, dict]]:
    results = []
    for f in sorted(date_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("triage") == "uncertain":
                results.append((f, data))
        except Exception as e:
            logger.warning("Stage 2: failed to read %s: %s", f, e)
    return results


def _write_triage(path: Path, triage: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["triage"] = triage
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run(target_date: str, api_key: str | None = None) -> dict:
    """
    Run Stage 2 judgment for target_date.
    Returns dict with counts: {processed, high, noise, skipped}.
    """
    client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
    date_dir = RAW_SIGNALS_DIR / target_date

    if not date_dir.exists():
        logger.info("Stage 2: no signal directory for %s, skipping", target_date)
        return {"processed": 0, "high": 0, "noise": 0, "skipped": 0}

    uncertain_signals = _load_uncertain_signals(date_dir)
    if not uncertain_signals:
        logger.info("Stage 2: no uncertain signals for %s", target_date)
        return {"processed": 0, "high": 0, "noise": 0, "skipped": 0}

    logger.info("Stage 2: judging %d uncertain signals", len(uncertain_signals))
    system_prompt = _load_system_prompt()
    counts = {"processed": 0, "high": 0, "noise": 0, "skipped": 0}

    for path, signal in uncertain_signals:
        try:
            triage = _judge_signal(client, system_prompt, signal)
            _write_triage(path, triage)
            counts["processed"] += 1
            counts[triage] += 1
            logger.debug("Stage 2: %s → %s", signal["id"], triage)
        except Exception as e:
            logger.warning("Stage 2: failed to judge signal %s: %s — defaulting to high", signal["id"], e)
            _write_triage(path, "high")
            counts["processed"] += 1
            counts["high"] += 1

    logger.info("Stage 2: results — %s", counts)
    return counts


def _judge_signal(client: anthropic.Anthropic, system_prompt: str, signal: dict) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=10,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"Make the final call for this signal:\n\n{signal['content']}",
            }
        ],
    )
    raw = response.content[0].text.strip().lower()
    if raw not in VALID_TRIAGE:
        logger.warning("Stage 2: unexpected response '%s', defaulting to high", raw)
        return "high"
    return raw
