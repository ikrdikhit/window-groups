#!/usr/bin/env bash
# install.sh — window-groups installer
# Supports: Arch, Debian/Ubuntu, Fedora/RHEL, openSUSE, Void, NixOS, Alpine
# Usage: bash install.sh [--prefix PREFIX] [--no-deps] [--uninstall]
set -euo pipefail
IFS=$'\n\t'

# ─── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; YLW='\033[0;33m'; GRN='\033[0;32m'
BLU='\033[0;34m'; CYN='\033[0;36m'; BOLD='\033[1m'; RST='\033[0m'

info()    { echo -e "${BLU}[INFO]${RST}  $*"; }
success() { echo -e "${GRN}[OK]${RST}    $*"; }
warn()    { echo -e "${YLW}[WARN]${RST}  $*"; }
error()   { echo -e "${RED}[ERR]${RST}   $*" >&2; }
die()     { error "$*"; exit 1; }
header()  { echo -e "\n${BOLD}${CYN}=== $* ===${RST}"; }

# ─── Defaults ─────────────────────────────────────────────────────────────────
PREFIX="${HOME}/.local"
BIN_DIR="${PREFIX}/bin"
SHARE_DIR="${PREFIX}/share/window-groups"
SYSTEMD_DIR="${HOME}/.config/systemd/user"
COMP_BASH_DIR="${HOME}/.local/share/bash-completion/completions"
COMP_ZSH_DIR="${HOME}/.local/share/zsh/site-functions"
COMP_FISH_DIR="${HOME}/.config/fish/completions"
INSTALL_DEPS=true
DO_UNINSTALL=false
INSTALL_KDE=false
INSTALL_GNOME=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ─── Arg parsing ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix)       PREFIX="$2"; BIN_DIR="${PREFIX}/bin"; SHARE_DIR="${PREFIX}/share/window-groups"; shift 2 ;;
    --no-deps)      INSTALL_DEPS=false; shift ;;
    --uninstall)    DO_UNINSTALL=true; shift ;;
    --kde)          INSTALL_KDE=true; shift ;;
    --gnome)        INSTALL_GNOME=true; shift ;;
    -h|--help)
      echo "Usage: bash install.sh [--prefix DIR] [--no-deps] [--kde] [--gnome] [--uninstall]"
      echo ""
      echo "  --prefix DIR    Install to DIR/bin (default: ~/.local)"
      echo "  --no-deps       Skip dependency installation"
      echo "  --kde           Install KRunner plugin (no extra launcher needed on KDE)"
      echo "  --gnome         Install GNOME search provider (no extra launcher on GNOME)"
      echo "  --uninstall     Remove window-groups from the system"
      exit 0 ;;
    *) die "Unknown argument: $1. Use --help for usage." ;;
  esac
done

# ─── Uninstall ────────────────────────────────────────────────────────────────
do_uninstall() {
  header "Uninstalling window-groups"

  local files=(
    "${BIN_DIR}/window-groups"
    "${COMP_BASH_DIR}/window-groups"
    "${COMP_ZSH_DIR}/_window-groups"
    "${COMP_FISH_DIR}/window-groups.fish"
  )
  for f in "${files[@]}"; do
    if [[ -f "$f" ]]; then
      rm -f "$f" && success "Removed $f"
    fi
  done

  if [[ -d "${SHARE_DIR}" ]]; then
    rm -rf "${SHARE_DIR}" && success "Removed ${SHARE_DIR}"
  fi

  # Disable systemd service
  if systemctl --user is-enabled window-groups-save.service &>/dev/null; then
    systemctl --user disable --now window-groups-save.service 2>/dev/null || true
    success "Disabled systemd service"
  fi
  local svc="${SYSTEMD_DIR}/window-groups-save.service"
  [[ -f "$svc" ]] && rm -f "$svc" && success "Removed $svc"

  echo ""
  success "window-groups uninstalled."
  warn "Your config (~/.config/window-groups/) was NOT removed."
  warn "Delete it manually if you want a clean slate:"
  warn "  rm -rf ~/.config/window-groups"
}

if $DO_UNINSTALL; then
  do_uninstall
  exit 0
fi

# ─── Banner ───────────────────────────────────────────────────────────────────
echo -e "${BOLD}"
cat << 'EOF'
  ╦ ╦╦╔╗╔╔╦╗╔═╗╦ ╦  ╔═╗╦═╗╔═╗╦ ╦╔═╗╔═╗
  ║║║║║║║ ║║║ ║║║║  ║ ╦╠╦╝║ ║║ ║╠═╝╚═╗
  ╚╩╝╩╝╚╝═╩╝╚═╝╚╩╝  ╚═╝╩╚═╚═╝╚═╝╩  ╚═╝
  Smart window/app group launcher for Linux
EOF
echo -e "${RST}"

# ─── System checks ────────────────────────────────────────────────────────────
header "System checks"

# Python version
PYTHON=""
for py in python3 python3.11 python3.10 python3.9 python3.8; do
  if command -v "$py" &>/dev/null; then
    ver=$("$py" -c 'import sys; print(sys.version_info[:2])')
    # Check >= 3.8
    if "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)' 2>/dev/null; then
      PYTHON="$py"
      break
    fi
  fi
done

if [[ -z "$PYTHON" ]]; then
  die "Python 3.8+ is required but not found. Install it with your package manager."
fi

PYTHON_VER=$($PYTHON --version 2>&1)
success "Python: ${PYTHON_VER}"

# Detect OS / package manager
OS_ID=""
PKG_MGR=""
INSTALL_CMD=""

if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
  OS_ID="${ID:-unknown}"
fi

detect_pkg_manager() {
  if   command -v pacman  &>/dev/null; then PKG_MGR="pacman";  INSTALL_CMD="sudo pacman -S --noconfirm --needed"
  elif command -v apt-get &>/dev/null; then PKG_MGR="apt";     INSTALL_CMD="sudo apt-get install -y"
  elif command -v dnf     &>/dev/null; then PKG_MGR="dnf";     INSTALL_CMD="sudo dnf install -y"
  elif command -v zypper  &>/dev/null; then PKG_MGR="zypper";  INSTALL_CMD="sudo zypper install -y"
  elif command -v xbps-install &>/dev/null; then PKG_MGR="xbps"; INSTALL_CMD="sudo xbps-install -y"
  elif command -v apk     &>/dev/null; then PKG_MGR="apk";     INSTALL_CMD="sudo apk add"
  elif command -v nix-env &>/dev/null; then PKG_MGR="nix";     INSTALL_CMD="nix-env -iA nixpkgs"
  else PKG_MGR="unknown"; fi
}
detect_pkg_manager
info "Detected OS: ${PRETTY_NAME:-${OS_ID}} | Package manager: ${PKG_MGR}"

# ─── Display server detection ─────────────────────────────────────────────────
header "Display server detection"

SESSION_TYPE="${XDG_SESSION_TYPE:-}"
WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-}"
DISPLAY_X11="${DISPLAY:-}"
CURRENT_DESKTOP="${XDG_CURRENT_DESKTOP:-${DESKTOP_SESSION:-unknown}}"

if [[ -n "$WAYLAND_DISPLAY" || "$SESSION_TYPE" == "wayland" ]]; then
  DS="Wayland"
elif [[ -n "$DISPLAY_X11" || "$SESSION_TYPE" == "x11" ]]; then
  DS="X11"
else
  DS="unknown"
fi

info "Display server: ${DS}"
info "Desktop: ${CURRENT_DESKTOP}"

# ─── Dependency matrix ────────────────────────────────────────────────────────
header "Checking dependencies"

# Core tools by package manager
declare -A PKG_NAMES_APT=(
  [rofi]="rofi" [wofi]="wofi" [wmctrl]="wmctrl" [xdotool]="xdotool"
  [notify-send]="libnotify-bin"
)
declare -A PKG_NAMES_PACMAN=(
  [rofi]="rofi" [wofi]="wofi" [wmctrl]="wmctrl" [xdotool]="xdotool"
  [notify-send]="libnotify"
)
declare -A PKG_NAMES_DNF=(
  [rofi]="rofi" [wofi]="wofi" [wmctrl]="wmctrl" [xdotool]="xdotool"
  [notify-send]="libnotify"
)
declare -A PKG_NAMES_ZYPPER=(
  [rofi]="rofi" [wofi]="wofi" [wmctrl]="wmctrl" [xdotool]="xdotool"
  [notify-send]="libnotify-tools"
)
declare -A PKG_NAMES_XBPS=(
  [rofi]="rofi" [wofi]="wofi" [wmctrl]="wmctrl" [xdotool]="xdotool"
  [notify-send]="libnotify"
)
declare -A PKG_NAMES_APK=(
  [rofi]="rofi" [wofi]="wofi" [wmctrl]="wmctrl" [xdotool]="xdotool"
  [notify-send]="libnotify"
)

check_tool() {
  local tool="$1"
  local required="${2:-optional}"
  if command -v "$tool" &>/dev/null; then
    success "${tool} ✓"
    return 0
  else
    if [[ "$required" == "required" ]]; then
      warn "${tool} ✗  (required — will attempt to install)"
    else
      warn "${tool} ✗  (optional)"
    fi
    return 1
  fi
}

# Check UI backends (need at least one)
UI_OK=false
for ui_tool in rofi wofi fuzzel dmenu; do
  if command -v "$ui_tool" &>/dev/null; then
    UI_OK=true
    success "${ui_tool} ✓  (UI backend)"
  fi
done

if ! $UI_OK; then
  warn "No UI backend found. Will try to install rofi."
  if [[ "$DS" == "Wayland" ]]; then
    warn "On Wayland, wofi or fuzzel may work better than rofi."
    warn "  Arch: sudo pacman -S wofi"
    warn "  Apt:  sudo apt install wofi"
  fi
fi

# Check window listing tools
WM_TOOL_OK=false
for wt in hyprctl swaymsg wmctrl; do
  if command -v "$wt" &>/dev/null; then
    WM_TOOL_OK=true
    success "${wt} ✓  (window management)"
  fi
done

if ! $WM_TOOL_OK; then
  warn "No window management tool found."
  warn "Session save/restore will be limited without wmctrl/hyprctl/swaymsg."
fi

check_tool "notify-send" "optional"
check_tool "kdialog"     "optional"

# ─── Install missing deps ─────────────────────────────────────────────────────
header "Installing dependencies"

install_pkg() {
  local tool="$1"
  if command -v "$tool" &>/dev/null; then return 0; fi

  local pkg_name=""
  case "$PKG_MGR" in
    apt)    pkg_name="${PKG_NAMES_APT[$tool]:-$tool}" ;;
    pacman) pkg_name="${PKG_NAMES_PACMAN[$tool]:-$tool}" ;;
    dnf)    pkg_name="${PKG_NAMES_DNF[$tool]:-$tool}" ;;
    zypper) pkg_name="${PKG_NAMES_ZYPPER[$tool]:-$tool}" ;;
    xbps)   pkg_name="${PKG_NAMES_XBPS[$tool]:-$tool}" ;;
    apk)    pkg_name="${PKG_NAMES_APK[$tool]:-$tool}" ;;
    nix)    pkg_name="nixpkgs.${tool}" ;;
    *)      warn "Cannot auto-install ${tool} (unknown package manager)"; return 1 ;;
  esac

  info "Installing ${tool} (${pkg_name})…"
  if $INSTALL_CMD "$pkg_name" 2>/dev/null; then
    success "Installed ${tool}"
    return 0
  else
    warn "Could not install ${tool} automatically."
    warn "Please install it manually: ${pkg_name}"
    return 1
  fi
}

if $INSTALL_DEPS; then
  # Require at least one UI backend
  if ! $UI_OK; then
    if [[ "$DS" == "Wayland" ]]; then
      install_pkg "wofi" || install_pkg "rofi" || true
    else
      install_pkg "rofi" || true
    fi
  fi

  # wmctrl for X11 setups
  if [[ "$DS" != "Wayland" ]] || command -v wmctrl &>/dev/null; then
    install_pkg "wmctrl" || true
  fi

  install_pkg "notify-send" || true
else
  info "Skipping dependency installation (--no-deps)"
fi

# Final UI check
UI_FOUND=""
for ui_tool in rofi wofi fuzzel dmenu; do
  if command -v "$ui_tool" &>/dev/null; then
    UI_FOUND="$ui_tool"
    break
  fi
done

if [[ -z "$UI_FOUND" ]]; then
  die "No UI backend available. Install one of: rofi, wofi, fuzzel, dmenu"
fi
success "Using UI backend: ${UI_FOUND}"

# ─── Install files ────────────────────────────────────────────────────────────
header "Installing window-groups"

mkdir -p "${BIN_DIR}" "${SHARE_DIR}" "${SHARE_DIR}/lib"
success "Created directories"

# Copy source files
cp "${SCRIPT_DIR}/window-groups.py" "${SHARE_DIR}/window-groups.py"
chmod 755 "${SHARE_DIR}/window-groups.py"

# Copy lib modules
for f in "${SCRIPT_DIR}/lib/"*.py; do
  cp "$f" "${SHARE_DIR}/lib/"
done

# Copy integration files
cp -r "${SCRIPT_DIR}/integrations" "${SHARE_DIR}/"
success "Installed source files to ${SHARE_DIR}"

# Create launcher wrapper in bin
cat > "${BIN_DIR}/window-groups" << WRAPPER
#!/usr/bin/env bash
exec "${PYTHON}" "${SHARE_DIR}/window-groups.py" "\$@"
WRAPPER
chmod 755 "${BIN_DIR}/window-groups"
success "Created launcher: ${BIN_DIR}/window-groups"

# Ensure ~/.local/bin is in PATH
SHELL_RC=""
case "${SHELL:-/bin/bash}" in
  */zsh)  SHELL_RC="${ZDOTDIR:-$HOME}/.zshrc" ;;
  */fish) SHELL_RC="${HOME}/.config/fish/config.fish" ;;
  *)      SHELL_RC="${HOME}/.bashrc" ;;
esac

PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
FISH_PATH_LINE='fish_add_path $HOME/.local/bin'

if [[ "${BIN_DIR}" == "${HOME}/.local/bin" ]]; then
  if ! echo "$PATH" | grep -q "${HOME}/.local/bin"; then
    warn "${HOME}/.local/bin is not in your PATH."
    if [[ -f "${SHELL_RC}" ]]; then
      if [[ "${SHELL}" == *fish ]]; then
        echo "" >> "${SHELL_RC}"
        echo "${FISH_PATH_LINE}" >> "${SHELL_RC}"
      else
        echo "" >> "${SHELL_RC}"
        echo "# Added by window-groups installer" >> "${SHELL_RC}"
        echo "${PATH_LINE}" >> "${SHELL_RC}"
      fi
      success "Added ${HOME}/.local/bin to PATH in ${SHELL_RC}"
      warn "Restart your shell or run: source ${SHELL_RC}"
    else
      warn "Add this to your shell RC manually:"
      warn "  ${PATH_LINE}"
    fi
  fi
fi

# ─── Shell completions ────────────────────────────────────────────────────────
header "Installing shell completions"

install_bash_completion() {
  mkdir -p "${COMP_BASH_DIR}"
  cat > "${COMP_BASH_DIR}/window-groups" << 'COMP'
_window_groups() {
  local cur prev opts groups
  COMPREPLY=()
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"

  opts="--launch --save-session --restore-session --manage --smart
        --list --info --export --import-groups --version --help"

  if [[ "$prev" == "--launch" ]]; then
    groups=$(window-groups --list 2>/dev/null)
    COMPREPLY=($(compgen -W "${groups}" -- "${cur}"))
    return 0
  fi

  COMPREPLY=($(compgen -W "${opts}" -- "${cur}"))
  return 0
}
complete -F _window_groups window-groups
COMP
  success "Bash completion installed → ${COMP_BASH_DIR}/window-groups"
}

install_zsh_completion() {
  mkdir -p "${COMP_ZSH_DIR}"
  cat > "${COMP_ZSH_DIR}/_window-groups" << 'COMP'
#compdef window-groups
_window_groups() {
  local -a opts
  opts=(
    '--launch[Launch a group by name]:group:->groups'
    '--save-session[Save currently open windows]'
    '--restore-session[Open session restore menu]'
    '--manage[Open group management menu]'
    '--smart[Open smart groups menu]'
    '--list[Print group names]'
    '--info[Print compositor info]'
    '--export[Export groups to JSON]:file:_files'
    '--import-groups[Import groups from JSON]:file:_files'
    '--version[Show version]'
    '--help[Show help]'
  )
  _arguments $opts
  case $state in
    groups)
      local groups; groups=(${(f)"$(window-groups --list 2>/dev/null)"})
      _describe 'groups' groups ;;
  esac
}
_window_groups
COMP
  success "Zsh completion installed → ${COMP_ZSH_DIR}/_window-groups"
}

install_fish_completion() {
  mkdir -p "${COMP_FISH_DIR}"
  cat > "${COMP_FISH_DIR}/window-groups.fish" << 'COMP'
function __wg_groups
  window-groups --list 2>/dev/null
end

complete -c window-groups -l launch           -d 'Launch a group' -xa '(__wg_groups)'
complete -c window-groups -l save-session     -d 'Save current windows'
complete -c window-groups -l restore-session  -d 'Restore saved session'
complete -c window-groups -l manage           -d 'Manage groups'
complete -c window-groups -l smart            -d 'Smart groups analysis'
complete -c window-groups -l list             -d 'List group names'
complete -c window-groups -l info             -d 'Show compositor info'
complete -c window-groups -l export           -d 'Export groups to JSON'
complete -c window-groups -l import-groups    -d 'Import groups from JSON'
complete -c window-groups -l version          -d 'Show version'
complete -c window-groups -l help             -d 'Show help'
COMP
  success "Fish completion installed → ${COMP_FISH_DIR}/window-groups.fish"
}

install_bash_completion || warn "Could not install bash completion"
install_zsh_completion  || warn "Could not install zsh completion"
install_fish_completion || warn "Could not install fish completion"

# ─── Systemd user service ─────────────────────────────────────────────────────
header "Installing systemd service (auto-save on shutdown)"

if command -v systemctl &>/dev/null && systemctl --user status &>/dev/null 2>&1; then
  mkdir -p "${SYSTEMD_DIR}"
  cat > "${SYSTEMD_DIR}/window-groups-save.service" << SERVICE
[Unit]
Description=window-groups — save open windows on shutdown
DefaultDependencies=no
Before=default.target

[Service]
Type=oneshot
ExecStart=${BIN_DIR}/window-groups --save-session
RemainAfterExit=yes
TimeoutStopSec=5

[Install]
WantedBy=default.target
SERVICE

  systemctl --user daemon-reload 2>/dev/null || true

  echo ""
  info "Systemd service installed at:"
  info "  ${SYSTEMD_DIR}/window-groups-save.service"
  echo ""
  info "To enable auto-save on shutdown:"
  echo -e "  ${BOLD}systemctl --user enable window-groups-save.service${RST}"
  echo ""
  read -rp "Enable auto-save on shutdown now? [y/N] " yn
  yn="${yn:-n}"
  if [[ "${yn,,}" == "y" ]]; then
    systemctl --user enable window-groups-save.service 2>/dev/null && \
      success "Auto-save enabled" || warn "Could not enable service"
  fi
else
  warn "systemd user session not available — skipping service installation."
  warn "You can manually run --save-session before logging out."
fi

# ─── WM keybinding hints ──────────────────────────────────────────────────────
header "Keybinding setup hints"

WG_CMD="${BIN_DIR}/window-groups"

case "${CURRENT_DESKTOP,,}" in
  *hyprland*)
    echo -e "${YLW}Add to ~/.config/hypr/hyprland.conf:${RST}"
    echo "  bind = \$mainMod, G,       exec, ${WG_CMD}"
    echo "  bind = \$mainMod SHIFT, G, exec, ${WG_CMD} --manage"
    echo "  bind = \$mainMod CTRL, S,  exec, ${WG_CMD} --save-session"
    echo "  bind = \$mainMod CTRL, R,  exec, ${WG_CMD} --restore-session" ;;
  *sway*)
    echo -e "${YLW}Add to ~/.config/sway/config:${RST}"
    echo "  bindsym \$mod+g       exec ${WG_CMD}"
    echo "  bindsym \$mod+Shift+g exec ${WG_CMD} --manage"
    echo "  bindsym \$mod+ctrl+s  exec ${WG_CMD} --save-session"
    echo "  bindsym \$mod+ctrl+r  exec ${WG_CMD} --restore-session" ;;
  *i3*)
    echo -e "${YLW}Add to ~/.config/i3/config:${RST}"
    echo "  bindsym \$mod+g       exec ${WG_CMD}"
    echo "  bindsym \$mod+Shift+g exec ${WG_CMD} --manage"
    echo "  bindsym \$mod+ctrl+s  exec ${WG_CMD} --save-session"
    echo "  bindsym \$mod+ctrl+r  exec ${WG_CMD} --restore-session" ;;
  *kde*|*plasma*)
    echo -e "${YLW}KDE Plasma:${RST}"
    echo "  System Settings → Shortcuts → Custom Shortcuts → New Command"
    echo "  Command: ${WG_CMD}"
    echo "  Assign your preferred key combo (e.g. Meta+G)" ;;
  *gnome*)
    echo -e "${YLW}GNOME:${RST}"
    echo "  Settings → Keyboard → Custom Shortcuts → Add"
    echo "  Command: ${WG_CMD}"
    echo "  Or use dconf:"
    echo "  gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings \\"
    echo "    \"['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/wg/']\"" ;;
  *xfce*)
    echo -e "${YLW}XFCE:${RST}"
    echo "  Settings → Keyboard → Application Shortcuts → Add"
    echo "  Command: ${WG_CMD}" ;;
  *bspwm*)
    echo -e "${YLW}Add to ~/.config/sxhkd/sxhkdrc:${RST}"
    echo "  super + g"
    echo "    ${WG_CMD}"
    echo "  super + shift + g"
    echo "    ${WG_CMD} --manage" ;;
  *kde*|*plasma*)
    echo -e "${YLW}KDE Plasma detected.${RST}"
    if ! $INSTALL_KDE; then
      echo ""
      echo -e "  ${BOLD}Recommended:${RST} install the KRunner plugin so groups appear"
      echo -e "  in KRunner (Alt+Space) without any extra launcher:"
      echo -e "    ${BOLD}bash install.sh --kde${RST}"
      echo ""
    fi
    echo -e "  For a keybind fallback:"
    echo "  System Settings → Shortcuts → Custom Shortcuts → New Command"
    echo "  Command: ${WG_CMD}  |  Shortcut: Meta+G" ;;
  *gnome*)
    echo -e "${YLW}GNOME detected.${RST}"
    if ! $INSTALL_GNOME; then
      echo ""
      echo -e "  ${BOLD}Recommended:${RST} install the GNOME search provider so groups"
      echo -e "  appear in Activities search (Super key) without any extra launcher:"
      echo -e "    ${BOLD}bash install.sh --gnome${RST}"
      echo ""
    fi
    echo -e "  For a keybind fallback:"
    echo "  Settings → Keyboard → Custom Shortcuts → +"
    echo "  Command: ${WG_CMD}  |  Shortcut: Super+G" ;;
  *hyprland*)
    echo -e "${YLW}Add to ~/.config/hypr/hyprland.conf:${RST}"
    echo "  bind = \$mainMod, G,       exec, ${WG_CMD}"
    echo "  bind = \$mainMod SHIFT, G, exec, ${WG_CMD} --manage"
    echo "  bind = \$mainMod CTRL, S,  exec, ${WG_CMD} --save-session"
    echo "  bind = \$mainMod CTRL, R,  exec, ${WG_CMD} --restore-session" ;;
  *sway*)
    echo -e "${YLW}Add to ~/.config/sway/config:${RST}"
    echo "  bindsym \$mod+g       exec ${WG_CMD}"
    echo "  bindsym \$mod+Shift+g exec ${WG_CMD} --manage"
    echo "  bindsym \$mod+ctrl+s  exec ${WG_CMD} --save-session"
    echo "  bindsym \$mod+ctrl+r  exec ${WG_CMD} --restore-session" ;;
  *i3*)
    echo -e "${YLW}Add to ~/.config/i3/config:${RST}"
    echo "  bindsym \$mod+g       exec ${WG_CMD}"
    echo "  bindsym \$mod+Shift+g exec ${WG_CMD} --manage"
    echo "  bindsym \$mod+ctrl+s  exec ${WG_CMD} --save-session"
    echo "  bindsym \$mod+ctrl+r  exec ${WG_CMD} --restore-session" ;;
  *xfce*)
    echo -e "${YLW}XFCE — Settings → Keyboard → Application Shortcuts → Add:${RST}"
    echo "  Command: ${WG_CMD}" ;;
  *bspwm*)
    echo -e "${YLW}Add to ~/.config/sxhkd/sxhkdrc:${RST}"
    echo "  super + g"
    echo "    ${WG_CMD}"
    echo "  super + shift + g"
    echo "    ${WG_CMD} --manage" ;;
  *)
    echo -e "${YLW}Generic — bind these commands in your WM config:${RST}"
    echo "  Main menu:       ${WG_CMD}"
    echo "  Manage:          ${WG_CMD} --manage"
    echo "  Save session:    ${WG_CMD} --save-session"
    echo "  Restore session: ${WG_CMD} --restore-session" ;;
esac

# ─── KDE KRunner integration ──────────────────────────────────────────────────
install_kde_integration() {
  header "Installing KDE KRunner plugin"

  # Check dbus-python
  if ! "$PYTHON" -c "import dbus" 2>/dev/null; then
    info "Installing dbus-python…"
    install_pkg "python3-dbus" || \
    "$PYTHON" -m pip install --user dbus-python 2>/dev/null || \
    warn "Could not install dbus-python. KRunner plugin may not work."
  fi

  local KRUNNER_SVC_DIR="${HOME}/.local/share/dbus-1/services"
  local KRUNNER_DESKTOP_DIR="${HOME}/.local/share/kservices5"
  # KDE6 uses kservices6 / plasma6
  if [[ -d "${HOME}/.local/share/kservices6" ]] || \
     krunner --version 2>/dev/null | grep -q "^krunner 6"; then
    KRUNNER_DESKTOP_DIR="${HOME}/.local/share/kservices6"
  fi

  mkdir -p "${KRUNNER_SVC_DIR}" "${KRUNNER_DESKTOP_DIR}"

  # Write the D-Bus service activation file (replaces placeholders)
  sed \
    -e "s|PLACEHOLDER_PYTHON|${PYTHON}|g" \
    -e "s|PLACEHOLDER_SCRIPT|${SHARE_DIR}/integrations/krunner/window_groups_runner.py|g" \
    "${SHARE_DIR}/integrations/krunner/com.github.window_groups.krunner.service.in" \
    > "${KRUNNER_SVC_DIR}/com.github.window_groups.krunner.service"
  success "KRunner D-Bus service: ${KRUNNER_SVC_DIR}/com.github.window_groups.krunner.service"

  # Write the plasma runner .desktop file
  cp "${SHARE_DIR}/integrations/krunner/window-groups-runner.desktop" \
     "${KRUNNER_DESKTOP_DIR}/window-groups-runner.desktop"
  success "KRunner desktop file: ${KRUNNER_DESKTOP_DIR}/window-groups-runner.desktop"

  echo ""
  info "Restarting KRunner to activate the plugin…"
  kquitapp6 krunner 2>/dev/null || kquitapp5 krunner 2>/dev/null || \
    killall krunner 2>/dev/null || true
  sleep 1
  # KRunner restarts automatically, but start it explicitly just in case
  (krunner &>/dev/null &) || true

  echo ""
  success "KRunner plugin installed!"
  echo -e "  Press ${BOLD}Alt+Space${RST} and type a group name (e.g. \"work\") to launch it."
  echo -e "  You can also prefix with ${BOLD}wg ${RST}to narrow to window-groups results."
}

# ─── GNOME search provider integration ───────────────────────────────────────
install_gnome_integration() {
  header "Installing GNOME Shell search provider"

  if ! "$PYTHON" -c "import dbus" 2>/dev/null; then
    info "Installing dbus-python…"
    install_pkg "python3-dbus" || \
    "$PYTHON" -m pip install --user dbus-python 2>/dev/null || \
    warn "Could not install dbus-python. Search provider may not work."
  fi

  local GNOME_SP_DIR="${HOME}/.local/share/gnome-shell/search-providers"
  local DBUS_SVC_DIR="${HOME}/.local/share/dbus-1/services"
  local APPS_DIR="${HOME}/.local/share/applications"

  mkdir -p "${GNOME_SP_DIR}" "${DBUS_SVC_DIR}" "${APPS_DIR}"

  # Search provider .ini
  cp "${SHARE_DIR}/integrations/gnome/window-groups.ini" \
     "${GNOME_SP_DIR}/window-groups.ini"
  success "Search provider ini: ${GNOME_SP_DIR}/window-groups.ini"

  # D-Bus service activation file
  sed \
    -e "s|PLACEHOLDER_PYTHON|${PYTHON}|g" \
    -e "s|PLACEHOLDER_SCRIPT|${SHARE_DIR}/integrations/gnome/window_groups_search_provider.py|g" \
    "${SHARE_DIR}/integrations/gnome/com.github.window_groups.SearchProvider.service.in" \
    > "${DBUS_SVC_DIR}/com.github.window_groups.SearchProvider.service"
  success "D-Bus service: ${DBUS_SVC_DIR}/com.github.window_groups.SearchProvider.service"

  # .desktop file (required for DesktopId reference in the .ini)
  sed \
    -e "s|PLACEHOLDER_PYTHON|${PYTHON}|g" \
    -e "s|PLACEHOLDER_SCRIPT|${SHARE_DIR}/window-groups.py|g" \
    "${SHARE_DIR}/integrations/gnome/window-groups.desktop.in" \
    > "${APPS_DIR}/window-groups.desktop"
  success "Desktop file: ${APPS_DIR}/window-groups.desktop"

  echo ""
  info "Notifying GNOME Shell to reload search providers…"
  gdbus call --session \
    --dest org.gnome.Shell \
    --object-path /org/gnome/Shell \
    --method org.gnome.Shell.Eval \
    "imports.ui.main.overview._searchController._searchResults._reloadRemoteProviders();" \
    2>/dev/null || true

  echo ""
  success "GNOME search provider installed!"
  echo -e "  Press ${BOLD}Super${RST} and start typing a group name to launch it."
  echo -e "  If it doesn't appear immediately, ${BOLD}log out and back in${RST} once."
  echo -e ""
  echo -e "  ${YLW}Note:${RST} GNOME may require you to enable the provider in:"
  echo -e "    Settings → Search → Window Groups  (toggle ON)"
}

# Auto-detect and prompt if not explicitly requested
if ! $INSTALL_KDE && [[ "${CURRENT_DESKTOP,,}" == *kde* || "${CURRENT_DESKTOP,,}" == *plasma* ]]; then
  echo ""
  read -rp "Install KRunner plugin? (groups appear in Alt+Space search) [Y/n] " yn
  yn="${yn:-y}"
  [[ "${yn,,}" == "y" ]] && INSTALL_KDE=true
fi

if ! $INSTALL_GNOME && [[ "${CURRENT_DESKTOP,,}" == *gnome* ]]; then
  echo ""
  read -rp "Install GNOME search provider? (groups appear in Super search) [Y/n] " yn
  yn="${yn:-y}"
  [[ "${yn,,}" == "y" ]] && INSTALL_GNOME=true
fi

$INSTALL_KDE  && install_kde_integration
$INSTALL_GNOME && install_gnome_integration

# ─── Verify installation ──────────────────────────────────────────────────────
header "Verifying installation"

if command -v window-groups &>/dev/null || [[ -x "${BIN_DIR}/window-groups" ]]; then
  VER=$("${BIN_DIR}/window-groups" --version 2>/dev/null || echo "unknown")
  success "window-groups is installed: ${VER}"
  info "Run: window-groups --info  to see detected compositor details"
else
  warn "Launcher not found in PATH yet."
  warn "Ensure ${BIN_DIR} is in your PATH and restart your shell."
fi

echo ""
echo -e "${BOLD}${GRN}✔ Installation complete!${RST}"
echo ""
echo -e "  Run ${BOLD}window-groups${RST} to open the launcher"
echo -e "  Run ${BOLD}window-groups --info${RST} to verify compositor detection"
echo -e "  Run ${BOLD}bash install.sh --uninstall${RST} to remove"
echo ""
