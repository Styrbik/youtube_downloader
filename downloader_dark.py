import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# подключаем кэш yt-dlp ДО импорта gui_dark
try:
    from modules import updater
    updater.load_cached()
except Exception as e:
    print(f"⚠️ Не удалось загрузить кэш yt-dlp: {e}")

from modules import gui_dark


if __name__ == '__main__':
    gui_dark.run()