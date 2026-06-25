#!/usr/bin/env bash
# install_linux.sh — installs AlleyCat GPG as a desktop app on Linux
# Run with: bash install_linux.sh
set -e

echo "=== AlleyCat GPG — Linux Desktop Install ==="

# ── Check dependencies ────────────────────────────────────────────────────────
echo "→ Checking dependencies..."

if ! command -v python3 &>/dev/null; then
    echo "Installing python3..."
    sudo apt-get install -y python3
fi

if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "Installing python3-tk..."
    sudo apt-get install -y python3-tk
fi

if ! command -v gpg &>/dev/null; then
    echo "Installing gnupg..."
    sudo apt-get install -y gnupg
fi

echo "✓ Dependencies OK"

# ── Install app files ─────────────────────────────────────────────────────────
INSTALL_DIR="$HOME/.local/share/alleycat-gpg"
mkdir -p "$INSTALL_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp "$SCRIPT_DIR/gpg_messenger.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/launch.sh" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/launch.sh"

echo "→ App installed to: $INSTALL_DIR"

# ── Desktop entry ─────────────────────────────────────────────────────────────
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_DIR/alleycat-gpg.desktop" << EOF
[Desktop Entry]
Name=AlleyCat GPG
GenericName=GPG Messenger
Comment=Encrypt and decrypt messages and files with GPG
Exec=bash $INSTALL_DIR/launch.sh
Icon=security-high
Type=Application
Categories=Security;Network;Utility;
Keywords=gpg;pgp;encryption;privacy;security;
StartupNotify=true
Terminal=false
EOF

chmod +x "$DESKTOP_DIR/alleycat-gpg.desktop"

# Refresh app menu
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$DESKTOP_DIR"
fi

# ── CLI shortcut ──────────────────────────────────────────────────────────────
SYMLINK="/usr/local/bin/alleycat-gpg"
if [ -w "/usr/local/bin" ] || sudo -n true 2>/dev/null; then
    sudo ln -sf "$INSTALL_DIR/launch.sh" "$SYMLINK" 2>/dev/null || true
    echo "→ CLI shortcut: alleycat-gpg"
fi

echo ""
echo "✓ Installed. You can now:"
echo "  • Find 'AlleyCat GPG' in your app launcher / Activities"
echo "  • Run from terminal: bash $INSTALL_DIR/launch.sh"
echo "  • Or directly:       python3 $INSTALL_DIR/gpg_messenger.py"
