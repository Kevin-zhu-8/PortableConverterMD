# -*- mode: python ; coding: utf-8 -*-
import importlib.util
import os as _os

_magika_root = _os.path.dirname(importlib.util.find_spec('magika').origin)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('res/PortableConverterMD.ico', 'res'),
        ('res/screenshot.png', 'res'),
        ('res/icon_download.svg', 'res'),
        ('tesseract', 'tesseract'),
        ('NOTICE', '.'),
        (_os.path.join(_magika_root, 'models'), 'magika/models'),
        (_os.path.join(_magika_root, 'config'), 'magika/config'),
    ],
    hiddenimports=['markitdown', 'markitdown._markitdown', 'magika', 'pytesseract', 'PIL'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numba', 'scipy', 'cv2', 'notebook', 'ipykernel'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PortableConverterMD',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='res/PortableConverterMD.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PortableConverterMD',
)
