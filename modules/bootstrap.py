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


def _cleanup_old_mei():
    """Удаляет старые временные папки _MEI от PyInstaller."""
    import tempfile
    import glob

    tmp = tempfile.gettempdir()
    current_mei = getattr(sys, "_MEIPASS", None)

    pattern = os.path.join(tmp, "_MEI*")
    for path in glob.glob(pattern):
        if current_mei and os.path.abspath(path) == os.path.abspath(current_mei):
            continue
        try:
            shutil.rmtree(path, ignore_errors=True)
            print(f"🧹 Удалён старый _MEI: {path}")
        except Exception:
            pass


def _set_app_user_model_id(app_id: str):
    """Устанавливает AppUserModelID для правильной иконки в панели задач."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception as e:
        print(f"⚠️ Не удалось установить AppUserModelID: {e}")


def _unpack_assets():
    """
    Копирует ассеты рядом с exe.
    Проверяет КАЖДЫЙ файл — если не хватает, докопирует.
    """
    assets = [
        ('icon.ico', 'icon.ico'),
        ('cover.png', 'cover.png'),
        ('CHANGELOG.md', 'CHANGELOG.md'),
        ('icons', 'icons'),
        ('assets', 'assets'),
    ]

    for src_name, dst_name in assets:
        src = os.path.join(MEIPASS, src_name)
        dst = os.path.join(BASE_DIR, dst_name)

        if not os.path.exists(src):
            continue

        if os.path.isdir(src):
            _copy_tree_merge(src, dst)
        else:
            if not os.path.exists(dst):
                try:
                    shutil.copy2(src, dst)
                    print(f"📄 Распакован файл: {dst_name}")
                except Exception as e:
                    print(f"⚠️ Не удалось распаковать {dst_name}: {e}")


def _copy_tree_merge(src, dst):
    """
    Рекурсивно копирует src → dst.
    Досоздаёт недостающие файлы, не трогает существующие.
    """
    os.makedirs(dst, exist_ok=True)

    for item in os.listdir(src):
        src_item = os.path.join(src, item)
        dst_item = os.path.join(dst, item)

        if os.path.isdir(src_item):
            _copy_tree_merge(src_item, dst_item)
        else:
            # Копируем только если файла нет или размер не совпадает
            need_copy = False
            if not os.path.exists(dst_item):
                need_copy = True
            else:
                try:
                    if os.path.getsize(src_item) != os.path.getsize(dst_item):
                        need_copy = True
                except Exception:
                    need_copy = True

            if need_copy:
                try:
                    shutil.copy2(src_item, dst_item)
                    print(f"📄 Докопирован: {item}")
                except Exception as e:
                    print(f"⚠️ Не удалось скопировать {item}: {e}")


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
             например "Styrbik.YouTubeDownloader.Tk.0.4.2"
    """
    # чтобы можно было импортировать modules.*
    sys.path.insert(0, BASE_DIR)

    # чистим старые _MEI (только в exe)
    if getattr(sys, "frozen", False):
        _cleanup_old_mei()

    _set_app_user_model_id(app_id)

    # распаковка только в exe-режиме
    if getattr(sys, 'frozen', False):
        _unpack_assets()

    _load_ytdlp_cache()