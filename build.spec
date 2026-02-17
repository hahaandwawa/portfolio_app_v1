# PyInstaller spec for Portfolio App backend. Run from repo root: pyinstaller build.spec
# Produces dist/backend/backend (executable) for use inside Electron resources.

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Ensure uvicorn and app are fully collected (string-based uvicorn.run('src.app.main:app') is not traced)
uvicorn_hidden = [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
]
src_hidden = collect_submodules('src')
hidden_imports = uvicorn_hidden + src_hidden + [
    'fastapi',
    'yfinance',
    'httpx',
    'multipart',
]

a = Analysis(
    ['entrypoint.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No terminal window on macOS
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# One-file output: single executable. We copy it to electron/resources/backend/backend
# Build from repo root: pyinstaller build.spec
# Output: dist/backend (single file)
