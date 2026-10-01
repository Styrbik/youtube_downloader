"""
Общий bootstrap для обеих версий приложения (Tkinter и PyQt6).
Выполняет:
- установку AppUserModelID (для иконки в панели задач Windows)
- определение BASE_DIR / MEIPASS
- распаковку ассетов рядом с exe
- загрузку кэша yt-dlp
"""

import os
import sys
import shutil
import ctypes


# Определяем пути (exe или скрипт)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    MEIPASS = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    MEIPASS = BASE_DIR


def _set_app_user_model_id(app_id: str):
    """Устанавливает AppUserModelID для правильной иконки в панели задач."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception as e:
        print(f"⚠️ Не удалось установить AppUserModelID: {e}")


def _unpack_assets():
    """Копирует icons/, icon.ico, CHANGELOG.md, cover.png рядом с exe при первом запуске."""
    assets = [
        ('icons', 'icons'),           # папка
        ('icon.ico', 'icon.ico'),     # файл
        ('CHANGELOG.md', 'CHANGELOG.md'),
        ('cover.png', 'cover.png'),
    ]

    for src_name, dst_name in assets:
        src = os.path.join(MEIPASS, src_name)
        dst = os.path.join(BASE_DIR, dst_name)

        if not os.path.exists(src):
            continue

        if os.path.isdir(src):
            if not os.path.isdir(dst):
                try:
                    shutil.copytree(src, dst)
                    print(f"📁 Распакована папка: {dst_name}")
                except Exception as e:
                    print(f"⚠️ Не удалось распаковать {dst_name}: {e}")
        else:
            if not os.path.exists(dst):
                try:
                    shutil.copy2(src, dst)
                    print(f"📄 Распакован файл: {dst_name}")
                except Exception as e:
                    print(f"⚠️ Не удалось распаковать {dst_name}: {e}")


def _load_ytdlp_cache():
    """Подключает кэш yt-dlp (если модуль updater доступен)."""
    try:
        from modules import updater
        updater.load_cached()
    except Exception as e:
        print(f"⚠️ Не удалось загрузить кэш yt-dlp: {e}")


def setup(app_id: str):
    """
    Полный bootstrap. Вызывать первым делом в downloader_*.py.
    
    app_id — уникальный идентификатор приложения для Windows,
             например "Styfik.YouTubeDownloader.Tk.0.4.2"
    """
    # чтобы можно было импортировать modules.*
    sys.path.insert(0, BASE_DIR)

    _set_app_user_model_id(app_id)

    # распаковка только в exe-режиме
    if getattr(sys, 'frozen', False):
        _unpack_assets()

    _load_ytdlp_cache()