"""
Точка входа для Tkinter-версии YouTube Downloader.
Запуск: python downloader_dark.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import bootstrap

# AppUserModelID — для правильной иконки в панели задач
bootstrap.setup("Styrbik.YouTubeDownloader.Tk.0.4.2")

from modules import gui_dark


if __name__ == '__main__':
    gui_dark.run()