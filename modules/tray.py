"""
Иконка в системном трее + управление окном.
"""

import threading
import os


def create_tray_icon(root_window, icon_path, on_open=None, on_quit=None):
    """
    Создаёт иконку в трее.
    Возвращает объект pystray.Icon или None.
    """
    try:
        import pystray
        from PIL import Image
    except ImportError as e:
        print(f"⚠️ pystray не установлен: {e}")
        return None

    if not os.path.exists(icon_path):
        print(f"⚠️ Иконка не найдена: {icon_path}")
        return None

    try:
        image = Image.open(icon_path).convert("RGBA")
        image = image.resize((64, 64), Image.LANCZOS)
    except Exception as e:
        print(f"⚠️ Не удалось открыть иконку: {e}")
        return None

    def _open(icon, item):
        try:
            root_window.after(0, lambda: _show_window(root_window))
            if on_open:
                root_window.after(0, on_open)
        except Exception:
            pass

    def _hide(icon, item):
        try:
            root_window.after(0, lambda: _hide_window(root_window))
        except Exception:
            pass

    def _quit(icon, item):
        try:
            icon.stop()
            if on_quit:
                root_window.after(0, on_quit)
            else:
                root_window.after(0, root_window.destroy)
        except Exception:
            pass

    menu = pystray.Menu(
        pystray.MenuItem("🎬 Открыть", _open, default=True),
        pystray.MenuItem("📥 Свернуть", _hide),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("❌ Выход", _quit),
    )

    icon = pystray.Icon(
        "YouTubeDownloader",
        image,
        "YouTube Downloader",
        menu,
    )

    thread = threading.Thread(target=icon.run, daemon=True)
    thread.start()

    return icon


def update_tray_icon(icon, icon_path):
    """Обновляет иконку трея."""
    if icon is None:
        return False
    try:
        from PIL import Image
        if not os.path.exists(icon_path):
            return False
        image = Image.open(icon_path).convert("RGBA")
        image = image.resize((64, 64), Image.LANCZOS)
        icon.icon = image
        icon.title = "YouTube Downloader"
        return True
    except Exception as e:
        print(f"⚠️ Не удалось обновить иконку трея: {e}")
        return False


def _show_window(root):
    try:
        root.deiconify()
        root.lift()
        root.attributes("-topmost", True)
        root.after(150, lambda: root.attributes("-topmost", False))
    except Exception:
        pass


def _hide_window(root):
    try:
        root.withdraw()
    except Exception:
        pass