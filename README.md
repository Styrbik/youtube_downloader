<div align="center">

# 🎬 YouTube Downloader

**Only Tube, but fucking good**

[![Version](https://img.shields.io/badge/version-0.4.2-red)](https://github.com/Styrbik/youtube-downloader)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Красивая качалка для YouTube, YouTube Music и других платформ.
С кастомным интерфейсом, темами, плеером и праздничными эффектами.

</div>

---

## ✨ Возможности

### 🎨 Интерфейс
- Двухколоночный layout с плавными анимациями
- Кастомная шапка окна (не как у всех)
- 3 обычные темы: Тёмная, Бежевая, Красная
- **4 праздничные темы** с падающими объектами:
  - 🎃 Хэллоуин (31 октября)
  - 💀 Doomsday (21 декабря)
  - 🎄 Новый год (31 декабря)
  - 🌸 8 марта
- Менеджер иконок + генератор с GUI

### 🎵 Плеер
- Встроенный плеер для MP3
- Пауза, стоп, прогресс-бар
- Плейлист из истории

### 🎛 Качество
- Динамические кнопки качества
- Размер файла (MB / GB)
- Подтверждение для больших файлов (>5 ГБ)

### 🖼 Обложки
- Авто-обрезка заливки YouTube Music (16:9 → 1:1)
- Вшивание обложки в MP3
- Метаданные (артист, альбом, год)

### ⚙️ Настройки
- Отдельное окно с чекбоксами
- Автосортировка по папкам
- Автообновление yt-dlp
- Профили: Музыка 320, Видео 1080, Архив

### 🚀 Загрузка
- Кнопка «Отмена»
- ETA и скорость
- Поддержка плейлистов
- Дубликат-чек

---

## 🚀 Быстрый старт

### Windows (exe)
1. Скачай последний релиз из [Releases](../../releases)
2. Распакуй в любую папку
3. Запусти `YouTubeDownloader.exe`

### Из исходников
```bash
git clone https://github.com/your-username/youtube-downloader.git
cd youtube-downloader
pip install -r requirements.txt
python downloader_dark.py