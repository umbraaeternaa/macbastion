#!/bin/bash
# CHIMERA — install the privileged shim as a root LaunchDaemon (P2). RUN WITH sudo.
#
# The shim is the ONLY root component (§7.10 / §8.8: lock screen, evict Keychain, reboot,
# force-killall — nothing else). This copies the signed binary to a stable libexec path,
# writes the LaunchDaemon plist (with YOUR console-user UID so core can reach the socket,
# SS-0), and bootstraps it. YOU run this — never CI, never core.
#
#   sudo bash deploy/install-shim.sh              # install + bootstrap
#   sudo bash deploy/install-shim.sh --uninstall  # bootout + remove
set -euo pipefail

LABEL="com.umbra.chimera.shim"
PLIST="/Library/LaunchDaemons/$LABEL.plist"
LIBEXEC="/usr/local/libexec/chimera"
DEST="$LIBEXEC/chimera-shim"
SOCKET="/var/run/chimera-shim.sock"
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/../shim/chimera-shim"
CORE_SRC="$HERE/../dist/chimera/chimera"   # signed frozen core (deploy/build-core.sh + sign-core.sh)
CORE_REQ="$LIBEXEC/core.req"               # core's designated requirement, for SecCode attestation

[ "$(id -u)" -eq 0 ] || { echo "[x] run with sudo" >&2; exit 1; }

uninstall() {
  launchctl bootout system "$PLIST" 2>/dev/null || true
  rm -f "$PLIST" "$DEST" "$CORE_REQ"
  echo "[*] uninstalled $LABEL"
}

install_shim() {
  [ -f "$SRC" ] || { echo "[x] shim binary missing: $SRC  (build it: make -C shim)" >&2; exit 1; }
  if ! codesign --verify "$SRC" 2>/dev/null; then
    echo "[!] $SRC is not validly signed yet — run deploy/sign.sh first (INSTALL.md Step 1)."
    echo "    Continuing, but the privileged auth path (SS-4) stays gated until it is signed."
  fi
  local op_uid
  op_uid="$(stat -f %u /dev/console)"  # the logged-in operator

  mkdir -p "$LIBEXEC"
  install -m 0755 "$SRC" "$DEST"

  # 2b-ii: capture core's designated requirement so the shim attests the connecting peer
  # (audit-token SecCode) before issuing the per-boot secret. Best-effort: if core isn't
  # built+signed, core.req is absent and the shim stays fail-closed (no secret issued).
  if [ -x "$CORE_SRC" ] && codesign --verify "$CORE_SRC" 2>/dev/null; then
    if codesign -d -r- "$CORE_SRC" 2>&1 | sed -n 's/^designated => //p' > "$CORE_REQ" \
       && [ -s "$CORE_REQ" ]; then
      chown root:wheel "$CORE_REQ"; chmod 0644 "$CORE_REQ"
      echo "[*] core designated requirement -> $CORE_REQ"
    else
      rm -f "$CORE_REQ"
      echo "[!] could not capture core requirement — shim stays fail-closed (no secret issued)"
    fi
  else
    echo "[!] core binary not built+signed ($CORE_SRC): shim runs WITHOUT attestation"
    echo "    (fail-closed, no per-boot secret). Run deploy/build-core.sh + sign-core.sh, then reinstall."
  fi

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
        <string>--core-req</string>
        <string>$CORE_REQ</string>
        <string>-m</string>
        <string>privileged</string>
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
}

case "${1:-}" in
  --uninstall) uninstall ;;
  *) install_shim ;;
esac
