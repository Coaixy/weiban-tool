# -*- mode: python ; coding: utf-8 -*-
import ddddocr
ddddocrDir = os.path.dirname(ddddocr.__file__)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        (os.path.join(ddddocrDir, 'common.onnx'), 'ddddocr'),
        (os.path.join(ddddocrDir, 'common_det.onnx'), 'ddddocr'),
        (os.path.join(ddddocrDir, 'common_old.onnx'), 'ddddocr'),
    ],
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
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)