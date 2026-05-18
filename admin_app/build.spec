# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Hype HR Management Admin App
# Run: pyinstaller build.spec

import os

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('../logo.png', '.'),
        ('hype-hr-firebase-adminsdk-fbsvc-69b24d697e.json', '.'),
    ],
    hiddenimports=[
        'firebase_admin',
        'firebase_admin.auth',
        'firebase_admin.credentials',
        'firebase_admin.db',
        'firebase_admin.firestore',
        'firebase_admin.storage',
        'google.cloud',
        'google.cloud.firestore',
        'google.cloud.firestore_v1',
        'google.cloud.firestore_v1.base_collection',
        'google.api_core',
        'google.auth',
        'google.auth.transport',
        'google.auth.transport.requests',
        'google.cloud.storage',
        'PIL',
        'PIL.Image',
        'qrcode',
        'fpdf',
        'fpdf.fpdf',
        'requests',
        'cryptography',
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
    icon='logo.ico',
)
