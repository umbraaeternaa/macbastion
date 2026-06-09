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
  echo "[*] '$IDENTITY' code-signing identity not found — creating a self-signed one"
  local tmp
  tmp="$(mktemp -d)"
  openssl req -x509 -newkey rsa:2048 -keyout "$tmp/key.pem" -out "$tmp/cert.pem" \
    -days 3650 -nodes -subj "/CN=$IDENTITY" \
    -addext "extendedKeyUsage=critical,codeSigning" \
    -addext "basicConstraints=critical,CA:FALSE" 2>/dev/null
  # macOS `security` can't import an openssl-3 default PKCS#12 (SHA-256 MAC) — it fails
  # with "MAC verification failed". -legacy makes openssl emit the SHA-1/3DES form Apple
  # reads; fall back without it for LibreSSL / older openssl. A non-empty transient
  # password avoids the empty-password MAC edge case.
  local p12pass="chimera"
  if ! openssl pkcs12 -export -legacy -inkey "$tmp/key.pem" -in "$tmp/cert.pem" \
        -out "$tmp/chimera.p12" -passout "pass:$p12pass" -name "$IDENTITY" 2>/dev/null; then
    openssl pkcs12 -export -inkey "$tmp/key.pem" -in "$tmp/cert.pem" \
      -out "$tmp/chimera.p12" -passout "pass:$p12pass" -name "$IDENTITY"
  fi
  security import "$tmp/chimera.p12" -k "$KEYCHAIN" -P "$p12pass" -T /usr/bin/codesign
  rm -rf "$tmp"
  echo "[*] imported into $KEYCHAIN"
  echo "[!] ONE manual step: open Keychain Access -> '$IDENTITY' -> Get Info -> Trust ->"
  echo "    'Code Signing: Always Trust' (self-signed certs are untrusted until you say so)."
  echo "    Then re-run this script. See deploy/INSTALL.md."
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
