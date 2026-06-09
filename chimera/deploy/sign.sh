#!/bin/bash
# CHIMERA — local code-signing. Signs binaries with a VALID code-signing identity already
# in your keychain (e.g. your "Apple Development" cert) — no self-signed cert needed, since
# macOS won't use an untrusted one anyway. Override with CHIMERA_SIGN_ID="<name-or-SHA1>".
# YOU run this — never CI, never core. See deploy/INSTALL.md.
#
#   bash deploy/sign.sh shim/chimera-shim
#   CHIMERA_SIGN_ID=ABCD...40hex bash deploy/sign.sh shim/chimera-shim
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ENTITLEMENTS="$HERE/entitlements.plist"

# Resolve a code-signing identity: explicit override, else the first VALID one (40-hex SHA-1).
resolve_identity() {
  if [ -n "${CHIMERA_SIGN_ID:-}" ]; then
    printf '%s' "$CHIMERA_SIGN_ID"
    return 0
  fi
  security find-identity -v -p codesigning 2>/dev/null \
    | awk 'match($0, /[0-9A-Fa-f]{40}/) {print substr($0, RSTART, 40); exit}'
}

sign_one() {
  local id="$1" bin="$2"
  [ -f "$bin" ] || { echo "[x] no such binary: $bin" >&2; return 1; }
  echo "[*] signing: $bin"
  codesign --force --options runtime --timestamp=none \
    --entitlements "$ENTITLEMENTS" --sign "$id" "$bin"
  if codesign --verify --verbose=2 "$bin" 2>/dev/null; then
    echo "[ok] signed + verifies: $bin"
  else
    echo "[!] signed, but codesign --verify is unhappy: $bin" >&2
  fi
}

main() {
  [ "$#" -ge 1 ] || { echo "usage: bash deploy/sign.sh <binary> [<binary>...]" >&2; exit 2; }
  local id
  id="$(resolve_identity)"
  if [ -z "$id" ]; then
    cat >&2 <<'MSG'
[x] No VALID code-signing identity found in your keychain.
    If you have an Apple Development cert it is used automatically. Otherwise create a
    self-signed one: Keychain Access -> Certificate Assistant -> Create a Certificate
    (Name: CHIMERA Local, Identity Type: Self Signed Root, Certificate Type: Code Signing),
    then re-run. Or pass one: CHIMERA_SIGN_ID="<name or SHA1>" bash deploy/sign.sh <bin>
MSG
    exit 1
  fi
  echo "[*] using identity: $id"
  for b in "$@"; do sign_one "$id" "$b"; done
  echo "[*] done."
}

main "$@"
