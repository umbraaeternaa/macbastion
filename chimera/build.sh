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

echo ""
echo "==> CHIMERA built. Bring the organism up with:"
echo "      .venv/bin/python -m core up      # core + all 8 organs"
echo "      .venv/bin/python -m core status  # see it live"
