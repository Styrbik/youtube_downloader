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

# Сброс админки, если запущено НЕ через admin_run.py
if "--keep-admin" not in sys.argv:
    try:
        from config import CONFIG_PATH
        import json
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            changed = False

            # 1. Сброс админ-режима
            if data.get("admin_mode"):
                data["admin_mode"] = False
                changed = True
                print("🔒 Админ-режим сброшен")

            # 2. Сброс форсированного праздника
            if data.get("admin_forced_holiday"):
                data["admin_forced_holiday"] = None
                changed = True
                print("🎄 Тестовый праздник сброшен")

            # 3. Сохраняем, если что-то изменилось
            if changed:
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Не удалось сбросить админ-режим: {e}")


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