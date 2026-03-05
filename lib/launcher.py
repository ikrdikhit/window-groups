"""
lib/launcher.py — App launching with cross-compositor workspace support.
"""

from __future__ import annotations

import subprocess
import time
from datetime import datetime

from . import compositor as comp
from . import config
from . import ui


def launch_app(command: str,
               workspace: int | None = None,
               pre_command: str = ""):
    """
    Launch a single app, optionally on a specific workspace.
    pre_command is run first (synchronously) if provided.
    """
    info = comp.get()

    if pre_command:
        try:
            subprocess.run(pre_command, shell=True, check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    if workspace is not None:
        comp.switch_workspace(workspace, info)
        time.sleep(0.15)   # tiny pause so the WM registers the switch

    subprocess.Popen(
        command,
        shell=True,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def launch_group(group_name: str,
                 groups: dict | None = None,
                 silent: bool = False) -> bool:
    """
    Launch all apps in a named group.
    Returns True on success, False if group not found.
    """
    if groups is None:
        groups = config.load_groups()

    if group_name not in groups:
        if not silent:
            ui.notify(f'Group "{group_name}" not found', urgency="critical",
                      icon="dialog-error")
        return False

    group = groups[group_name]
    apps  = group.get("apps", [])
    if not apps:
        ui.notify(f'Group "{group_name}" has no apps configured.',
                  urgency="normal")
        return True

    if not silent:
        ui.notify(
            f'Launching "{group_name}"',
            f"{len(apps)} app(s) starting…",
            icon="system-run",
        )

    for app in apps:
        cmd       = app.get("command", "").strip()
        delay     = float(app.get("delay", 0))
        workspace = app.get("workspace")
        pre_cmd   = app.get("pre_command", "").strip()

        if not cmd:
            continue

        if delay > 0:
            time.sleep(delay)

        launch_app(cmd, workspace=workspace, pre_command=pre_cmd)

    _record_launch(group_name, [a.get("command", "") for a in apps])
    return True


def _record_launch(group_name: str, commands: list[str]):
    history = config.load_history()

    history.setdefault("launches", []).append({
        "group":    group_name,
        "commands": commands,
        "time":     datetime.now().isoformat(),
    })
    # Keep a rolling 1000-entry window
    history["launches"] = history["launches"][-1000:]

    co = history.setdefault("cooccurrence", {})
    clean = [c for c in commands if c]
    for i, a in enumerate(clean):
        for b in clean[i + 1:]:
            key = "|||".join(sorted([a, b]))
            co[key] = co.get(key, 0) + 1

    config.save_history(history)
