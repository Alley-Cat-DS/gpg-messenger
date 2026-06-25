#!/usr/bin/env bash
# build_mac.sh — builds GPG Messenger.app and packages it as a .dmg
# Run on macOS with: bash build_mac.sh
set -e

echo "=== GPG Messenger — macOS Build ==="

# ── Requirements ──────────────────────────────────────────────────────────────
echo "→ Checking requirements..."

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install from https://python.org or via Homebrew."
    exit 1
fi

if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "ERROR: tkinter not available. Run: brew install python-tk"
    exit 1
fi

if ! command -v pip3 &>/dev/null && ! python3 -m pip --version &>/dev/null; then
    echo "ERROR: pip not found."
    exit 1
fi

# ── Install build deps ────────────────────────────────────────────────────────
echo "→ Installing PyInstaller and create-dmg..."
python3 -m pip install --quiet --upgrade pyinstaller

if ! command -v create-dmg &>/dev/null; then
    if command -v brew &>/dev/null; then
        brew install create-dmg
    else
        echo "WARNING: create-dmg not found. DMG packaging will be skipped."
        echo "         Install with: brew install create-dmg"
        NO_DMG=1
    fi
fi

# ── Generate placeholder icon if missing ──────────────────────────────────────
mkdir -p assets
if [ ! -f assets/icon.icns ]; then
    echo "→ Generating placeholder icon (replace assets/icon.icns with your own)..."
    # Create a simple 512x512 PNG using Python, then convert to icns
    python3 - << 'PYEOF'
import struct, zlib, os

def make_png(size=512):
    """Minimal valid PNG — dark background with lock emoji placeholder."""
    def chunk(name, data):
        c = name + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))
    # Simple dark blue-grey square
    row = b'\x00' + b'\x1a\x1b\x1e' * size
    raw = row * size
    idat = chunk(b'IDAT', zlib.compress(raw))
    iend = chunk(b'IEND', b'')
    return sig + ihdr + idat + iend

os.makedirs('assets/icon.iconset', exist_ok=True)
png = make_png(512)
for size in [16, 32, 64, 128, 256, 512]:
    with open(f'assets/icon.iconset/icon_{size}x{size}.png', 'wb') as f:
        f.write(png)
    with open(f'assets/icon.iconset/icon_{size}x{size}@2x.png', 'wb') as f:
        f.write(png)
print("Icon PNGs written.")
PYEOF
    if command -v iconutil &>/dev/null; then
        iconutil -c icns assets/icon.iconset -o assets/icon.icns
        echo "→ icon.icns created."
    else
        echo "WARNING: iconutil not found, skipping .icns generation."
        cp assets/icon.iconset/icon_512x512.png assets/icon.icns 2>/dev/null || true
    fi
fi

# ── Clean previous build ───────────────────────────────────────────────────────
echo "→ Cleaning previous build..."
rm -rf build dist

# ── PyInstaller ───────────────────────────────────────────────────────────────
echo "→ Running PyInstaller..."
python3 -m PyInstaller gpg_messenger.spec --noconfirm

APP_PATH="dist/GPG Messenger.app"
if [ ! -d "$APP_PATH" ]; then
    echo "ERROR: Build failed — .app not found at: $APP_PATH"
    exit 1
fi
echo "→ .app built: $APP_PATH"

# ── DMG packaging ─────────────────────────────────────────────────────────────
if [ -z "$NO_DMG" ]; then
    echo "→ Creating .dmg..."
    DMG_NAME="GPG-Messenger-macOS.dmg"
    rm -f "$DMG_NAME"
    create-dmg \
        --volname "GPG Messenger" \
        --volicon "assets/icon.icns" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "GPG Messenger.app" 175 190 \
        --hide-extension "GPG Messenger.app" \
        --app-drop-link 425 190 \
        "$DMG_NAME" \
        "dist/"
    echo ""
    echo "✓ Done: $DMG_NAME"
else
    echo "✓ Done: $APP_PATH (no DMG — install create-dmg to package)"
fi
