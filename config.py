import os
import sys

# Базовая папка (работает и для .py, и для .exe)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    MEIPASS_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    MEIPASS_DIR = BASE_DIR

# Папки и пути
DOWNLOADS_DIR = os.path.join(BASE_DIR, 'downloads')
FFMPEG_PATH = os.path.join(MEIPASS_DIR, 'ffmpeg.exe')
ICONS_DIR = os.path.join(BASE_DIR, 'icons')
ICON_PATH = os.path.join(BASE_DIR, 'icon.ico')  # активная
COVER_PATH = os.path.join(BASE_DIR, 'cover.png')
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')
CHANGELOG_PATH = os.path.join(BASE_DIR, 'CHANGELOG.md')

# Цвета градиента (для visual.py)
GRADIENT_START = (255, 40, 40)
GRADIENT_END = (150, 0, 0)

# Размеры
ICON_SIZE = 256
COVER_SIZE = 500
CHANGELOG_PATH = os.path.join(BASE_DIR, 'CHANGELOG.md')
ICONS_DIR = os.path.join(BASE_DIR, 'icons')
ICON_PATH = os.path.join(BASE_DIR, 'icon.ico')  # активная

def get_default_geometry(width=780, height=920, offset_y=60):
    """Возвращает геометрию по центру экрана, чуть ниже центра."""
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.destroy()
    x = (sw - width) // 2
    y = (sh - height) // 2 + offset_y
    if y < 0:
        y = 0
    return f"{width}x{height}+{x}+{y}"
    
def get_centered_geometry(width=780, height=920, offset_y=0):
    """
    Возвращает геометрию по центру экрана.
    offset_y — сдвиг вниз от центра (если хочется чуть ниже).
    Работает без создания Tk-окна, через WinAPI на Windows,
    и через tkinter как fallback.
    """
    sw, sh = 1920, 1080  # дефолт на случай если ничего не сработает
    try:
        if sys.platform == "win32":
            import ctypes
            user32 = ctypes.windll.user32
            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)
        else:
            import tkinter as tk
            r = tk.Tk()
            r.withdraw()
            sw = r.winfo_screenwidth()
            sh = r.winfo_screenheight()
            r.destroy()
    except Exception:
        pass

    # не даём окну быть больше экрана
    width = min(width, sw - 40)
    height = min(height, sh - 80)

    x = (sw - width) // 2
    y = (sh - height) // 2 + offset_y
    if y < 0:
        y = 0
    return f"{width}x{height}+{x}+{y}"
    
    # Версия приложения — единый источник правды
APP_VERSION = "0.4.2"
APP_BUILD_NAME = "Holiday Edition"
APP_AUTHOR = "Styrbik"
APP_DESCRIPTION = "YouTube Downloader"
APP_COPYRIGHT = "© 2026 Styrbik Corp."
APP_INTERNAL_NAME = "YouTubeDownloader"
APP_ORIGINAL_FILENAME = "YouTubeDownloader.exe"