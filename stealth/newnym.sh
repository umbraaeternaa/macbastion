#!/bin/bash
# newnym.sh — rotate the Tor exit IP only (SIGNAL NEWNYM via control port 9051, null auth).
# NO root. Driven by the com.umbra.mimicry LaunchAgent: every 20 min + on network change + wake.
# App-level (Tor control) — never touches pf (ECHO) or Bluetooth (TETHER).
# Logging is BEST-EFFORT: NEWNYM must run even if the log file isn't writable (it once was
# root-owned from a sudo run and blocked the user agent — that must never stop the rotation).
OWNER="${SUDO_USER:-$(whoami)}"
LOG="/Users/$OWNER/.config/macbastion/mimic.log"
out=$(/usr/bin/python3 - <<'PY'
import socket, datetime
stamp = datetime.datetime.now().isoformat(timespec="seconds")
try:
    s = socket.socket(); s.settimeout(6); s.connect(("127.0.0.1", 9051))
    s.sendall(b"AUTHENTICATE\r\n"); s.recv(128)
    s.sendall(b"SIGNAL NEWNYM\r\n"); r = s.recv(128)
    s.sendall(b"QUIT\r\n"); s.close()
    print(f"{stamp} agent NEWNYM -> " + ("OK (IP rotated)" if b"250" in r else "FAIL"))
except Exception as e:
    print(f"{stamp} agent NEWNYM skip ({e})")
PY
)
echo "$out"
echo "$out" >> "$LOG" 2>/dev/null || true
