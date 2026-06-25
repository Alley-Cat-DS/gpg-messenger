#!/usr/bin/env bash
# build_linux.sh — builds GPG Messenger as a portable AppImage
# Run on Ubuntu/Debian with: bash build_linux.sh
# Works on other distros with minor adjustments.
set -e

echo "=== GPG Messenger — Linux Build ==="

# ── Check requirements ────────────────────────────────────────────────────────
echo "→ Checking requirements..."

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install with: sudo apt install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  Python $PYTHON_VERSION found."

if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "ERROR: tkinter not available."
    echo "       Install with: sudo apt install python3-tk"
    exit 1
fi

# ── Install build deps ────────────────────────────────────────────────────────
echo "→ Installing PyInstaller..."
python3 -m pip install --quiet --upgrade pyinstaller

# appimagetool for packaging
APPIMAGETOOL="./appimagetool-x86_64.AppImage"
if [ ! -f "$APPIMAGETOOL" ]; then
    echo "→ Downloading appimagetool..."
    ARCH=$(uname -m)
    curl -fsSL -o "$APPIMAGETOOL" \
        "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${ARCH}.AppImage"
    chmod +x "$APPIMAGETOOL"
fi

# ── Generate placeholder icon if missing ─────────────────────────────────────
mkdir -p assets
if [ ! -f assets/icon.png ]; then
    echo "→ Generating placeholder icon..."
    python3 - << 'PYEOF'
import struct, zlib

def make_png(size=256):
    def chunk(name, data):
        c = name + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
    row = b'\x00' + b'\x1a\x1b\x1e' * size
    raw = row * size
    idat = chunk(b'IDAT', zlib.compress(raw))
    iend = chunk(b'IEND', b'')
    return sig + ihdr + idat + iend

with open('assets/icon.png', 'wb') as f:
    f.write(make_png(256))
print("icon.png created.")
PYEOF
fi

# ── Clean ─────────────────────────────────────────────────────────────────────
echo "→ Cleaning previous build..."
rm -rf build dist GPG-Messenger.AppDir

# ── PyInstaller ───────────────────────────────────────────────────────────────
echo "→ Running PyInstaller..."
python3 -m PyInstaller gpg_messenger.spec --noconfirm

DIST_DIR="dist/GPG Messenger"
if [ ! -d "$DIST_DIR" ]; then
    echo "ERROR: Build failed — dist directory not found."
    exit 1
fi
echo "→ PyInstaller output: $DIST_DIR"

# ── Build AppDir structure ────────────────────────────────────────────────────
echo "→ Building AppDir..."
APPDIR="GPG-Messenger.AppDir"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

# Copy PyInstaller output
cp -r "$DIST_DIR/." "$APPDIR/usr/bin/"

# Desktop entry
cat > "$APPDIR/usr/share/applications/gpg-messenger.desktop" << 'DESKTOP'
[Desktop Entry]
Name=GPG Messenger
Comment=Secure GPG encrypted messaging
Exec=GPG Messenger
Icon=gpg-messenger
Type=Application
Categories=Security;Network;
Keywords=gpg;pgp;encryption;privacy;security;
DESKTOP

# AppRun launcher
cat > "$APPDIR/AppRun" << 'APPRUN'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "${0}")")"
exec "$HERE/usr/bin/GPG Messenger" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

# Icons and desktop file at root (AppImage standard)
cp assets/icon.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/gpg-messenger.png"
cp assets/icon.png "$APPDIR/gpg-messenger.png"
cp "$APPDIR/usr/share/applications/gpg-messenger.desktop" "$APPDIR/gpg-messenger.desktop"

# ── Package as AppImage ───────────────────────────────────────────────────────
echo "→ Packaging AppImage..."
ARCH=$(uname -m)
OUTPUT="GPG-Messenger-Linux-${ARCH}.AppImage"
ARCH=$ARCH "$APPIMAGETOOL" "$APPDIR" "$OUTPUT"
chmod +x "$OUTPUT"

echo ""
echo "✓ Done: $OUTPUT"
echo "  Users can run it with: ./$OUTPUT"
echo "  No installation required — works on any Linux distro."
