#!/usr/bin/env bash

# Launch the GUI from this folder, regardless of the directory the launcher
# was started from (which is important when opened by a desktop shortcut).
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR"
exec python3 "$SCRIPT_DIR/mifi_gui.py"
