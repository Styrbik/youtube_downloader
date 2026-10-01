"""
Точка входа для лаунчера.
Запускает лаунчер (выбор версии) или сразу нужную версию.
"""

import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from config import get_preferred_gui

    preferred = get_preferred_gui()

    # Если пользователь уже выбрал версию — запускаем её сразу
    if preferred == "tkinter":
        launch("downloader_dark.py")
        return
    elif preferred == "qt":
        launch("downloader_qt.py")
        return

    # Иначе — показываем лаунчер (на Qt, он красивый)
    try:
        from modules import launcher_qt
        launcher_qt.run()
    except ImportError as e:
        print(f"⚠️ Qt-лаунчер не доступен: {e}")
        print("   Запускаю Tkinter-лаунчер...")
        try:
            from modules import launcher_dark
            launcher_dark.run()
        except ImportError as e2:
            print(f"⚠️ Tkinter-лаунчер тоже не доступен: {e2}")
            print("   Запускаю Qt-версию по умолчанию...")
            launch("downloader_qt.py")


def launch(script_name):
    """Запускает указанный скрипт."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)
    subprocess.Popen([sys.executable, script])
    sys.exit(0)


if __name__ == "__main__":
    main()