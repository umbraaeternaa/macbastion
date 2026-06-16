#!/usr/bin/env bash
# Install the CHIMERA SwiftBar plugin into the SwiftBar plugin directory. Coexists with any
# other plugins there; touches only the chimera plugin file (never macbastion's, §6).
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGDIR="$(defaults read com.ameba.SwiftBar PluginDirectory 2>/dev/null || true)"
PLUGDIR="${PLUGDIR:-$HOME/.config/macbastion/swiftbar-plugins}"
mkdir -p "$PLUGDIR"
cp "$DIR/chimera.10s.py" "$PLUGDIR/chimera.10s.py"
chmod +x "$PLUGDIR/chimera.10s.py"
echo "installed chimera.10s.py -> $PLUGDIR"
open -a SwiftBar 2>/dev/null || true
open "swiftbar://refreshallplugins" 2>/dev/null || true
echo "done — look for the 🜲 item in the menu bar (refreshes every 10s)."
