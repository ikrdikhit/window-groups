#!/usr/bin/env python3
"""
integrations/gnome/window_groups_search_provider.py
─────────────────────────────────────────────────────
GNOME Shell Search Provider for window-groups.

Registers as a org.gnome.Shell.SearchProvider2 D-Bus service so that
pressing Super and typing a group name shows it in the Activities overview
search results — no extra launcher needed on GNOME.

PROTOCOL  (org.gnome.Shell.SearchProvider2)
  GetInitialResultSet(terms)         → result IDs matching all terms
  GetSubsearchResultSet(prev, terms) → narrow previous results
  GetResultMetas(ids)                → display metadata for each result
  ActivateResult(id, terms, ts)      → launch the group
  LaunchSearch(terms, ts)            → open window-groups main menu

DEPENDENCIES
  pip install dbus-python
  (dbus-python + PyGObject — same as KRunner plugin)

INSTALL (done by install.sh --gnome)
  Files placed at:
    ~/.local/share/dbus-1/services/
        com.github.window_groups.SearchProvider.service
    ~/.local/share/gnome-shell/search-providers/
        window-groups-search-provider.ini
  Then:
    systemctl --user restart gnome-shell-portal-helper   (or log out/in)
"""

from __future__ import annotations

import sys
import subprocess
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
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
DBUS_SERVICE = "com.github.window_groups.SearchProvider"
DBUS_PATH    = "/com/github/window_groups/SearchProvider"
DBUS_IFACE   = "org.gnome.Shell.SearchProvider2"


def _terms_match(name: str, desc: str, terms: list[str]) -> bool:
    """Return True if every term appears somewhere in name or description."""
    haystack = (name + " " + desc).lower()
    return all(t.lower() in haystack for t in terms)


def _icon_for(group_name: str, meta: dict) -> str:
    """
    Return a GIcon string. We use a symbolic icon name; GNOME will resolve it.
    For a richer experience you could return 'themed:<icon-name>' or an
    absolute path to a PNG.
    """
    custom = _ROOT / "assets" / "window-groups.png"
    if custom.exists():
        return str(custom)
    return "window-duplicate-symbolic"


class WindowGroupsSearchProvider(dbus.service.Object):
    """
    GNOME Shell Search Provider 2 implementation.
    Result IDs are simply group names.
    """

    def __init__(self, conn, obj_path=DBUS_PATH):
        super().__init__(conn, obj_path)

    # ── SearchProvider2 API ─────────────────────────────────────────────────

    @dbus.service.method(DBUS_IFACE,
                         in_signature="as", out_signature="as")
    def GetInitialResultSet(self, terms):
        """Return IDs (group names) matching all terms."""
        groups  = config.load_groups()
        results = []
        for name, meta in sorted(groups.items()):
            desc = meta.get("description", "")
            if _terms_match(name, desc, terms):
                results.append(name)
        return results

    @dbus.service.method(DBUS_IFACE,
                         in_signature="asas", out_signature="as")
    def GetSubsearchResultSet(self, previous_results, terms):
        """Narrow the previous result set — re-filter is fine here."""
        groups  = config.load_groups()
        results = []
        for name in previous_results:
            if name not in groups:
                continue
            desc = groups[name].get("description", "")
            if _terms_match(name, desc, terms):
                results.append(name)
        return results

    @dbus.service.method(DBUS_IFACE,
                         in_signature="as", out_signature="aa{sv}")
    def GetResultMetas(self, ids):
        """
        Return display metadata for each result ID.
        Each dict must have at least 'id' and 'name'.
        Supported keys: id, name, description, gicon, clipboardText.
        """
        groups = config.load_groups()
        metas  = []
        for gid in ids:
            if gid not in groups:
                continue
            meta  = groups[gid]
            n_apps = len(meta.get("apps", []))
            desc   = meta.get("description", "")
            subtitle = f"{desc}  ·  {n_apps} app{'s' if n_apps != 1 else ''}"

            metas.append(dbus.Dictionary({
                "id":          dbus.String(gid),
                "name":        dbus.String(gid),
                "description": dbus.String(subtitle),
                "gicon":       dbus.String(_icon_for(gid, meta)),
            }, signature="sv"))
        return metas

    @dbus.service.method(DBUS_IFACE,
                         in_signature="sasu")
    def ActivateResult(self, result_id, terms, timestamp):
        """Launch the group when the user clicks/enters a result."""
        groups = config.load_groups()
        if result_id in groups:
            launcher.launch_group(result_id, groups, silent=True)

    @dbus.service.method(DBUS_IFACE,
                         in_signature="asu")
    def LaunchSearch(self, terms, timestamp):
        """
        Called when the user clicks 'Show more results' or similar.
        Open the window-groups main menu.
        """
        _script = _ROOT / "window-groups.py"
        python  = sys.executable
        subprocess.Popen(
            [python, str(_script)],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


# ── Entry point ─────────────────────────────────────────────────────────────

def main():
    if not _DBUS_OK:
        print(
            "ERROR: dbus-python or PyGObject not found.\n"
            "Install:  pip install dbus-python\n"
            "      or: sudo apt install python3-dbus python3-gi",
            file=sys.stderr,
        )
        sys.exit(1)

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    session_bus = dbus.SessionBus()

    bus_name = dbus.service.BusName(DBUS_SERVICE, session_bus)
    provider  = WindowGroupsSearchProvider(session_bus)

    print(f"window-groups GNOME search provider running on {DBUS_SERVICE}",
          flush=True)

    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
