#!/usr/bin/env bash
# apply.sh — disassociate Wi-Fi → set new MAC (iface stays UP) → reassociate
#
# macOS specifics:
#   - SIOCSIFLLADDR fails on a DOWN interface ("Network is down")
#   - The trick is: keep iface UP, but disassociate from SSID first
#   - `networksetup -setairportpower off/on` is the macOS-native way to do this
set -e

IFACE="${1:-en0}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SPOOF="$SCRIPT_DIR/mac_spoof"

if [ ! -x "$SPOOF" ]; then
    echo "✗ mac_spoof binary not found at $SPOOF — run 'make' first"
    exit 1
fi

if [ "$EUID" -ne 0 ]; then
    echo "✗ this script needs root"
    echo "  re-run: sudo $0 $IFACE"
    exit 1
fi

OLD_MAC=$("$SPOOF" show "$IFACE" | awk '{print $2}')
echo "→ $IFACE current MAC: $OLD_MAC"

echo "→ turning Wi-Fi OFF (disassociate, keep iface UP)…"
networksetup -setairportpower "$IFACE" off
sleep 2

echo "→ applying new random MAC…"
"$SPOOF" set "$IFACE"
SET_RC=$?

echo "→ turning Wi-Fi ON (reassociate)…"
networksetup -setairportpower "$IFACE" on

# Reassociation can take a few seconds depending on network
echo "→ waiting for reassociation…"
sleep 5

NEW_MAC=$("$SPOOF" show "$IFACE" | awk '{print $2}')
echo
echo "── result ──"
echo "  old: $OLD_MAC"
echo "  new: $NEW_MAC"

if [ "$OLD_MAC" = "$NEW_MAC" ]; then
    echo
    echo "⚠ MAC did NOT change after reassociation."
    echo "  macOS Sequoia+ has 'Private Wi-Fi address' which can revert"
    echo "  our change when it joins a known SSID."
    echo "  Workaround options:"
    echo "    1) System Settings → Wi-Fi → (i) on SSID → Private Wi-Fi address: Off"
    echo "    2) Forget the network, then run this script again before reconnect"
    exit 2
fi

echo "✓ MAC successfully changed"
