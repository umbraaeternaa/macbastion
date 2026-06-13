#!/usr/bin/env bash
# CHIMERA — one-command self-configuring setup for a fresh clone on any Apple-Silicon Mac.
# Verifies/installs the Homebrew C deps + the Ollama runtime and ORACLE model, then builds
# the venv + all native organs (via build.sh). It does NOT start the organism and touches
# NOTHING privileged (that is `core up` / deploy/INSTALL.md, by your hand). Re-runnable.
#   ./setup.sh            # set everything up
#   ./setup.sh --dev      # also install the dev tooling (pytest/ruff/mypy)
set -euo pipefail
cd "$(dirname "$0")"

bold() { printf '\033[1m%s\033[0m\n' "$1"; }

bold "==> CHIMERA setup"

# --- 0. platform sanity ---
if [ "$(uname -s)" != "Darwin" ]; then
  echo "CHIMERA is macOS-only (Apple Silicon)." >&2
  exit 1
fi

# --- 1. Homebrew + C deps (CLAUDE.md §6: CHAFF -> openssl@3, VAULT -> libsodium) ---
if ! command -v brew >/dev/null 2>&1; then
  echo "MISSING: Homebrew. Install it from https://brew.sh then re-run ./setup.sh" >&2
  exit 1
fi
bold "==> Homebrew C deps (openssl@3, libsodium)"
for dep in openssl@3 libsodium; do
  if brew --prefix "$dep" >/dev/null 2>&1; then
    echo "    $dep ok"
  else
    echo "    installing $dep ..."
    brew install "$dep"
  fi
done

# --- 2. Ollama runtime + the ORACLE model (local LLM, no cloud) ---
ORACLE_MODEL="${CHIMERA_ORACLE_MODEL:-qwen2.5:7b}"
bold "==> Ollama + ORACLE model ($ORACLE_MODEL)"
if ! command -v ollama >/dev/null 2>&1; then
  echo "    installing ollama ..."
  brew install ollama
fi
if ollama list 2>/dev/null | grep -q "$ORACLE_MODEL"; then
  echo "    model $ORACLE_MODEL present"
else
  echo "    pulling $ORACLE_MODEL (one-time, a few GB) ..."
  ollama pull "$ORACLE_MODEL"
fi

# --- 3. venv + native organs (delegates to build.sh; passes --dev through) ---
bold "==> build (venv + 8 organs)"
./build.sh "$@"

# --- 4. next steps (we never auto-start; you bring the organism up yourself) ---
bold "==> CHIMERA is set up."
cat <<'EOF'
    Bring the organism alive (non-privileged — runs unsigned):
      .venv/bin/python -m core up        # core + all 8 organs
      .venv/bin/python -m core status    # see it live

    Run it permanently (starts at login, restarts if it crashes):
      .venv/bin/python -m core plist > ~/Library/LaunchAgents/com.umbra.chimera.plist
      launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.umbra.chimera.plist

    Privileged + TCC-gated capabilities (shim root ops, MIRROR, TETHER, PURGE Keychain):
      see deploy/INSTALL.md — self-signed, by hand (Apple blocks scripting cert creation + TCC).
EOF
