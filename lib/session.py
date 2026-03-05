"""
lib/session.py — Session save and restore.
Uses compositor-specific APIs where possible, falls back to /proc introspection.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from . import compositor as comp
from . import config
from . import launcher
from . import ui


def save_session():
    """Capture all currently open windows and save to session file."""
    info    = comp.get()
    windows = comp.list_windows(info)

    if not windows:
        ui.notify("Session Save",
                  "No windows found. Is wmctrl/hyprctl/swaymsg installed?",
                  urgency="normal", icon="dialog-warning")
        return False

    session = {
        "saved_at": datetime.now().isoformat(),
        "wm":       info.wm_name,
        "windows":  windows,
    }
    config.save_session_data(session)
    ui.notify(
        "Session Saved",
        f"{len(windows)} window(s) captured  ·  {info.wm_name}",
        icon="document-save",
    )
    print(f"Session saved: {len(windows)} app(s) → {config.SESSION_FILE}")
    return True


def restore_session():
    """Interactive session restore menu."""
    session = config.load_session()
    if not session:
        ui.notify("Session Restore", "No saved session found.",
                  urgency="normal", icon="dialog-warning")
        return

    windows  = session.get("windows", [])
    saved_at = session.get("saved_at", "unknown")[:16].replace("T", " ")
    wm_saved = session.get("wm", "unknown")

    if not windows:
        ui.notify("Session Restore", "Saved session is empty.")
        return

    msg = f"Saved  {saved_at}  on  {wm_saved}"
    header = [
        f"▶  Restore ALL  ({len(windows)} apps)",
        "✦  Save as new group…",
        "─────────────────────",
    ]
    app_lines = [
        f"  {w['command']}  (workspace {w['workspace']})  — {w['title'][:48]}"
        for w in windows
    ]
    sel = ui.prompt("Restore Session", header + app_lines, message=msg)
    if not sel:
        return

    if sel.startswith("▶"):
        _do_restore(windows)
    elif sel.startswith("✦"):
        _save_as_group(windows)
    else:
        # Single app — match by index in app_lines
        try:
            idx = (header + app_lines).index(sel) - len(header)
            if 0 <= idx < len(windows):
                _do_restore([windows[idx]])
        except ValueError:
            pass


def _do_restore(windows: list[dict]):
    ui.notify("Session Restore", f"Restoring {len(windows)} app(s)…",
              icon="system-run")
    info = comp.get()
    for w in windows:
        ws = w.get("workspace", 1)
        if ws and ws > 0:
            comp.switch_workspace(ws, info)
            time.sleep(0.1)
        launcher.launch_app(w["command"])
        time.sleep(0.4)


def _save_as_group(windows: list[dict]):
    name = ui.text_input("New group name", "My Session")
    if not name:
        return
    groups = config.load_groups()
    if name in groups:
        overwrite = ui.prompt(
            f'"{name}" exists', ["Overwrite", "Pick a different name"]
        )
        if not overwrite or "different" in overwrite:
            new = ui.text_input("New group name")
            if not new:
                return
            name = new

    groups[name] = {
        "description": f"Restored from session {datetime.now().strftime('%Y-%m-%d')}",
        "color":       "#E67E22",
        "apps": [
            {
                "name":      w["command"],
                "command":   w["command"],
                "delay":     round(i * 0.5, 1),
                "workspace": w.get("workspace", 1),
            }
            for i, w in enumerate(windows)
        ],
    }
    config.save_groups(groups)
    ui.notify("Group Created",
              f'"{name}" saved with {len(windows)} app(s).',
              icon="list-add")
