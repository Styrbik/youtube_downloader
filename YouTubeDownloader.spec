# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules

PROJECT_ROOT = os.path.abspath(os.getcwd())


# ============================================================
#                    DATAS
# ============================================================
datas = [
    # ---- Основное ----
    ('icons', 'icons'),
    ('icon.ico', '.'),
    ('cover.png', '.'),
    ('CHANGELOG.md', '.'),
    ('ffmpeg.exe', '.'),
    ('version_info.txt', '.'),

    # ---- Ассеты ----
    ('assets', 'assets'),
]

if os.path.isdir('modules'):
    datas.append(('modules', 'modules'))


# ============================================================
#                    HIDDEN IMPORTS
# ============================================================
hiddenimports = [
    'config',
    'modules',
    'modules.bootstrap',
    'modules.core',
    'modules.settings',
    'modules.visual',
    'modules.embed',
    'modules.icon_manager',
    'modules.icon_maker',
    'modules.icons',
    'modules.cache',
    'modules.tray',
    'modules.sounds',
    'modules.toast',
    'modules.splash',
    'modules.updater',
    'modules.themes',
    'modules.theme_manager',
    'modules.theme_configurator',
    'modules.theme_language',
    'modules.achievements',
    'modules.holiday_fx_qt',
    'modules.background_widget',
    'modules.frost_fx_qt',
    'modules.falling_fx',
    'modules.falling_fx_qt',
    'modules.gaster_dialog',
    'modules.sans_easter_egg',
    'modules.player_qt',
    'modules.gui_qt',
    'modules.gui_dark',
    'modules.launcher_qt',
    'modules.launcher_dark',
    'modules.thumbs',

    '_overlapped',
    'asyncio',
    'asyncio.windows_events',
    'asyncio.windows_utils',
    'ctypes',
    'ctypes.wintypes',

    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',
    'PyQt6.QtMultimedia',
    'PyQt6.QtMultimediaWidgets',
    'PyQt6.sip',

    'tkinter',
    'yt_dlp',
    'mutagen',
    'mutagen.mp3',
    'mutagen.id3',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'PIL.ImageTk',
    'numpy',
    'pygame',
    'pystray',
]

hiddenimports += collect_submodules('yt_dlp')


# ============================================================
#                    ANALYSIS
# ============================================================
a = Analysis(
    ['downloader_launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)


# ============================================================
#                    EXE (onedir)
# ============================================================
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,       # ← ВАЖНО для onedir
    name='YouTubeDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon=['icon.ico'],
)


# ============================================================
#                    COLLECT (папка)
# ============================================================
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='YouTubeDownloader',
)