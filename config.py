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
    
def get_active_icon_path():
    """Возвращает путь к активной иконке."""
    try:
        import json
        config_path = os.path.join(BASE_DIR, 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            active = data.get("active_icon", "classic")
            icon = os.path.join(ICONS_DIR, f"{active}.ico")
            if os.path.exists(icon):
                return icon
    except Exception as e:
        print(f"⚠️ Не удалось получить активную иконку: {e}")
    return ICON_PATH
    
    # Версия приложения — единый источник правды
APP_VERSION = "0.5.0"
APP_BUILD_NAME = "Qt Edition"
APP_AUTHOR = "Styrbik"
APP_DESCRIPTION = "YouTube Downloader"
APP_COPYRIGHT = "© 2026 Styrbik Corp."
APP_INTERNAL_NAME = "YouTubeDownloader"
APP_ORIGINAL_FILENAME = "YouTubeDownloader.exe"

def get_preferred_gui():
    """
    Возвращает выбранную версию GUI: 'tkinter', 'qt' или None.
    None — значит, пользователь ещё не выбирал (показать лаунчер).
    """
    try:
        import json
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("preferred_gui", None)
    except Exception as e:
        print(f"⚠️ Не удалось прочитать preferred_gui: {e}")
    return None


def set_preferred_gui(name):
    """
    Записывает выбранную версию GUI в config.json.
    name: 'tkinter' | 'qt' | None (None — сбросить выбор)
    """
    try:
        import json
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}
        data["preferred_gui"] = name
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ preferred_gui = {name}")
        return True
    except Exception as e:
        print(f"⚠️ Не удалось записать preferred_gui: {e}")
        return False