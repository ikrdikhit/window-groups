"""
lib/ui.py — UI abstraction layer.

Tries launchers in this order: rofi → wofi → fuzzel → dmenu
Rofi is the most featureful; the others are fallbacks for Wayland-only setups.
All public functions return None when the user cancels.

NOTE ON NATIVE INTEGRATIONS
  On KDE Plasma:  install the KRunner plugin (integrations/krunner/).
                  Groups appear in KRunner (Alt+Space) — no launcher needed.
  On GNOME:       install the search provider (integrations/gnome/).
                  Groups appear in the Activities overview — no launcher needed.
  Both are installed automatically by: bash install.sh --kde  /  --gnome
  This file (ui.py) is still used by the management / smart-groups menus
  even when native integrations handle launching.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Optional


# ─── Theme / style constants ──────────────────────────────────────────────────

ROFI_THEME = r"""
* { font: "Monospace 11"; }
window {
    width: 640px;
    border-radius: 10px;
    border: 2px solid @accent;
    background-color: #1e1e2e;
}
@theme-str-override { accent: #4A90D9; }
mainbox { padding: 12px; spacing: 8px; }
inputbar {
    padding: 8px 14px;
    border-radius: 8px;
    background-color: #2a2a3e;
    text-color: #cdd6f4;
}
message { padding: 6px 10px; border-radius: 6px; background-color: #313244; }
listview { lines: 12; scrollbar: false; spacing: 4px; }
element { padding: 8px 14px; border-radius: 6px; }
element normal normal { text-color: #cdd6f4; }
element selected normal {
    background-color: #4A90D9;
    text-color: #1e1e2e;
}
"""

WOFI_STYLE = """
window { background-color: #1e1e2e; border-radius: 10px; }
#input { background-color: #2a2a3e; color: #cdd6f4; border-radius: 8px; }
#entry { color: #cdd6f4; }
#entry:selected { background-color: #4A90D9; color: #1e1e2e; border-radius: 6px; }
"""


# ─── Launcher detection ───────────────────────────────────────────────────────

def _launcher() -> str:
    """Return the first available launcher binary."""
    for prog in ("rofi", "wofi", "fuzzel", "dmenu"):
        if shutil.which(prog):
            return prog
    return ""


def available_launcher() -> str:
    return _launcher()


def launcher_name() -> str:
    lnch = _launcher()
    return lnch if lnch else "none"


# ─── Core prompt function ─────────────────────────────────────────────────────

def prompt(
    prompt_text: str,
    choices:     list[str],
    *,
    allow_custom: bool = False,
    message:      str  = "",
    multi:        bool = False,
) -> Optional[str | list[str]]:
    """
    Show a menu and return the chosen string, a list of strings (multi=True),
    or None if cancelled / no launcher found.
    """
    lnch = _launcher()
    if not lnch:
        return _cli_fallback(prompt_text, choices, multi=multi)

    if lnch == "rofi":
        return _rofi(prompt_text, choices,
                     allow_custom=allow_custom, message=message, multi=multi)
    elif lnch == "wofi":
        return _wofi(prompt_text, choices,
                     allow_custom=allow_custom, multi=multi)
    elif lnch == "fuzzel":
        return _fuzzel(prompt_text, choices, allow_custom=allow_custom)
    elif lnch == "dmenu":
        return _dmenu(prompt_text, choices)
    return None


def text_input(prompt_text: str, placeholder: str = "") -> Optional[str]:
    """Open a free-text input field. Returns the string or None."""
    lnch = _launcher()
    if not lnch:
        try:
            return input(f"{prompt_text}: ").strip() or None
        except (EOFError, KeyboardInterrupt):
            return None

    if lnch == "rofi":
        cmd = ["rofi", "-dmenu", "-p", prompt_text,
               "-theme-str", ROFI_THEME, "-lines", "0"]
        inp = placeholder.encode()
        r   = subprocess.run(cmd, input=inp, capture_output=True)
        return r.stdout.decode().strip() or None

    elif lnch == "wofi":
        cmd = ["wofi", "--dmenu", "--prompt", prompt_text, "--lines", "1"]
        r   = subprocess.run(cmd, input=placeholder.encode(), capture_output=True)
        return r.stdout.decode().strip() or None

    elif lnch == "fuzzel":
        cmd = ["fuzzel", "--dmenu", "--prompt", f"{prompt_text}: ",
               "--lines", "1"]
        r   = subprocess.run(cmd, input=placeholder.encode(), capture_output=True)
        return r.stdout.decode().strip() or None

    else:  # dmenu
        r = subprocess.run(["dmenu", "-p", prompt_text],
                           input=placeholder.encode(), capture_output=True)
        return r.stdout.decode().strip() or None


# ─── rofi ─────────────────────────────────────────────────────────────────────

def _rofi(prompt_text, choices, *, allow_custom, message, multi):
    cmd = [
        "rofi", "-dmenu",
        "-p", prompt_text,
        "-theme-str", ROFI_THEME,
        "-format", "s",
    ]
    if message:
        cmd += ["-mesg", message]
    if multi:
        cmd += ["-multi-select"]
    if not allow_custom:
        cmd += ["-no-custom"]

    inp = "\n".join(choices).encode()
    r   = subprocess.run(cmd, input=inp, capture_output=True)
    if r.returncode != 0:
        return None
    out = r.stdout.decode().strip()
    if not out:
        return None
    if multi:
        return [l for l in out.splitlines() if l]
    return out


# ─── wofi ─────────────────────────────────────────────────────────────────────

def _wofi(prompt_text, choices, *, allow_custom, multi):
    import tempfile, os
    # Write style to a temp file
    style_file = tempfile.NamedTemporaryFile(
        suffix=".css", mode="w", delete=False
    )
    style_file.write(WOFI_STYLE)
    style_file.close()

    cmd = [
        "wofi", "--dmenu",
        "--prompt", prompt_text,
        "--style", style_file.name,
        "--insensitive",
    ]
    if multi:
        cmd += ["--multi-select"]
    if not allow_custom:
        cmd += ["--hide-search"]

    inp = "\n".join(choices).encode()
    r   = subprocess.run(cmd, input=inp, capture_output=True)
    os.unlink(style_file.name)

    if r.returncode != 0:
        return None
    out = r.stdout.decode().strip()
    if not out:
        return None
    if multi:
        return [l for l in out.splitlines() if l]
    return out


# ─── fuzzel ───────────────────────────────────────────────────────────────────

def _fuzzel(prompt_text, choices, *, allow_custom):
    cmd = [
        "fuzzel", "--dmenu",
        "--prompt", f"{prompt_text}> ",
        "--lines", str(min(len(choices), 15)),
        "--background-color", "1e1e2eff",
        "--text-color",       "cdd6f4ff",
        "--selection-color",  "4A90D9ff",
        "--border-radius",    "10",
    ]
    inp = "\n".join(choices).encode()
    r   = subprocess.run(cmd, input=inp, capture_output=True)
    if r.returncode != 0:
        return None
    return r.stdout.decode().strip() or None


# ─── dmenu ────────────────────────────────────────────────────────────────────

def _dmenu(prompt_text, choices):
    cmd = ["dmenu", "-p", prompt_text, "-l", str(min(len(choices), 15)),
           "-nb", "#1e1e2e", "-nf", "#cdd6f4",
           "-sb", "#4A90D9", "-sf", "#1e1e2e"]
    inp = "\n".join(choices).encode()
    r   = subprocess.run(cmd, input=inp, capture_output=True)
    if r.returncode != 0:
        return None
    return r.stdout.decode().strip() or None


# ─── CLI fallback (no GUI) ────────────────────────────────────────────────────

def _cli_fallback(prompt_text, choices, *, multi=False):
    print(f"\n── {prompt_text} ──")
    for i, c in enumerate(choices, 1):
        print(f"  {i:>2}. {c}")
    try:
        raw = input("Enter number(s) [comma-separated] or 0 to cancel: ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if raw == "0" or not raw:
        return None
    try:
        indices = [int(x.strip()) - 1 for x in raw.split(",")]
        selected = [choices[i] for i in indices if 0 <= i < len(choices)]
        if not selected:
            return None
        return selected if multi else selected[0]
    except (ValueError, IndexError):
        return None


# ─── Notification ─────────────────────────────────────────────────────────────

def notify(title: str, body: str = "", urgency: str = "normal",
           icon: str = "dialog-information"):
    """Send a desktop notification. Tries notify-send, then kdialog, then stderr."""
    if shutil.which("notify-send"):
        subprocess.Popen(
            ["notify-send", f"--urgency={urgency}", f"--icon={icon}",
             "Window Groups — " + title, body],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    elif shutil.which("kdialog"):
        subprocess.Popen(
            ["kdialog", "--passivepopup", f"{title}\n{body}", "4"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    else:
        print(f"[window-groups] {title}: {body}", flush=True)
