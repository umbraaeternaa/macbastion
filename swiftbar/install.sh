#!/usr/bin/env bash
# Install macbastion SwiftBar plugin + triggers
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p ~/.config/macbastion/swiftbar-plugins
mkdir -p ~/.config/macbastion/triggers

cp "$DIR/macbastion.5s.py"   ~/.config/macbastion/swiftbar-plugins/
cp "$DIR/triggers/"*.sh      ~/.config/macbastion/triggers/

chmod +x ~/.config/macbastion/swiftbar-plugins/macbastion.5s.py
chmod +x ~/.config/macbastion/triggers/*.sh

echo "✓ installed to ~/.config/macbastion/"
echo "  Open SwiftBar and point its plugin dir to:"
echo "  ~/.config/macbastion/swiftbar-plugins/"
