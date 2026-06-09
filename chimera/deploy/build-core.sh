#!/usr/bin/env bash
# Build core as a standalone onedir binary (A-1, the §5.5 prerequisite for shim Slice 2b).
# Output: dist/chimera/chimera — a Mach-O whose code signature the shim can pin, so it can
# tell the real core from any same-uid process. Signing is a separate step (deploy/sign.sh).
# Run from anywhere; resolves chimera/ from this script's location. Needs PyInstaller in .venv.
set -euo pipefail
cd "$(dirname "$0")/.." # deploy/ -> chimera/

PYI=.venv/bin/pyinstaller
if [ ! -x "$PYI" ]; then
    echo "error: $PYI not found — run: VIRTUAL_ENV=\$PWD/.venv uv pip install pyinstaller" >&2
    exit 1
fi

# onedir (not onefile): all bundled dylibs stay visible so deploy/sign.sh can re-sign them
# with one identity — hardened runtime then passes library validation without the
# disable-library-validation hole that onefile would force.
rm -rf build/pyinstaller dist/chimera build/chimera.spec
"$PYI" --onedir --name chimera --noconfirm \
    --paths . \
    --specpath build \
    --distpath dist \
    --workpath build/pyinstaller \
    core/__main__.py

echo "built: dist/chimera/chimera"
