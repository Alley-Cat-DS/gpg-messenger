#!/usr/bin/env bash
# launch.sh — runs AlleyCat GPG without a terminal window
# Used by the .desktop entry so no terminal flashes on launch.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Redirect stdout/stderr to a log file instead of the terminal
LOG="$HOME/.local/share/alleycat-gpg/launch.log"
mkdir -p "$(dirname "$LOG")"

exec python3 "$SCRIPT_DIR/gpg_messenger.py" >> "$LOG" 2>&1
