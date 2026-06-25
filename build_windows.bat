@echo off
REM build_windows.bat — builds GPG Messenger .exe and Inno Setup installer
REM Run on Windows with: build_windows.bat
setlocal enabledelayedexpansion

echo === GPG Messenger — Windows Build ===

REM ── Check Python ─────────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: python not found. Install from https://python.org
    echo        Make sure "Add Python to PATH" is checked during install.
    exit /b 1
)

python -c "import tkinter" 2>nul
if errorlevel 1 (
    echo ERROR: tkinter not available.
    echo        Install Python from https://python.org ^(not the Microsoft Store version^).
    exit /b 1
)

REM ── Install PyInstaller ───────────────────────────────────────────────────────
echo ^-^> Installing PyInstaller...
python -m pip install --quiet --upgrade pyinstaller
if errorlevel 1 (
    echo ERROR: pip install failed.
    exit /b 1
)

REM ── Generate placeholder icon if missing ─────────────────────────────────────
if not exist assets mkdir assets
if not exist assets\icon.ico (
    echo ^-^> Generating placeholder icon...
    python -c "
import struct, zlib
def make_ico():
    # Minimal valid 32x32 ICO
    size = 32
    bmp_header = struct.pack('<IiiHHIIiiII', 40, size, -size, 1, 32, 0, size*size*4, 0, 0, 0, 0)
    pixels = b'\x1a\x1b\x1e\xff' * (size * size)
    bmp_data = bmp_header + pixels
    ico_header = struct.pack('<HHH', 0, 1, 1)
    ico_entry = struct.pack('<BBBBHHII', size, size, 0, 0, 1, 32, len(bmp_data), 22)
    with open('assets/icon.ico', 'wb') as f:
        f.write(ico_header + ico_entry + bmp_data)
    print('icon.ico created.')
make_ico()
"
)

REM ── Clean ────────────────────────────────────────────────────────────────────
echo ^-^> Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM ── PyInstaller ──────────────────────────────────────────────────────────────
echo ^-^> Running PyInstaller...
python -m PyInstaller gpg_messenger.spec --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller failed.
    exit /b 1
)

if not exist "dist\GPG Messenger\GPG Messenger.exe" (
    echo ERROR: Build failed — .exe not found.
    exit /b 1
)
echo ^-^> .exe built: dist\GPG Messenger\GPG Messenger.exe

REM ── Inno Setup installer (optional) ──────────────────────────────────────────
set INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if exist "%INNO_PATH%" (
    echo ^-^> Building installer with Inno Setup...
    "%INNO_PATH%" installer_windows.iss
    if not errorlevel 1 (
        echo ^-^> Installer built: dist\GPG-Messenger-Setup.exe
    ) else (
        echo WARNING: Inno Setup failed. Distribute dist\GPG Messenger\ folder instead.
    )
) else (
    echo NOTE: Inno Setup not found at %INNO_PATH%
    echo       Install from https://jrsoftware.org/isinfo.php to build an installer.
    echo       For now, distribute the dist\GPG Messenger\ folder as a zip.
    powershell -Command "Compress-Archive -Path 'dist\GPG Messenger' -DestinationPath 'dist\GPG-Messenger-Windows.zip' -Force"
    echo ^-^> Zipped: dist\GPG-Messenger-Windows.zip
)

echo.
echo Done.
