#!/bin/bash
# CHIMERA — local code-signing (P1 / keystone). Self-signed, no Apple account, no cloud.
#
# Creates a "CHIMERA Local" code-signing identity once (in your login keychain) and signs
# the given binaries with it + the hardened runtime. This is the keystone the platform
# layer depends on (SHIM.md F2/SS-4): the per-boot secret and every destructive root op
# are gated on a signed binary, and TCC grants only stick to a stable signed identity.
#
# YOU run this — never CI, never core. It only touches your keychain + the named binaries.
# See deploy/INSTALL.md for the full procedure (trust + LaunchDaemon + TCC).
#
#   bash deploy/sign.sh ../shim/chimera-shim          # sign one binary
#   bash deploy/sign.sh ../shim/chimera-shim ../modules/mirror/mirror
set -euo pipefail

IDENTITY="CHIMERA Local"
KEYCHAIN="${CHIMERA_KEYCHAIN:-$HOME/Library/Keychains/login.keychain-db}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ENTITLEMENTS="$HERE/entitlements.plist"

have_identity() { security find-identity -v -p codesigning 2>/dev/null | grep -q "$IDENTITY"; }

create_identity() {
  cat >&2 <<MSG
[x] No trusted '$IDENTITY' code-signing identity found.
    macOS will not let codesign use a self-signed cert until it is TRUSTED, and trust
    cannot be set non-interactively. Create it ONCE via the GUI (it is auto-trusted):

      Keychain Access  ->  menu "Keychain Access"  ->  Certificate Assistant
        ->  "Create a Certificate..."
              Name:             $IDENTITY
              Identity Type:    Self Signed Root
              Certificate Type: Code Signing
        ->  Create  ->  (Continue past the self-signed warning)  ->  Done

    Then re-run:  bash deploy/sign.sh <binary>
MSG
  exit 1
}

sign_one() {
  local bin="$1"
  [ -f "$bin" ] || { echo "[x] no such binary: $bin" >&2; return 1; }
  echo "[*] signing: $bin"
  codesign --force --options runtime --timestamp=none \
    --entitlements "$ENTITLEMENTS" --sign "$IDENTITY" "$bin"
  if codesign --verify --verbose=2 "$bin" 2>/dev/null; then
    echo "[ok] signed + verifies: $bin"
  else
    echo "[!] signed, but verify is unhappy — expected for a self-signed cert you have not"
    echo "    yet trusted for Code Signing (see the trust step above / INSTALL.md)."
  fi
}

main() {
  if [ "$#" -lt 1 ]; then
    echo "usage: bash deploy/sign.sh <binary> [<binary>...]" >&2
    echo "  e.g. bash deploy/sign.sh ../shim/chimera-shim" >&2
    exit 2
  fi
  if ! have_identity; then
    create_identity
    exit 0
  fi
  for b in "$@"; do sign_one "$b"; done
  echo "[*] done."
}

main "$@"
