"""
lib/compositor.py — Compositor / WM detection and compatibility layer.

Supports:
  Wayland: Hyprland, Sway, KDE Plasma (KWin), GNOME Shell, Niri, River,
           LabWC, Wayfire, wlroots-based compositors (generic fallback)
  X11:     i3, bspwm, Openbox, XFCE, MATE, Cinnamon, KDE X11, GNOME X11,
           awesome, dwm, fluxbox, herbstluftwm, spectrwm, qtile (generic fallback)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class DisplayServer(Enum):
    WAYLAND = auto()
    X11     = auto()
    UNKNOWN = auto()


class WM(Enum):
    # Wayland
    HYPRLAND = "hyprland"
    SWAY     = "sway"
    KDE_KWin = "kwin_wayland"
    GNOME_WAYLAND = "gnome-wayland"
    NIRI     = "niri"
    RIVER    = "river"
    LABWC    = "labwc"
    WAYFIRE  = "wayfire"
    WLR_GENERIC = "wlroots"
    # X11
    I3       = "i3"
    BSPWM    = "bspwm"
    OPENBOX  = "openbox"
    XFWM     = "xfwm4"
    MARCO    = "marco"       # MATE
    MUFFIN   = "muffin"      # Cinnamon
    KWIN_X11 = "kwin_x11"
    GNOME_X11= "gnome-x11"
    AWESOME  = "awesome"
    DWM      = "dwm"
    FLUXBOX  = "fluxbox"
    HERBST   = "herbstluftwm"
    SPECTRWM = "spectrwm"
    QTILE    = "qtile"
    GENERIC_X11 = "generic-x11"
    UNKNOWN  = "unknown"


@dataclass
class CompositorInfo:
    display_server: DisplayServer = DisplayServer.UNKNOWN
    wm:             WM            = WM.UNKNOWN
    wm_name:        str           = ""
    version:        str           = ""
    # What capabilities are available
    can_switch_workspace: bool = True
    can_list_windows:     bool = True
    workspace_tool:       str  = ""   # which binary handles workspace ops
    window_list_tool:     str  = ""   # which binary lists windows


# ─── Detection ────────────────────────────────────────────────────────────────

def detect() -> CompositorInfo:
    """Detect the running compositor/WM and return a CompositorInfo."""
    info = CompositorInfo()

    # 1. Display server
    wayland_display = os.environ.get("WAYLAND_DISPLAY", "")
    x11_display     = os.environ.get("DISPLAY", "")
    xdg_session     = os.environ.get("XDG_SESSION_TYPE", "").lower()

    if wayland_display or xdg_session == "wayland":
        info.display_server = DisplayServer.WAYLAND
    elif x11_display or xdg_session == "x11":
        info.display_server = DisplayServer.X11
    else:
        info.display_server = DisplayServer.UNKNOWN

    # 2. Specific compositor
    info.wm_name = (
        os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
        and "hyprland"
        or os.environ.get("SWAYSOCK", "")
        and "sway"
        or os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    )

    # Check env vars first (fast)
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        info.wm      = WM.HYPRLAND
        info.wm_name = "Hyprland"
    elif os.environ.get("SWAYSOCK"):
        info.wm      = WM.SWAY
        info.wm_name = "Sway"
    else:
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        session  = os.environ.get("DESKTOP_SESSION", "").lower()
        gdm_full = os.environ.get("GDMSESSION", "").lower()

        if "hyprland" in desktop:
            info.wm, info.wm_name = WM.HYPRLAND, "Hyprland"
        elif "sway" in desktop or "sway" in session:
            info.wm, info.wm_name = WM.SWAY, "Sway"
        elif "kde" in desktop or "plasma" in desktop:
            if info.display_server == DisplayServer.WAYLAND:
                info.wm, info.wm_name = WM.KDE_KWin, "KDE Plasma (Wayland)"
            else:
                info.wm, info.wm_name = WM.KWIN_X11, "KDE Plasma (X11)"
        elif "gnome" in desktop:
            if info.display_server == DisplayServer.WAYLAND:
                info.wm, info.wm_name = WM.GNOME_WAYLAND, "GNOME (Wayland)"
            else:
                info.wm, info.wm_name = WM.GNOME_X11, "GNOME (X11)"
        elif "niri" in desktop or _proc_running("niri"):
            info.wm, info.wm_name = WM.NIRI, "Niri"
        elif "river" in desktop or _proc_running("river"):
            info.wm, info.wm_name = WM.RIVER, "River"
        elif "wayfire" in desktop or _proc_running("wayfire"):
            info.wm, info.wm_name = WM.WAYFIRE, "Wayfire"
        elif "labwc" in desktop or _proc_running("labwc"):
            info.wm, info.wm_name = WM.LABWC, "LabWC"
        elif _proc_running("i3"):
            info.wm, info.wm_name = WM.I3, "i3"
        elif _proc_running("bspwm"):
            info.wm, info.wm_name = WM.BSPWM, "bspwm"
        elif _proc_running("openbox"):
            info.wm, info.wm_name = WM.OPENBOX, "Openbox"
        elif "xfce" in desktop or _proc_running("xfwm4"):
            info.wm, info.wm_name = WM.XFWM, "XFCE (xfwm4)"
        elif "cinnamon" in desktop or _proc_running("muffin"):
            info.wm, info.wm_name = WM.MUFFIN, "Cinnamon"
        elif "mate" in desktop or _proc_running("marco"):
            info.wm, info.wm_name = WM.MARCO, "MATE"
        elif _proc_running("awesome"):
            info.wm, info.wm_name = WM.AWESOME, "Awesome"
        elif _proc_running("herbstluftwm"):
            info.wm, info.wm_name = WM.HERBST, "herbstluftwm"
        elif _proc_running("spectrwm"):
            info.wm, info.wm_name = WM.SPECTRWM, "spectrwm"
        elif _proc_running("qtile"):
            info.wm, info.wm_name = WM.QTILE, "Qtile"
        elif _proc_running("fluxbox"):
            info.wm, info.wm_name = WM.FLUXBOX, "Fluxbox"
        elif info.display_server == DisplayServer.WAYLAND:
            info.wm, info.wm_name = WM.WLR_GENERIC, "Wayland (generic)"
        elif info.display_server == DisplayServer.X11:
            info.wm, info.wm_name = WM.GENERIC_X11, "X11 (generic)"
        else:
            info.wm, info.wm_name = WM.UNKNOWN, "Unknown"

    # 3. Resolve capability tools
    _resolve_tools(info)
    return info


def _proc_running(name: str) -> bool:
    """Check if a process with the given name is running."""
    try:
        out = subprocess.check_output(
            ["pgrep", "-x", name], stderr=subprocess.DEVNULL
        )
        return bool(out.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _resolve_tools(info: CompositorInfo):
    """Set workspace_tool and window_list_tool based on WM."""
    wm = info.wm

    # Workspace switching tool
    if wm == WM.HYPRLAND:
        info.workspace_tool = "hyprctl"
    elif wm == WM.SWAY:
        info.workspace_tool = "swaymsg"
    elif wm in (WM.KDE_KWin, WM.KWIN_X11):
        if shutil.which("kwin_wayland") or shutil.which("kwriteconfig6"):
            info.workspace_tool = "qdbus"
        else:
            info.workspace_tool = "wmctrl"
    elif wm == WM.GNOME_WAYLAND:
        info.workspace_tool = "gdbus"
    elif wm == WM.I3:
        info.workspace_tool = "i3-msg"
    elif wm == WM.AWESOME:
        info.workspace_tool = "awesome-client"
    elif wm == WM.HERBST:
        info.workspace_tool = "herbstclient"
    elif wm == WM.BSPWM:
        info.workspace_tool = "bspc"
    elif wm == WM.QTILE:
        info.workspace_tool = "qtile"
    elif shutil.which("wmctrl"):
        info.workspace_tool = "wmctrl"
    else:
        info.can_switch_workspace = False

    # Validate the tool exists
    if info.workspace_tool and not shutil.which(info.workspace_tool):
        info.can_switch_workspace = False
        info.workspace_tool = ""

    # Window list tool
    if wm == WM.HYPRLAND:
        info.window_list_tool = "hyprctl"
    elif wm == WM.SWAY:
        info.window_list_tool = "swaymsg"
    elif shutil.which("wmctrl"):
        info.window_list_tool = "wmctrl"
    else:
        info.can_list_windows  = False
        info.window_list_tool  = ""


# ─── Workspace switching ──────────────────────────────────────────────────────

def switch_workspace(workspace: int, info: CompositorInfo) -> bool:
    """Switch to a workspace (1-indexed). Returns True on success."""
    if not info.can_switch_workspace or workspace < 1:
        return False

    ws0 = workspace - 1   # 0-indexed for some tools
    wm  = info.wm

    try:
        if wm == WM.HYPRLAND:
            _run(["hyprctl", "dispatch", "workspace", str(workspace)])
        elif wm == WM.SWAY:
            _run(["swaymsg", f"workspace number {workspace}"])
        elif wm in (WM.KDE_KWin, WM.KWIN_X11):
            _switch_kde(workspace)
        elif wm == WM.GNOME_WAYLAND:
            _switch_gnome_wayland(ws0)
        elif wm == WM.GNOME_X11:
            _run(["wmctrl", "-s", str(ws0)])
        elif wm == WM.I3:
            _run(["i3-msg", f"workspace number {workspace}"])
        elif wm == WM.BSPWM:
            _run(["bspc", "desktop", "-f", f"^{workspace}"])
        elif wm == WM.AWESOME:
            _run(["awesome-client",
                  f'require("awful").screen.focused().tags[{workspace}]:view_only()'])
        elif wm == WM.HERBST:
            _run(["herbstclient", "use", str(ws0)])
        elif wm == WM.QTILE:
            _run(["qtile", "cmd-obj", "-o", "cmd", "-f",
                  "switch_to_group", "-a", str(workspace)])
        elif info.workspace_tool == "wmctrl":
            _run(["wmctrl", "-s", str(ws0)])
        return True
    except Exception:
        return False


def _switch_kde(workspace: int):
    # KDE Plasma: try qdbus (both old and new API), fall back to wmctrl
    qdbus = shutil.which("qdbus6") or shutil.which("qdbus")
    if qdbus:
        services = [
            ["org.kde.KWin", "/KWin", "org.kde.KWin.setCurrentDesktop",
             str(workspace - 1)],
            ["org.kde.kglobalaccel", "/component/kwin",
             "org.kde.kglobalaccel.Component.invokeShortcut",
             f"Switch to Desktop {workspace}"],
        ]
        for svc in services:
            try:
                _run([qdbus] + svc)
                return
            except Exception:
                continue
    if shutil.which("wmctrl"):
        _run(["wmctrl", "-s", str(workspace - 1)])


def _switch_gnome_wayland(ws0: int):
    script = (
        f"const Meta = imports.gi.Meta; "
        f"global.workspace_manager.get_workspace_by_index({ws0}).activate(0);"
    )
    _run(["gdbus", "call", "--session",
          "--dest", "org.gnome.Shell",
          "--object-path", "/org/gnome/Shell",
          "--method", "org.gnome.Shell.Eval",
          script])


# ─── Window listing ───────────────────────────────────────────────────────────

def list_windows(info: CompositorInfo) -> list[dict]:
    """Return a list of dicts: {title, pid, command, workspace}."""
    wm = info.wm
    try:
        if wm == WM.HYPRLAND:
            return _windows_hyprland()
        elif wm == WM.SWAY:
            return _windows_sway()
        elif info.window_list_tool == "wmctrl":
            return _windows_wmctrl()
    except Exception:
        pass
    return []


def _windows_hyprland() -> list[dict]:
    out  = subprocess.check_output(["hyprctl", "clients", "-j"], text=True)
    data = json.loads(out)
    seen = set()
    result = []
    for w in data:
        cmd = (w.get("class") or w.get("initialClass") or "").lower()
        ws  = w.get("workspace", {}).get("id", 1)
        if cmd and cmd not in seen:
            seen.add(cmd)
            result.append({
                "title":     w.get("title", cmd),
                "pid":       w.get("pid", 0),
                "command":   cmd,
                "workspace": ws,
            })
    return result


def _windows_sway() -> list[dict]:
    out  = subprocess.check_output(["swaymsg", "-t", "get_tree"], text=True)
    tree = json.loads(out)
    windows = []
    seen    = set()
    _walk_sway(tree, windows, seen)
    return windows


def _walk_sway(node: dict, out: list, seen: set):
    if node.get("type") == "con" and node.get("app_id"):
        cmd = node["app_id"].lower()
        if cmd not in seen:
            seen.add(cmd)
            ws = 1
            for i, w in enumerate(node.get("nodes", []), 1):
                if w.get("name") == node.get("name"):
                    ws = i
                    break
            out.append({
                "title":     node.get("name", cmd),
                "pid":       node.get("pid", 0),
                "command":   cmd,
                "workspace": ws,
            })
    for child in node.get("nodes", []) + node.get("floating_nodes", []):
        _walk_sway(child, out, seen)


def _windows_wmctrl() -> list[dict]:
    import os
    out = subprocess.check_output(["wmctrl", "-lp"], text=True)
    windows, seen = [], set()
    for line in out.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        _, desktop, pid, _, title = parts
        pid = int(pid) if pid.isdigit() else 0
        exe = ""
        if pid:
            try:
                exe = os.readlink(f"/proc/{pid}/exe")
            except OSError:
                try:
                    raw = open(f"/proc/{pid}/cmdline", "rb").read()
                    exe = raw.split(b"\x00")[0].decode(errors="replace")
                except Exception:
                    pass
        cmd = os.path.basename(exe) if exe else ""
        ws  = int(desktop) + 1 if desktop.lstrip("-").isdigit() else 1
        key = (cmd, ws)
        if cmd and key not in seen:
            seen.add(key)
            windows.append({
                "title":     title.strip(),
                "pid":       pid,
                "command":   cmd,
                "workspace": ws,
            })
    return windows


# ─── Utility ──────────────────────────────────────────────────────────────────

def _run(cmd: list[str], **kwargs):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, **kwargs)


# Singleton — detect once per process
_info: Optional[CompositorInfo] = None

def get() -> CompositorInfo:
    global _info
    if _info is None:
        _info = detect()
    return _info
