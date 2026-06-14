#!/bin/bash
# CHIMERA — install the ECHO packet-shaper as a root LaunchDaemon (§8 Amendment A1, EP-9). RUN WITH sudo.
#
# Opt-in, OFF by default (EP-4). Installs the chimera-echo-shaper binary, writes its
# LaunchDaemon plist, AND adds the ONE required pf hook — dummynet-anchor "com.chimera.echo" —
# to /etc/pf.conf (with a backup), so the runtime daemon's anchor is actually evaluated (F1,
# ECHO_PACKET §7). The runtime daemon then touches ONLY its own anchor; this installer is the
# single, audited main-ruleset touch the operator ratified (EP-9). YOU run this — never CI,
# never core.
#
#   sudo bash deploy/install-echo-shaper.sh              # install + add hook + bootstrap
#   sudo bash deploy/install-echo-shaper.sh --uninstall  # bootout + remove hook + remove
#   PF_CONF=/path bash deploy/install-echo-shaper.sh --add-hook     # hook only (no root if $PF_CONF writable)
#   PF_CONF=/path bash deploy/install-echo-shaper.sh --remove-hook  # remove hook only
set -euo pipefail

LABEL="com.umbra.chimera.echo-shaper"
PLIST="/Library/LaunchDaemons/$LABEL.plist"
LIBEXEC="/usr/local/libexec/chimera"
DEST="$LIBEXEC/chimera-echo-shaper"
SOCKET="/var/run/chimera-echo-shaper.sock"
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/../echo-shaper/chimera-echo-shaper"

PF_CONF="${PF_CONF:-/etc/pf.conf}"                  # overridable so the hook logic tests root-free
HOOK='dummynet-anchor "com.chimera.echo"'
HOOK_AFTER='dummynet-anchor "com.apple/*"'          # insert ours right after the stock dummynet anchor

# --- EP-9 pf.conf hook management (operates on $PF_CONF ONLY; no pfctl/launchctl here) ---
add_hook() {
  [ -f "$PF_CONF" ] || { echo "[x] pf.conf not found: $PF_CONF" >&2; exit 1; }
  if grep -qF "$HOOK" "$PF_CONF"; then
    echo "[*] hook already present in $PF_CONF (idempotent no-op)"
    return 0
  fi
  cp -p "$PF_CONF" "$PF_CONF.chimera-bak"           # pre-edit backup (the original, no hook)
  # Insert our hook on its own line right after the stock com.apple dummynet anchor; if that
  # line is absent, append at end. index() = literal match (the anchor string has regex metachars).
  if grep -qF "$HOOK_AFTER" "$PF_CONF"; then
    awk -v after="$HOOK_AFTER" -v hook="$HOOK" '
      {print}
      index($0, after) && !done {print hook; done=1}
    ' "$PF_CONF" > "$PF_CONF.tmp"
  else
    cp "$PF_CONF" "$PF_CONF.tmp"
    printf '%s\n' "$HOOK" >> "$PF_CONF.tmp"
  fi
  mv "$PF_CONF.tmp" "$PF_CONF"
  echo "[*] added hook to $PF_CONF (backup: $PF_CONF.chimera-bak)"
}

remove_hook() {
  [ -f "$PF_CONF" ] || return 0
  if grep -qF "$HOOK" "$PF_CONF"; then
    grep -vF "$HOOK" "$PF_CONF" > "$PF_CONF.tmp"
    mv "$PF_CONF.tmp" "$PF_CONF"
    echo "[*] removed hook from $PF_CONF"
  else
    echo "[*] hook not present in $PF_CONF (nothing to remove)"
  fi
}

install_shaper() {
  [ "$(id -u)" -eq 0 ] || { echo "[x] run with sudo" >&2; exit 1; }
  [ -f "$SRC" ] || { echo "[x] echo-shaper binary missing: $SRC  (build it: make -C echo-shaper)" >&2; exit 1; }
  if ! codesign --verify "$SRC" 2>/dev/null; then
    echo "[!] $SRC is not validly signed — run deploy/sign.sh first; the per-boot-secret auth"
    echo "    path stays gated until it is signed. Continuing with install."
  fi
  local op_uid
  op_uid="$(stat -f %u /dev/console)"               # the logged-in operator

  mkdir -p "$LIBEXEC"
  install -m 0755 "$SRC" "$DEST"

  add_hook                                          # EP-9: declare our dummynet anchor in main pf
  pfctl -f "$PF_CONF" 2>/dev/null || echo "[!] pfctl -f $PF_CONF failed (is pf enabled? try: sudo pfctl -E)"

  cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$DEST</string>
        <string>--socket-path</string>
        <string>$SOCKET</string>
        <string>--operator-uid</string>
        <string>$op_uid</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ProcessType</key>
    <string>Interactive</string>
</dict>
</plist>
PLISTEOF
  chown root:wheel "$PLIST"
  chmod 0644 "$PLIST"

  launchctl bootout system "$PLIST" 2>/dev/null || true
  launchctl bootstrap system "$PLIST"
  echo "[*] installed + bootstrapped $LABEL"
  echo "    binary: $DEST"
  echo "    socket: $SOCKET   operator-uid: $op_uid"
  echo "    pf hook: $HOOK  ->  $PF_CONF"
}

uninstall() {
  [ "$(id -u)" -eq 0 ] || { echo "[x] run with sudo" >&2; exit 1; }
  launchctl bootout system "$PLIST" 2>/dev/null || true
  rm -f "$PLIST" "$DEST"
  remove_hook                                       # EP-9: pull our line back out of main pf
  pfctl -f "$PF_CONF" 2>/dev/null || true           # FAIL-OPEN: reload stock; never wedge the net
  echo "[*] uninstalled $LABEL"
}

case "${1:-}" in
  --add-hook) add_hook ;;
  --remove-hook) remove_hook ;;
  --uninstall) uninstall ;;
  *) install_shaper ;;
esac
