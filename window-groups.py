#!/usr/bin/env python3
"""
window-groups — Smart window/app group launcher for Linux.

Supports: Hyprland · Sway · KDE Plasma · GNOME · i3 · bspwm · XFCE
          and any other X11/Wayland compositor.
UI:       rofi (preferred) · wofi · fuzzel · dmenu (fallbacks)

Usage
─────
  window-groups                   Open the main launcher menu
  window-groups --launch "Work"   Launch a group directly (great for keybinds)
  window-groups --manage          Open group management
  window-groups --smart           Open smart groups analysis
  window-groups --save-session    Snapshot currently open windows
  window-groups --restore-session Restore last saved session
  window-groups --list            Print group names (for scripts/completions)
  window-groups --info            Print detected compositor info

Source: https://github.com/YOUR_USERNAME/window-groups
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as a script without installing the package
_repo_root = Path(__file__).resolve().parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from lib import compositor as comp
from lib import config
from lib import groups as grp_mgr
from lib import launcher
from lib import session
from lib import smart
from lib import ui


# ─── Main menu ────────────────────────────────────────────────────────────────

def main_menu():
    while True:
        groups = config.load_groups()
        names  = sorted(groups.keys())

        info   = comp.get()
        status = f"Compositor: {info.wm_name}   UI: {ui.launcher_name()}"

        launch_items = [
            f"▶  {n}   —   {groups[n].get('description', '')}   "
            f"({len(groups[n].get('apps', []))} apps)"
            for n in names
        ]
        sep = ["─────────────────────"]
        actions = [
            "✏️   Manage groups",
            "💡  Smart groups",
            "💾  Save current session",
            "🔄  Restore last session",
            "❓  Help / about",
        ]

        sel = ui.prompt("Window Groups", launch_items + sep + actions,
                        message=status)
        if not sel:
            return

        # Launch a group
        matched = next((n for n in names if sel.startswith(f"▶  {n}")), None)
        if matched:
            launcher.launch_group(matched, groups)
            return

        if sel.startswith("✏️"):
            grp_mgr.manage_menu()
        elif sel.startswith("💡"):
            smart.smart_menu()
        elif sel.startswith("💾"):
            session.save_session()
            return
        elif sel.startswith("🔄"):
            session.restore_session()
        elif sel.startswith("❓"):
            _help_menu()


def _help_menu():
    info  = comp.get()
    lines = [
        "window-groups  —  https://github.com/YOUR_USERNAME/window-groups",
        f"  Compositor : {info.wm_name}",
        f"  UI backend : {ui.launcher_name()}",
        f"  Config dir : {config.CONFIG_DIR}",
        f"  Groups file: {config.GROUPS_FILE}",
        "",
        "KEYBINDINGS (add to your WM config)",
        "  Main menu       →  window-groups",
        "  Manage groups   →  window-groups --manage",
        "  Save session    →  window-groups --save-session",
        "  Restore session →  window-groups --restore-session",
        "",
        "LAUNCHING A GROUP DIRECTLY",
        "  window-groups --launch \"Work\"",
        "",
        "EXPORT / IMPORT",
        "  Manage → Export groups  (saves JSON to home dir)",
        "  Manage → Import groups  (merges JSON into current groups)",
        "",
        "AUTO-SAVE ON SHUTDOWN",
        "  systemctl --user enable window-groups-save.service",
        "  (after running the installer)",
    ]
    ui.prompt("Help & About", lines)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="window-groups",
        description="Smart window/app group launcher for Linux",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--launch",           metavar="GROUP",
                   help="Launch a group by name and exit")
    p.add_argument("--save-session",     action="store_true",
                   help="Save currently open windows to session file")
    p.add_argument("--restore-session",  action="store_true",
                   help="Open the session restore menu")
    p.add_argument("--manage",           action="store_true",
                   help="Open the group management menu")
    p.add_argument("--smart",            action="store_true",
                   help="Open the smart groups menu")
    p.add_argument("--list",             action="store_true",
                   help="Print all group names to stdout")
    p.add_argument("--info",             action="store_true",
                   help="Print detected compositor / environment info")
    p.add_argument("--export",           metavar="FILE",
                   help="Export groups to a JSON file")
    p.add_argument("--import-groups",    metavar="FILE",
                   help="Import groups from a JSON file (merges)")
    p.add_argument("--version",          action="version", version="window-groups 1.0.0")
    return p


def main():
    args = build_parser().parse_args()

    if args.info:
        info = comp.get()
        print(f"Compositor : {info.wm_name}  ({info.wm.value})")
        print(f"Display    : {info.display_server.name}")
        print(f"WS tool    : {info.workspace_tool or '(none)'}")
        print(f"Win tool   : {info.window_list_tool or '(none)'}")
        print(f"UI backend : {ui.launcher_name()}")
        print(f"Config dir : {config.CONFIG_DIR}")
        return

    if args.list:
        for name in sorted(config.load_groups().keys()):
            print(name)
        return

    if args.launch:
        ok = launcher.launch_group(args.launch)
        sys.exit(0 if ok else 1)

    if args.save_session:
        session.save_session()
        return

    if args.restore_session:
        session.restore_session()
        return

    if args.manage:
        grp_mgr.manage_menu()
        return

    if args.smart:
        smart.smart_menu()
        return

    if args.export:
        import json
        Path(args.export).write_text(
            json.dumps(config.load_groups(), indent=2)
        )
        print(f"Groups exported to {args.export}")
        return

    if args.import_groups:
        import json
        imported = json.loads(Path(args.import_groups).read_text())
        groups   = config.load_groups()
        groups.update(imported)
        config.save_groups(groups)
        print(f"Imported {len(imported)} group(s).")
        return

    # Default: open main menu
    main_menu()


if __name__ == "__main__":
    main()
