#!/bin/bash
# CHIMERA — sign the frozen core onedir bundle (A-2) with hardened runtime, deep over every
# nested Mach-O, all under ONE identity. This is what lets the shim pin core's code signature
# (Slice 2b) and what protects core's in-memory per-boot secret from a same-uid task_for_pid
# (hardened runtime + no get-task-allow). Run AFTER deploy/build-core.sh. See deploy/INSTALL.md.
#
#   bash deploy/sign-core.sh
#   CHIMERA_SIGN_ID="<name-or-SHA1>" bash deploy/sign-core.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ENTITLEMENTS="$HERE/entitlements.plist" # empty dict: no get-task-allow, no disable-library-validation
BUNDLE="$HERE/../dist/chimera"
EXE="$BUNDLE/chimera"

# Same identity resolution as deploy/sign.sh: explicit override, else first VALID 40-hex SHA-1.
resolve_identity() {
    if [ -n "${CHIMERA_SIGN_ID:-}" ]; then
        printf '%s' "$CHIMERA_SIGN_ID"
        return 0
    fi
    security find-identity -v -p codesigning 2>/dev/null \
        | awk 'match($0, /[0-9A-Fa-f]{40}/) {print substr($0, RSTART, 40); exit}'
}

[ -x "$EXE" ] || {
    echo "[x] $EXE not found — run deploy/build-core.sh first" >&2
    exit 1
}
ID="$(resolve_identity)"
[ -n "$ID" ] || {
    echo "[x] no VALID code-signing identity (see deploy/sign.sh for how to create one)" >&2
    exit 1
}
echo "[*] using identity: $ID"

sign() {
    codesign --force --options runtime --timestamp=none \
        --entitlements "$ENTITLEMENTS" --sign "$ID" "$1"
}

# Bottom-up: every nested Mach-O first, main executable last, so the outer signature seals
# over already-signed libraries. One identity throughout -> library validation passes under
# hardened runtime WITHOUT the disable-library-validation hole.
echo "[*] signing nested Mach-O (dylibs / .so / Python framework)..."
n=0
while IFS= read -r -d '' f; do
    sign "$f"
    n=$((n + 1))
done < <(find "$BUNDLE/_internal" -type f \( -name '*.so' -o -name '*.dylib' \) -print0)
sign "$BUNDLE/_internal/Python.framework/Versions/3.13/Python"
echo "[*] signed $((n + 1)) nested Mach-O"

echo "[*] signing main executable: $EXE"
sign "$EXE"

echo "[*] verifying (strict, deep)..."
codesign --verify --strict --deep --verbose=2 "$EXE"
echo "[*] flags: $(codesign -dv "$EXE" 2>&1 | grep -i '^CodeDirectory' || true)"
echo "[*] done."
