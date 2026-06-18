#!/usr/bin/env bash
# mimicry.sh — master STEALTH-mimicry toggle:  on | off | status
#
#   on     : Tor system-SOCKS ON + rotate hostname + (Phase 2) load the rotation agent
#   off    : SOCKS OFF (normal IP) + restore the original hostname + unload the agent
#   status : print current mode / hostname / Tor-SOCKS / exit IP   (no root needed)
#
# MAC is macOS "Private Wi-Fi Address" in BOTH modes (the real a4:cf:.. stays hidden — that
# is the macOS default, "like everyone else"). CHIMERA-SAFE: touches only the system SOCKS
# setting + hostname + Tor — never pf (ECHO) or Bluetooth (TETHER). on/off need root (hostname).
set -u
# Resolve the REAL owner even under `osascript … with administrator privileges`
# (which, unlike sudo, leaves SUDO_USER unset and makes whoami=root → wrong /Users/root home).
# The GUI console user is the right owner in every invocation path (osascript-root / sudo / user).
OWNER="${SUDO_USER:-$(stat -f%Su /dev/console)}"
OWNER_UID="$(id -u "$OWNER")"
HOME_DIR="/Users/$OWNER"
STATE_DIR="$HOME_DIR/.config/macbastion"
STATE="$STATE_DIR/mimicry.state"
HOST_BACKUP="$STATE_DIR/hostname.original"
HERE="$(cd "$(dirname "$0")" && pwd)"
SVC="Wi-Fi"
AGENT_PLIST="$HOME_DIR/Library/LaunchAgents/com.umbra.mimicry.plist"
mkdir -p "$STATE_DIR"

need_root() { [ "$EUID" -eq 0 ] || { echo "✗ needs root: sudo $0 $1"; exit 1; }; }
socks() { networksetup -setsocksfirewallproxystate "$SVC" "$1"; }

cmd_on() {
    need_root on
    socks on
    "$HERE/mimic.sh"                                  # initial rotation: hostname + Tor IP
    # Phase 2 (continuous rotation agent) — load if installed; harmless no-op until then.
    [ -f "$AGENT_PLIST" ] && launchctl bootstrap "gui/$OWNER_UID" "$AGENT_PLIST" 2>/dev/null || true
    echo "on" > "$STATE"
    echo "🥷 STEALTH-MIMICRY ON — Tor IP + hostname rotating; MAC = macOS Private Wi-Fi"
}

cmd_off() {
    need_root off
    socks off
    [ -f "$AGENT_PLIST" ] && launchctl bootout "gui/$OWNER_UID" "$AGENT_PLIST" 2>/dev/null || true
    if [ -f "$HOST_BACKUP" ]; then
        orig="$(cat "$HOST_BACKUP")"
        scutil --set ComputerName "$orig"
        scutil --set HostName "$orig"
        scutil --set LocalHostName "$orig"
        dscacheutil -flushcache 2>/dev/null || true
        echo "  hostname restored -> $orig"
    fi
    echo "off" > "$STATE"
    echo "🌐 NORMAL MODE — no Tor proxy, original hostname; MAC stays macOS-default"
}

cmd_status() {
    st="$( [ -f "$STATE" ] && cat "$STATE" || echo unknown )"
    socks_on="$(networksetup -getsocksfirewallproxy "$SVC" 2>/dev/null | awk '/^Enabled/{print $2}')"
    echo "mode:      $st"
    echo "hostname:  $(scutil --get ComputerName 2>/dev/null)"
    echo "Tor SOCKS: ${socks_on:-?}"
}

case "${1:-status}" in
    on)     cmd_on ;;
    off)    cmd_off ;;
    status) cmd_status ;;
    *) echo "usage: $0 {on|off|status}"; exit 1 ;;
esac
