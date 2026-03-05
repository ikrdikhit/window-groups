"""
lib/groups.py — Full CRUD for group and app management via rofi menus.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path

from . import config
from . import ui


# ─── Top-level manage menu ────────────────────────────────────────────────────

def manage_menu():
    while True:
        groups = config.load_groups()
        names  = sorted(groups.keys())

        header = [
            "➕  Add new group",
            "📋  Duplicate a group",
            "🗑️   Delete a group",
            "📤  Export groups",
            "📥  Import groups",
            "─────────────────────",
        ]
        group_items = [
            f"✏️   {n}   —   {groups[n].get('description', '')}"
            f"   ({len(groups[n].get('apps', []))} apps)"
            for n in names
        ]
        sel = ui.prompt("Manage Groups", header + group_items,
                        message="Select a group to edit, or choose an action")
        if not sel:
            return

        if sel.startswith("➕"):
            _add_group(groups)
        elif sel.startswith("📋"):
            _duplicate_group(groups, names)
        elif sel.startswith("🗑️"):
            _delete_group(groups, names)
        elif sel.startswith("📤"):
            _export_groups(groups)
        elif sel.startswith("📥"):
            _import_groups()
        elif sel.startswith("✏️"):
            group_name = sel.split("✏️")[1].split("—")[0].strip()
            if group_name in groups:
                _edit_group(groups, group_name)


# ─── Add / duplicate / delete ─────────────────────────────────────────────────

def _add_group(groups: dict):
    name = ui.text_input("Group name")
    if not name:
        return
    if name in groups:
        ui.notify("Already exists", f'A group named "{name}" already exists.',
                  icon="dialog-warning")
        return

    desc  = ui.text_input("Short description (optional)") or ""
    color = ui.text_input("Accent color hex (e.g. #4A90D9)") or "#4A90D9"

    groups[name] = {"description": desc, "color": color, "apps": []}
    config.save_groups(groups)
    ui.notify("Group Created", f'"{name}" created. Add apps to it now.')
    _edit_group(groups, name)


def _duplicate_group(groups: dict, names: list):
    sel = ui.prompt("Duplicate which group?", names)
    if not sel or sel not in groups:
        return
    new_name = ui.text_input("New group name", f"{sel} copy")
    if not new_name:
        return
    if new_name in groups:
        ui.notify("Already exists", f'"{new_name}" already exists.',
                  icon="dialog-warning")
        return
    groups[new_name] = copy.deepcopy(groups[sel])
    groups[new_name]["description"] += " (copy)"
    config.save_groups(groups)
    ui.notify("Duplicated", f'"{sel}" → "{new_name}"')


def _delete_group(groups: dict, names: list):
    sel = ui.prompt("Delete which group?", names,
                    message="⚠  This cannot be undone")
    if not sel or sel not in groups:
        return
    confirm = ui.prompt(f'Really delete "{sel}"?',
                        ["Yes, delete it", "No, cancel"])
    if confirm and confirm.startswith("Yes"):
        del groups[sel]
        config.save_groups(groups)
        ui.notify("Deleted", f'"{sel}" removed.')


# ─── Edit a group ─────────────────────────────────────────────────────────────

def _edit_group(groups: dict, name: str):
    while True:
        groups = config.load_groups()   # reload on each loop in case name changed
        if name not in groups:
            return
        group = groups[name]
        apps  = group.get("apps", [])

        meta = [
            f"📝  Rename  (current: {name})",
            f"💬  Description: {group.get('description', '')}",
            f"🎨  Color: {group.get('color', '#4A90D9')}",
            "─────────────────────",
            "➕  Add app",
            "🔃  Reorder apps",
            "─────────────────────",
        ]
        app_lines = [
            f"  [{i+1}]  {a.get('name', a.get('command','?'))}"
            f"   cmd: {a.get('command','')}"
            f"   delay: {a.get('delay',0)}s"
            + (f"   ws:{a['workspace']}" if a.get('workspace') else "")
            for i, a in enumerate(apps)
        ]
        choices = meta + app_lines + ["◀  Back"]

        sel = ui.prompt(f"Edit: {name}", choices)
        if not sel or sel.startswith("◀"):
            return

        if "Rename" in sel:
            _rename_group(groups, name)
            return  # parent loop will pick up new name via manage_menu reload

        elif "Description:" in sel:
            v = ui.text_input("Description", group.get("description", ""))
            if v is not None:
                groups[name]["description"] = v
                config.save_groups(groups)

        elif "Color:" in sel:
            v = ui.text_input("Accent color (hex)", group.get("color", "#4A90D9"))
            if v:
                groups[name]["color"] = v
                config.save_groups(groups)

        elif "Add app" in sel:
            _add_app(groups, name)

        elif "Reorder apps" in sel:
            _reorder_apps(groups, name)

        elif sel.strip().startswith("["):
            m = re.match(r"\s*\[(\d+)\]", sel)
            if m:
                idx = int(m.group(1)) - 1
                _edit_app(groups, name, idx)


def _rename_group(groups: dict, old_name: str):
    new_name = ui.text_input("New group name", old_name)
    if not new_name or new_name == old_name:
        return
    if new_name in groups:
        ui.notify("Already exists", f'"{new_name}" already exists.',
                  icon="dialog-warning")
        return
    groups[new_name] = groups.pop(old_name)
    config.save_groups(groups)
    ui.notify("Renamed", f'"{old_name}" → "{new_name}"')


# ─── App CRUD ─────────────────────────────────────────────────────────────────

def _add_app(groups: dict, group_name: str):
    cmd = ui.text_input("Command to launch  (e.g. firefox, code, kitty)")
    if not cmd:
        return

    default_name = Path(cmd.split()[0]).name
    label   = ui.text_input("Display name", default_name) or default_name
    delay   = ui.text_input("Launch delay in seconds", "0") or "0"
    ws_raw  = ui.text_input("Workspace number  (blank = current workspace)", "")
    pre_cmd = ui.text_input("Pre-launch command  (blank to skip)", "")

    try:
        delay_f = float(delay)
    except ValueError:
        delay_f = 0.0

    app: dict = {"name": label, "command": cmd, "delay": delay_f}
    if ws_raw and ws_raw.isdigit():
        app["workspace"] = int(ws_raw)
    if pre_cmd:
        app["pre_command"] = pre_cmd

    groups[group_name]["apps"].append(app)
    config.save_groups(groups)
    ui.notify("App Added", f'"{label}" added to "{group_name}".')


def _edit_app(groups: dict, group_name: str, idx: int):
    apps = groups[group_name]["apps"]
    if idx < 0 or idx >= len(apps):
        return
    app = apps[idx]

    while True:
        choices = [
            f"✏️  Command:     {app.get('command','')}",
            f"🏷️  Name:        {app.get('name','')}",
            f"⏱️  Delay:       {app.get('delay', 0)}s",
            f"🖥️  Workspace:   {app.get('workspace', '(current)')}",
            f"⚙️  Pre-command: {app.get('pre_command', '(none)')}",
            "─────────────────────",
            "🗑️  Remove this app",
            "◀  Back",
        ]
        sel = ui.prompt(f"Edit App [{idx+1}]: {app.get('name','')}", choices)
        if not sel or sel.startswith("◀"):
            config.save_groups(groups)
            return

        if "Command:" in sel:
            v = ui.text_input("Command", app.get("command", ""))
            if v: app["command"] = v

        elif "Name:" in sel:
            v = ui.text_input("Display name", app.get("name", ""))
            if v is not None: app["name"] = v

        elif "Delay:" in sel:
            v = ui.text_input("Delay (seconds)", str(app.get("delay", 0)))
            try: app["delay"] = float(v or 0)
            except ValueError: pass

        elif "Workspace:" in sel:
            v = ui.text_input("Workspace number  (blank = current)")
            if v and v.isdigit():
                app["workspace"] = int(v)
            elif v == "":
                app.pop("workspace", None)

        elif "Pre-command:" in sel:
            v = ui.text_input("Pre-launch command  (blank to remove)")
            if v:
                app["pre_command"] = v
            elif v == "":
                app.pop("pre_command", None)

        elif "Remove" in sel:
            confirm = ui.prompt("Remove this app?",
                                ["Yes, remove it", "No, cancel"])
            if confirm and confirm.startswith("Yes"):
                apps.pop(idx)
                config.save_groups(groups)
                return


def _reorder_apps(groups: dict, group_name: str):
    apps = groups[group_name]["apps"]
    if len(apps) < 2:
        ui.notify("Reorder", "Need at least 2 apps to reorder.")
        return

    while True:
        labels = [
            f"[{i+1}] {a.get('name', a.get('command','?'))}" for i, a in enumerate(apps)
        ]
        labels += ["✅  Done reordering"]
        sel = ui.prompt("Reorder — pick app to move", labels,
                        message="Select an app, then select its new position")
        if not sel or sel.startswith("✅"):
            config.save_groups(groups)
            return

        m = re.match(r"\[(\d+)\]", sel)
        if not m:
            continue
        from_idx = int(m.group(1)) - 1

        pos_labels = [
            f"Position {i+1}" for i in range(len(apps)) if i != from_idx
        ]
        pos_sel = ui.prompt(f"Move to position…", pos_labels)
        if not pos_sel:
            continue
        to_idx = int(pos_sel.split()[1]) - 1

        # Reinsert
        item = apps.pop(from_idx)
        if to_idx > from_idx:
            to_idx -= 1
        apps.insert(to_idx, item)


# ─── Export / Import ──────────────────────────────────────────────────────────

def _export_groups(groups: dict):
    import json
    from datetime import datetime
    dest = Path.home() / f"window-groups-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    dest.write_text(json.dumps(groups, indent=2))
    ui.notify("Exported", f"Saved to {dest}")
    print(f"Groups exported to: {dest}")


def _import_groups():
    import json
    path_str = ui.text_input("Path to JSON file to import")
    if not path_str:
        return
    path = Path(path_str).expanduser()
    if not path.exists():
        ui.notify("Import Failed", f"File not found: {path}", icon="dialog-error")
        return
    try:
        imported = json.loads(path.read_text())
    except Exception as e:
        ui.notify("Import Failed", str(e), icon="dialog-error")
        return

    groups = config.load_groups()
    conflicts = [k for k in imported if k in groups]
    if conflicts:
        sel = ui.prompt(
            f"{len(conflicts)} conflict(s)",
            ["Overwrite existing", "Skip conflicts", "Cancel"],
            message="Some imported groups already exist.",
        )
        if not sel or sel == "Cancel":
            return
        if sel.startswith("Skip"):
            imported = {k: v for k, v in imported.items() if k not in groups}

    groups.update(imported)
    config.save_groups(groups)
    ui.notify("Imported", f"{len(imported)} group(s) imported from {path.name}")
