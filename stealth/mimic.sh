#!/usr/bin/env bash
# mimic.sh — ONE coordinated STEALTH identity rotation: hostname + Tor exit IP.
#
# MAC is intentionally NOT here: forced SIOCSIFLLADDR is blocked on current macOS (rc=3),
# and macOS "Private Wi-Fi Address" already hides + rotates the Wi-Fi MAC (real a4:cf:.. stays
# hidden). So this rotates what we CAN, cleanly. See memory direction-stealth-mimicry.
#
# CHIMERA-SAFE: touches ONLY hostname + Tor's app-level control — NEVER pf (ECHO) or
# Bluetooth (TETHER). INSTANT: no Wi-Fi blip. Needs root for the hostname set.
#   sudo ./mimic.sh
set -u
# Real owner even under osascript-admin (SUDO_USER unset, whoami=root) — use the console user.
OWNER="${SUDO_USER:-$(stat -f%Su /dev/console)}"
STATE_DIR="/Users/$OWNER/.config/macbastion"
LOG="$STATE_DIR/mimic.log"
HOST_BACKUP="$STATE_DIR/hostname.original"
mkdir -p "$STATE_DIR"

if [ "$EUID" -ne 0 ]; then echo "✗ needs root: sudo $0"; exit 1; fi
ts()  { date "+%Y-%m-%dT%H:%M:%S"; }
log() { echo "$(ts) $*" | tee -a "$LOG"; }

log "── mimic rotate (hostname + Tor IP) — MAC=macOS, pf/Bluetooth untouched ──"

# back up the original hostname once (so NORMAL mode can restore it)
[ -f "$HOST_BACKUP" ] || scutil --get ComputerName > "$HOST_BACKUP" 2>/dev/null || true

# 1. hostname — instant, no network drop
NEWHOST="Mac-$(LC_ALL=C tr -dc 'a-f0-9' </dev/urandom | head -c 6)"
scutil --set ComputerName "$NEWHOST"
scutil --set HostName "$NEWHOST"
scutil --set LocalHostName "$NEWHOST"
dscacheutil -flushcache 2>/dev/null || true
log "hostname -> $NEWHOST"

# 2. Tor exit IP — SIGNAL NEWNYM (null auth). App-level only: no pf, CHIMERA-safe.
/usr/bin/python3 - <<'PY' 2>&1 | tee -a "$LOG"
import socket
try:
    s = socket.socket(); s.settimeout(6); s.connect(("127.0.0.1", 9051))
    s.sendall(b"AUTHENTICATE\r\n"); s.recv(128)
    s.sendall(b"SIGNAL NEWNYM\r\n"); r = s.recv(128)
    s.sendall(b"QUIT\r\n"); s.close()
    print("tor NEWNYM -> " + ("OK (exit IP rotates)" if b"250" in r else "FAIL " + repr(r[:50])))
except Exception as e:
    print(f"tor NEWNYM skip ({e})")
PY

log "── rotation done — CHIMERA intact ──"

# hand the log back to the operator so the (non-root) rotation agent can append to it
chown "$OWNER" "$LOG" "$HOST_BACKUP" 2>/dev/null || true
