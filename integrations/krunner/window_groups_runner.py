#!/usr/bin/env python3
"""
integrations/krunner/window_groups_runner.py
─────────────────────────────────────────────
KRunner plugin for window-groups.

Exposes every group as a KRunner result so you can type
  "work"  or  "wg work"  in KRunner (Alt+Space / Alt+F2)
and hit Enter to launch the group — no rofi needed.

PROTOCOL
  Implements org.kde.krunner1 over D-Bus (session bus).
  KRunner calls Match(), Run(), and Actions() on us.

DEPENDENCIES
  pip install dbus-python          (or: sudo apt install python3-dbus)
  -- dbus-python is the only external dep this file needs --

INSTALL (done automatically by install.sh --kde)
  1. Copy this file somewhere permanent, e.g.:
       ~/.local/share/window-groups/integrations/krunner/window_groups_runner.py
  2. Install the .desktop service file (see window-groups-runner.desktop below)
  3. kquitapp6 krunner && krunner   (or log out/in)

  The installer handles all of this for you.
"""

from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

# ── locate our lib/ from wherever this file lives ──────────────────────────
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent   # integrations/krunner → integrations → root
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    import dbus
    import dbus.service
    import dbus.mainloop.glib
    from gi.repository import GLib
    _DBUS_OK = True
except ImportError:
    _DBUS_OK = False

from lib import config
from lib import launcher

# ── D-Bus constants ─────────────────────────────────────────────────────────
DBUS_SERVICE   = "com.github.window_groups.krunner"
DBUS_PATH      = "/window_groups_runner"
DBUS_IFACE     = "org.kde.krunner1"

# Match relevance scores (0.0 – 1.0)
RELEVANCE_EXACT  = 1.0
RELEVANCE_PREFIX = 0.9
RELEVANCE_FUZZY  = 0.7

# KRunner match types
MATCH_EXACT      = 100
MATCH_POSSIBLE   = 70
MATCH_INFORMATIONAL = 20

# KRunner icon — use a standard icon name or an absolute path
ICON_NAME = "window-duplicate"   # reasonable fallback; KDE will scale it


def _icon() -> str:
    """Return the best available icon for the runner matches."""
    # Try our own icon first
    custom = _ROOT / "assets" / "window-groups.png"
    if custom.exists():
        return str(custom)
    return ICON_NAME


class WindowGroupsRunner(dbus.service.Object):
    """
    KRunner plugin that exposes window-groups groups as launchable results.
    """

    def __init__(self, conn, obj_path=DBUS_PATH):
        super().__init__(conn, obj_path)

    # ── KRunner API ─────────────────────────────────────────────────────────

    @dbus.service.method(DBUS_IFACE, in_signature="s",
                         out_signature="a(ssssia{sv})")
    def Match(self, query: str):
        """
        Called by KRunner as the user types.
        Returns a list of (data, display_text, icon, type, relevance, props).
        """
        query = query.strip().lower()
        groups = config.load_groups()
        results = []

        # Strip optional "wg " prefix so "wg work" and "work" both work
        if query.startswith("wg "):
            query = query[3:].strip()

        for name, meta in groups.items():
            name_lower = name.lower()
            desc       = meta.get("description", "")
            n_apps     = len(meta.get("apps", []))
            subtitle   = f"{desc}  ·  {n_apps} app{'s' if n_apps!=1 else ''}"

            if not query:
                # Show all groups when nothing is typed yet (after "wg ")
                relevance = RELEVANCE_FUZZY
                mtype     = MATCH_POSSIBLE
            elif name_lower == query:
                relevance = RELEVANCE_EXACT
                mtype     = MATCH_EXACT
            elif name_lower.startswith(query):
                relevance = RELEVANCE_PREFIX
                mtype     = MATCH_POSSIBLE
            elif query in name_lower or query in desc.lower():
                relevance = RELEVANCE_FUZZY
                mtype     = MATCH_POSSIBLE
            else:
                # Try fuzzy: all query chars appear in order in name
                if _fuzzy_match(query, name_lower):
                    relevance = RELEVANCE_FUZZY * 0.8
                    mtype     = MATCH_POSSIBLE
                else:
                    continue

            props = dbus.Dictionary({
                "subtext": subtitle,
                "urls":    dbus.Array([], signature="s"),
            }, signature="sv")

            results.append((
                name,          # data — passed back to Run()
                name,          # display text
                _icon(),       # icon
                mtype,         # match type
                relevance,     # relevance
                props,
            ))

        return results

    @dbus.service.method(DBUS_IFACE, in_signature="ss")
    def Run(self, data: str, action_id: str):
        """Called when the user hits Enter on a result."""
        groups = config.load_groups()
        if data in groups:
            launcher.launch_group(data, groups, silent=True)

    @dbus.service.method(DBUS_IFACE, out_signature="a(sss)")
    def Actions(self):
        """
        Optional secondary actions shown as sub-buttons in KRunner.
        Return list of (id, text, icon).
        """
        return [
            ("manage", "Manage this group", "document-edit"),
        ]

    @dbus.service.method(DBUS_IFACE, in_signature="s",
                         out_signature="a(ssssia{sv})")
    def Config(self):
        return []


def _fuzzy_match(query: str, target: str) -> bool:
    """Return True if all chars of query appear in order in target."""
    it = iter(target)
    return all(c in it for c in query)


# ── Entry point ─────────────────────────────────────────────────────────────

def main():
    if not _DBUS_OK:
        print(
            "ERROR: dbus-python or PyGObject not found.\n"
            "Install with:  pip install dbus-python\n"
            "           or: sudo apt install python3-dbus python3-gi",
            file=sys.stderr,
        )
        sys.exit(1)

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    session_bus = dbus.SessionBus()

    # Acquire service name
    bus_name = dbus.service.BusName(DBUS_SERVICE, session_bus)
    runner   = WindowGroupsRunner(session_bus)

    print(f"window-groups KRunner plugin running on {DBUS_SERVICE}", flush=True)

    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
