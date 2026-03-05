"""
lib/config.py — Paths, defaults, and JSON helpers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ─── Paths ────────────────────────────────────────────────────────────────────

CONFIG_DIR   = Path.home() / ".config"  / "window-groups"
GROUPS_FILE  = CONFIG_DIR / "groups.json"
HISTORY_FILE = CONFIG_DIR / "history.json"
SESSION_FILE = CONFIG_DIR / "session.json"
LOG_FILE     = CONFIG_DIR / "window-groups.log"

CONFIG_DIR.mkdir(parents=True, exist_ok=True)


# ─── Default groups ───────────────────────────────────────────────────────────

DEFAULT_GROUPS: dict = {
    "Work": {
        "description": "Development workspace",
        "color": "#4A90D9",
        "apps": [
            {"name": "Terminal",  "command": "kitty",    "delay": 0},
            {"name": "Browser",   "command": "firefox",  "delay": 0.8},
            {"name": "Editor",    "command": "code",     "delay": 1.2},
        ],
    },
    "Study": {
        "description": "Study / research session",
        "color": "#27AE60",
        "apps": [
            {"name": "Browser",   "command": "firefox",   "delay": 0},
            {"name": "Notes",     "command": "obsidian",  "delay": 1.0},
            {"name": "Terminal",  "command": "kitty",     "delay": 1.5},
        ],
    },
    "Media": {
        "description": "Music and streaming",
        "color": "#8E44AD",
        "apps": [
            {"name": "Music",     "command": "spotify",  "delay": 0},
            {"name": "Discord",   "command": "discord",  "delay": 2.0},
        ],
    },
    "Communication": {
        "description": "Chat and email",
        "color": "#E67E22",
        "apps": [
            {"name": "Email",     "command": "thunderbird", "delay": 0},
            {"name": "Telegram",  "command": "telegram-desktop", "delay": 1.0},
        ],
    },
}


# ─── JSON helpers ─────────────────────────────────────────────────────────────

def load_json(path: Path, default: Any) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return default


def save_json(path: Path, data: Any):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8")


def load_groups() -> dict:
    groups = load_json(GROUPS_FILE, None)
    if groups is None:
        save_json(GROUPS_FILE, DEFAULT_GROUPS)
        return DEFAULT_GROUPS
    return groups


def save_groups(groups: dict):
    save_json(GROUPS_FILE, groups)


def load_history() -> dict:
    return load_json(HISTORY_FILE, {"launches": [], "cooccurrence": {}})


def save_history(history: dict):
    save_json(HISTORY_FILE, history)


def load_session() -> dict | None:
    return load_json(SESSION_FILE, None)


def save_session_data(session: dict):
    save_json(SESSION_FILE, session)
