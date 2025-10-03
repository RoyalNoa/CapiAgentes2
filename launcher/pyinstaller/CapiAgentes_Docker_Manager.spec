# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path.cwd().parent
APP_SRC = ROOT / 'src' / 'launcher_app' / 'app.py'
ASSETS_DIR = ROOT / 'assets'


a = Analysis(
    [str(APP_SRC)],
    pathex=[],
    binaries=[],
    datas=[(str(ASSETS_DIR), 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CapiLauncher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    icon=str(ASSETS_DIR / "cocoCapi.ico"),
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

