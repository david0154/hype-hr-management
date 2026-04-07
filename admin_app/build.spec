# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Hype HR Management Admin App
# Run: pyinstaller build.spec

import os

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('../assets/logo.png', 'assets'),
        ('serviceAccountKey.json', '.'),
    ],
    hiddenimports=[
        'firebase_admin',
        'google.cloud.firestore',
        'PIL',
        'qrcode',
        'fpdf',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='HypeHRManagement',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../assets/logo.ico',
)
