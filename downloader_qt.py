"""
Точка входа для PyQt6-версии YouTube Downloader.
Запуск: python downloader_qt.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import bootstrap

# AppUserModelID — для правильной иконки в панели задач
bootstrap.setup("Styrbik.YouTubeDownloader.Qt.0.5.0")

# запускаем PyQt6-версию
try:
    from modules import gui_qt
    if __name__ == '__main__':
        gui_qt.run()
except ImportError as e:
    print(f"❌ Не удалось импортировать gui_qt: {e}")
    print("   Убедись, что модуль modules/gui_qt.py существует.")
    sys.exit(1)