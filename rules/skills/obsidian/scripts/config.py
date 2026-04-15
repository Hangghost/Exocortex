"""
Config loader for the obsidian skill.
Reads ~/.config/obsidian/config.json; prompts interactively on first run.
"""

import json
import os
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "obsidian" / "config.json"

DEFAULT_CONFIG = {
    "vault_path": "",
    "rest_api": {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 27123,
        "api_key": "",
    },
}


def _prompt(question: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        answer = input(f"{question}{suffix}: ").strip()
    except EOFError:
        answer = ""
    return answer if answer else default


def _save(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


def load_config() -> dict:
    """Load config; prompt for any missing required fields and persist."""
    config = {}

    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                config = json.load(f)
        except json.JSONDecodeError:
            print(f"[obsidian] Warning: {CONFIG_PATH} is invalid JSON, re-prompting.", file=sys.stderr)
            config = {}

    # Ensure top-level structure
    config.setdefault("vault_path", DEFAULT_CONFIG["vault_path"])
    config.setdefault("rest_api", {})
    for k, v in DEFAULT_CONFIG["rest_api"].items():
        config["rest_api"].setdefault(k, v)

    changed = False

    # Validate vault_path
    vault_path = config.get("vault_path", "")
    if not vault_path or not Path(vault_path).expanduser().exists():
        if vault_path:
            print(f"[obsidian] vault_path '{vault_path}' does not exist.", file=sys.stderr)
        vault_path = _prompt("Obsidian vault path (absolute path to your vault folder)")
        if not vault_path:
            print("[obsidian] Error: vault_path is required.", file=sys.stderr)
            sys.exit(1)
        config["vault_path"] = str(Path(vault_path).expanduser())
        changed = True

    config["vault_path"] = str(Path(config["vault_path"]).expanduser())

    # Optionally prompt for REST API settings if api_key is empty and not already disabled
    if not config["rest_api"].get("api_key") and config["rest_api"].get("enabled", True):
        print("[obsidian] REST API key not configured (leave blank to use filesystem-only mode).")
        api_key = _prompt("obsidian-local-rest-api key", default="")
        if api_key:
            config["rest_api"]["api_key"] = api_key
            port_str = _prompt("REST API port", default=str(config["rest_api"]["port"]))
            try:
                config["rest_api"]["port"] = int(port_str)
            except ValueError:
                pass
        else:
            config["rest_api"]["enabled"] = False
        changed = True

    if changed:
        _save(config)
        print(f"[obsidian] Config saved to {CONFIG_PATH}", file=sys.stderr)

    return config
