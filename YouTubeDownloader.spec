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
]

# ---- assets/ (шрифты, курсоры, звуки, гифки) ----
if os.path.isdir('assets'):
    datas.append(('assets', 'assets'))


# ---- Модули (на случай, если есть не .py файлы) ----
if os.path.isdir('modules'):
    datas.append(('modules', 'modules'))


# ============================================================
#                    HIDDEN IMPORTS
# ============================================================
hiddenimports = [
    # ---- Внутренние модули ----
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
    'modules.theme_language',      # ← НОВОЕ
    'modules.achievements',
    'modules.holiday_fx_qt',
    'modules.background_widget',
    'modules.frost_fx_qt',
    'modules.falling_fx',
    'modules.falling_fx_qt',
    'modules.gaster_dialog',       # ← НОВОЕ
    'modules.sans_easter_egg',     # ← НОВОЕ
    'modules.player_qt',           # ← НОВОЕ
    'modules.gui_qt',
    'modules.gui_dark',
    'modules.launcher_qt',
    'modules.launcher_dark',

    # ---- Python встроенные ----
    '_overlapped',
    'asyncio',
    'asyncio.windows_events',
    'asyncio.windows_utils',
    'ctypes',
    'ctypes.wintypes',

    # ---- PyQt6 ----
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',
    'PyQt6.QtMultimedia',          # ← НОВОЕ (для плеера)
    'PyQt6.QtMultimediaWidgets',   # ← НОВОЕ (для QVideoWidget)
    'PyQt6.sip',

    # ---- Сторонние ----
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

# Автосбор всех подмодулей yt_dlp (для свежих экстракторов)
hiddenimports += collect_submodules('yt_dlp')


# ============================================================
#                    EXCLUDES (чтобы меньше весил)
# ============================================================
excludes = [
    # Если что-то лишнее не нужно — вписывай сюда:
    # 'matplotlib',
    # 'IPython',
    # 'pytest',
]


# ============================================================
#                    ANALYSE
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
    excludes=excludes,
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