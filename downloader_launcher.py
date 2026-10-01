"""
Точка входа для лаунчера.
Запускает лаунчер (выбор версии) или сразу нужную версию.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import bootstrap

# AppUserModelID для правильной иконки в панели задач
bootstrap.setup("Styrbik.YouTubeDownloader.Launcher.0.5.0")


def main():
    from config import get_preferred_gui

    preferred = get_preferred_gui()

    if preferred == "tkinter":
        launch_tkinter()
        return
    elif preferred == "qt":
        launch_qt()
        return

    launch_launcher()


def launch_launcher():
    """Запускает лаунчер."""
    try:
        from modules import launcher_qt
        launcher_qt.run()
    except ImportError as e:
        print(f"⚠️ Qt-лаунчер недоступен: {e}")
        try:
            from modules import launcher_dark
            launcher_dark.run()
        except ImportError as e2:
            print(f"⚠️ Tkinter-лаунчер тоже недоступен: {e2}")
            launch_qt()


def launch_tkinter():
    """Запускает Tkinter-версию."""
    from modules import gui_dark
    gui_dark.run()


def launch_qt():
    """Запускает PyQt6-версию."""
    from modules import gui_qt
    gui_qt.run()


if __name__ == "__main__":
    main()