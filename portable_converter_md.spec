# -*- mode: python ; coding: utf-8 -*-
import glob
import importlib.util
import os as _os

_magika_root = _os.path.dirname(importlib.util.find_spec('magika').origin)

# 收集 tesseract 目录下所有文件
_tess_files = []
for _root, _dirs, _files in _os.walk('tesseract'):
    for _f in _files:
        _src = _os.path.join(_root, _f)
        _dst = _os.path.relpath(_root, '.')
        _tess_files.append((_src, _dst))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('res/PortableConverterMD.ico', 'res'),
        ('res/screenshot.png', 'res'),
        ('res/icon_download.svg', 'res'),
        ('NOTICE', '.'),
        (_os.path.join(_magika_root, 'models'), 'magika/models'),
        (_os.path.join(_magika_root, 'config'), 'magika/config'),
    ] + _tess_files,
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
