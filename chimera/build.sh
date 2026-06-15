#!/usr/bin/env bash
# CHIMERA — one-command build. Sets up the Python venv + builds every native organ, so a
# fresh clone is ready to run. Usage:
#     ./build.sh            # build everything
#     ./build.sh --dev      # also install the dev tooling (pytest/ruff/mypy)
# Then bring the organism up:
#     .venv/bin/python -m core up
set -euo pipefail
cd "$(dirname "$0")"

# --- Homebrew C dependencies (CLAUDE.md §6): CHAFF -> openssl@3, VAULT -> libsodium ---
for dep in openssl@3 libsodium; do
  brew --prefix "$dep" >/dev/null 2>&1 || {
    echo "MISSING Homebrew dependency: $dep"
    echo "  install it with:  brew install $dep"
    exit 1
  }
done

# --- Python 3.11+ (the project floor; an older python3 builds an unusable venv) ---
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
  echo "MISSING: Python 3.11+ (found: $(python3 -V 2>&1))." >&2
  echo "  Install a newer python3 (e.g. brew install python@3.12), then re-run ./build.sh" >&2
  exit 1
fi

# --- Python venv + dependencies ---
echo "==> python venv + deps"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m ensurepip --upgrade >/dev/null 2>&1 || true  # bootstrap pip if absent
.venv/bin/python -m pip install --quiet --upgrade pip
if [ "${1:-}" = "--dev" ]; then
  .venv/bin/python -m pip install --quiet -r requirements-dev.txt
else
  .venv/bin/python -m pip install --quiet -r requirements.txt
fi

# --- native organs (C / C++ / AArch64 asm). oracle + pulse are pure Python (no build) ---
echo "==> native organs"
for m in chaff echo mirror vault tether purge; do
  printf '    %-8s ' "$m"
  make -C "modules/$m" >/dev/null && echo "ok"
done

# TETHER is launched as a real .app bundle (its CFBundleIdentifier makes macOS bind the
# Bluetooth TCC grant to the daemon — OPEN TAIL #1). Assemble the bundle from the binary
# just built; ./sign.sh signs it as a bundle so the grant persists across rebuilds.
printf '    %-8s ' "tether.app"
make -C modules/tether app >/dev/null && echo "ok"

echo ""
echo "==> CHIMERA built. Bring the organism up with:"
echo "      .venv/bin/python -m core up      # core + all 8 organs"
echo "      .venv/bin/python -m core status  # see it live"
