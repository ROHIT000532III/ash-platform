from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


backend_root = Path(SPECPATH).parent

hiddenimports = collect_submodules("app") + collect_submodules("uvicorn")

a = Analysis(
    [str(backend_root / "backend_launcher.py")],
    pathex=[str(backend_root)],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
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
    name="ASHBackend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
