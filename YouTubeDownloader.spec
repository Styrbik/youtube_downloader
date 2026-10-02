# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['downloader_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('icons', 'icons'), ('icon.ico', '.'), ('CHANGELOG.md', '.'), ('cover.png', '.'), ('ffmpeg.exe', '.')],
    hiddenimports=['PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui', 'tkinter', 'yt_dlp', 'mutagen', 'PIL', 'numpy', 'pygame'],
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
    name='YouTubeDownloader',
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
    version='version_info.txt',
    icon=['icon.ico'],
)
