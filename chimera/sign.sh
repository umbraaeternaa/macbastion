#!/usr/bin/env bash
# CHIMERA — sign the native binaries with a STABLE code-signing identity, so macOS
# TCC grants (Accessibility for MIRROR, Bluetooth for TETHER, ...) survive rebuilds.
# An unsigned binary is identified by its content hash, which changes every rebuild —
# so its grant resets. A binary signed with a stable identity keeps a stable designated
# requirement, so the grant persists. Usage:
#     ./sign.sh                # auto-detect the first Apple Development / Developer ID identity
#     ./sign.sh <identity>     # a specific identity (full name or SHA-1 hash)
#     ./sign.sh -              # ad-hoc sign (valid signature, but NO stable identity)
set -euo pipefail
cd "$(dirname "$0")"

ID="${1:-}"
if [ -z "$ID" ]; then
  ID=$(security find-identity -v -p codesigning \
        | awk '/Apple Development|Developer ID/ {print $2; exit}')
  [ -z "$ID" ] && {
    echo "no code-signing identity found — pass one explicitly, or use '-' for ad-hoc"
    exit 1
  }
fi
echo "==> signing with identity: $ID"

for m in chaff echo mirror vault tether purge; do
  bin="modules/$m/$m"
  if [ ! -x "$bin" ]; then
    printf '    %-8s (not built — skipped)\n' "$m"
    continue
  fi
  codesign -s "$ID" --force --identifier "com.umbra.chimera.$m" "$bin"
  codesign --verify --strict "$bin"
  printf '    %-8s signed + verified\n' "$m"
done

echo ""
echo "==> done. NOTE: a TCC grant given to an UNSIGNED binary does not match the signed"
echo "    one — re-grant it ONCE after signing (e.g. MIRROR Accessibility); it persists"
echo "    across every later rebuild as long as you re-sign with the same identity."
