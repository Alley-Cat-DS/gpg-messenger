# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for GPG Messenger
# Produces a single-folder app on all platforms.
# Run with: pyinstaller gpg_messenger.spec

import sys
import os

block_cipher = None

a = Analysis(
    ['gpg_messenger.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'tkinter.colorchooser',
        '_tkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy',
        'PIL', 'cv2', 'PyQt5', 'wx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GPG Messenger',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # no terminal window on Windows
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join('assets', 'icon.icns') if sys.platform == 'darwin'
         else os.path.join('assets', 'icon.ico') if sys.platform == 'win32'
         else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GPG Messenger',
)

# macOS: wrap the collected folder into a .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='GPG Messenger.app',
        icon=os.path.join('assets', 'icon.icns'),
        bundle_identifier='com.gpgmessenger.app',
        info_plist={
            'CFBundleShortVersionString': '2.0.0',
            'CFBundleVersion': '2.0.0',
            'NSHighResolutionCapable': True,
            'NSRequiresAquaSystemAppearance': False,
            'LSMinimumSystemVersion': '10.14',
            'CFBundleDisplayName': 'GPG Messenger',
        },
    )
