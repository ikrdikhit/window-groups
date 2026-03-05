# 🪟 window-groups

> Smart window/app group launcher for Linux — open your entire workflow with one keypress.

[![CI](https://github.com/YOUR_USERNAME/window-groups/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/window-groups/actions)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platforms](https://img.shields.io/badge/platform-Linux-lightgrey)

---

## What is it?

window-groups lets you define named groups of applications (e.g. "Work", "Study", "Gaming") and launch all of them at once with a single hotkey. It also tracks your usage over time to suggest smart groupings, and can save/restore your entire window session across reboots.

```
╔════════════════════════════════════╗
║  Window Groups                     ║
║  ─────────────────────────────────  ║
║  ▶  Work     — Dev workspace (3)   ║
║  ▶  Study    — Research     (3)   ║
║  ▶  Media    — Music/chat   (2)   ║
║  ─────────────────────────────────  ║
║  ✏️  Manage groups                  ║
║  💡 Smart groups                   ║
║  💾 Save current session           ║
╚════════════════════════════════════╝
```

---

## Compositor / WM support

| Compositor | Status | Workspace switching | Window listing |
|---|---|---|---|
| **Hyprland** | ✅ Full | `hyprctl dispatch workspace` | `hyprctl clients -j` |
| **Sway** | ✅ Full | `swaymsg workspace` | `swaymsg -t get_tree` |
| **KDE Plasma (Wayland)** | ✅ Full | `qdbus` / `wmctrl` | `wmctrl` |
| **KDE Plasma (X11)** | ✅ Full | `qdbus` / `wmctrl` | `wmctrl` |
| **GNOME (Wayland)** | ✅ Full | `gdbus` / Shell eval | `wmctrl` |
| **GNOME (X11)** | ✅ Full | `wmctrl` | `wmctrl` |
| **i3** | ✅ Full | `i3-msg workspace` | `wmctrl` |
| **bspwm** | ✅ Full | `bspc desktop` | `wmctrl` |
| **XFCE** | ✅ Full | `wmctrl` | `wmctrl` |
| **MATE** | ✅ Full | `wmctrl` | `wmctrl` |
| **Cinnamon** | ✅ Full | `wmctrl` | `wmctrl` |
| **Openbox** | ✅ Full | `wmctrl` | `wmctrl` |
| **awesome** | ✅ Full | `awesome-client` | `wmctrl` |
| **herbstluftwm** | ✅ Full | `herbstclient` | `wmctrl` |
| **Qtile** | ✅ Full | `qtile cmd-obj` | `wmctrl` |
| **Niri** | ⚡ Partial | workspace via keybind | limited |
| **River** | ⚡ Partial | generic fallback | limited |
| **LabWC / Wayfire** | ⚡ Partial | generic fallback | limited |
| **Any other X11 WM** | ⚡ Partial | `wmctrl` | `wmctrl` |

---

## UI backend support

| Tool | Protocol | Notes |
|---|---|---|
| **rofi** | X11 + XWayland | Most featureful, best styling |
| **wofi** | Native Wayland | Recommended for pure Wayland |
| **fuzzel** | Native Wayland | Lightweight option |
| **dmenu** | X11 + XWayland | Minimal fallback |

window-groups will automatically use the first one it finds. Install your preferred option.

---

## Native desktop integrations

### KDE Plasma — KRunner (Alt+Space)

No rofi or wofi needed. Groups appear directly in KRunner's search popup.

```bash
bash install.sh --kde
```

- Press **Alt+Space**, type a group name → hit Enter to launch
- Type `wg ` to see all groups at once
- Secondary action: "Manage this group" opens the edit menu

**How it works:** a tiny Python D-Bus service (`org.kde.krunner1`) registers with KDE's service bus. KRunner activates it via D-Bus auto-activation — it only runs when KRunner queries it.

**Requirements:** `python3-dbus` (installed automatically by `--kde`)

---

### GNOME Shell — Activities search (Super key)

No rofi needed. Groups appear in the Activities overview search results alongside apps and files.

```bash
bash install.sh --gnome
```

- Press **Super**, start typing a group name → click or press Enter to launch
- Click "Window Groups" result to open the full menu
- After install, enable in: **Settings → Search → Window Groups** (toggle on)

**How it works:** registers a `org.gnome.Shell.SearchProvider2` D-Bus service. GNOME Shell queries it when you type in the Activities search bar. The service is auto-activated on demand — no background process.

**Requirements:** `python3-dbus` (installed automatically by `--gnome`); log out/in once after install.

---

## Installation

- **Python 3.8+** (stdlib only — zero pip dependencies)
- One of: `rofi`, `wofi`, `fuzzel`, or `dmenu`
- One of: `wmctrl` (X11/XWayland), `hyprctl` (Hyprland), or `swaymsg` (Sway) — for session save/restore
- `notify-send` or `kdialog` — optional, for desktop notifications

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/window-groups.git
cd window-groups
bash install.sh
```

The installer will:
1. Check your Python version
2. Detect your compositor and display server
3. Check for and optionally install missing dependencies
4. Install to `~/.local/bin/window-groups`
5. Install shell completions for bash, zsh, and fish
6. Install a systemd user service for auto-save on shutdown
7. Print keybinding instructions for your specific WM

### Options

```bash
bash install.sh --prefix /usr/local   # system-wide install (needs sudo for deps)
bash install.sh --no-deps             # skip dependency installation
bash install.sh --uninstall           # remove everything
```

### Manual install (no root needed)

```bash
git clone https://github.com/YOUR_USERNAME/window-groups.git
cd window-groups

# Make it runnable directly
chmod +x window-groups.py
./window-groups.py
```

---

## Usage

```
window-groups                       Open the main launcher menu
window-groups --launch "Work"       Launch a group directly
window-groups --manage              Open group management
window-groups --smart               Open smart groups analysis
window-groups --save-session        Save currently open windows
window-groups --restore-session     Restore last saved session
window-groups --list                Print group names (for scripts)
window-groups --info                Show compositor detection info
window-groups --export FILE         Export groups to JSON
window-groups --import-groups FILE  Import groups from JSON
```

---

## Keybindings

### Hyprland (`~/.config/hypr/hyprland.conf`)

```conf
bind = $mainMod, G,       exec, window-groups
bind = $mainMod SHIFT, G, exec, window-groups --manage
bind = $mainMod CTRL, S,  exec, window-groups --save-session
bind = $mainMod CTRL, R,  exec, window-groups --restore-session
```

### Sway / i3 (`~/.config/sway/config` or `~/.config/i3/config`)

```conf
bindsym $mod+g       exec window-groups
bindsym $mod+Shift+g exec window-groups --manage
bindsym $mod+ctrl+s  exec window-groups --save-session
bindsym $mod+ctrl+r  exec window-groups --restore-session
```

### bspwm (`~/.config/sxhkd/sxhkdrc`)

```conf
super + g
    window-groups

super + shift + g
    window-groups --manage
```

### KDE Plasma

`System Settings` → `Shortcuts` → `Custom Shortcuts` → `New Command/URL`
- Command: `window-groups`
- Assign: `Meta+G`

### GNOME

`Settings` → `Keyboard` → `View and Customize Shortcuts` → `Custom Shortcuts` → `+`
- Command: `window-groups`
- Shortcut: `Super+G`

### XFCE

`Settings Manager` → `Keyboard` → `Application Shortcuts` → `Add`
- Command: `window-groups`

---

## Configuration

Groups are stored in `~/.config/window-groups/groups.json`. You can edit this file directly or use the built-in management menu.

### Group format

```json
{
  "Work": {
    "description": "Development workspace",
    "color": "#4A90D9",
    "apps": [
      {
        "name":        "Terminal",
        "command":     "kitty",
        "delay":       0,
        "workspace":   1,
        "pre_command": "echo 'Starting terminal'"
      },
      {
        "name":    "Browser",
        "command": "firefox",
        "delay":   0.8
      }
    ]
  }
}
```

#### App fields

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✅ | Display name shown in menus |
| `command` | string | ✅ | Shell command to run |
| `delay` | float | — | Seconds to wait before launching (default: 0) |
| `workspace` | int | — | Workspace/desktop to switch to (1-indexed) |
| `pre_command` | string | — | Shell command to run before this app |

---

## Smart Groups

Smart Groups analyses your launch history (stored locally in `~/.config/window-groups/history.json`) to:

- **Show co-occurrence patterns** — apps you tend to open together
- **Top apps by frequency** — your most-used applications
- **Recent sessions** — what you launched and when
- **Auto-create a group** — clusters frequently co-occurring apps into a suggested group
- **Time-of-day analysis** — which groups you tend to use at different times

No data leaves your machine. No ML frameworks required.

---

## Session Save / Restore

```bash
# Save (also available as a systemd service for auto-save on shutdown)
window-groups --save-session

# Restore interactively
window-groups --restore-session
```

The restore menu lets you:
- Restore all saved windows at once
- Pick individual apps to relaunch
- Save the session as a named group for future use

### Auto-save on shutdown

After running the installer, enable the systemd service:

```bash
systemctl --user enable window-groups-save.service
```

---

## Data files

| File | Purpose |
|---|---|
| `~/.config/window-groups/groups.json` | Your group definitions |
| `~/.config/window-groups/history.json` | Launch history for smart groups |
| `~/.config/window-groups/session.json` | Most recent saved session |

All data is plain JSON — easy to back up, version control, or sync across machines.

---

## Contributing

Pull requests welcome! Areas to contribute:

- Support for more compositors (niri workspace control, river tags, etc.)
- Additional UI themes
- Test coverage
- Packaging (AUR, Nix flake, Flatpak)

---

## License

MIT — see [LICENSE](LICENSE)
