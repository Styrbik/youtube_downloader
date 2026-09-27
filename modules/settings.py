import json
import os
from config import CONFIG_PATH, DOWNLOADS_DIR

# Значения по умолчанию
DEFAULTS = {
    "mode": "video",
    "container": "mp4",
    "audio_codec": "aac",         # aac | opus | mp3
    "audio_mode": "best",         # best | 128 | 192 | 256 | 320 | none
    "last_format_id": None,
    "recent_urls": [],
    "output_dir": None,
    "window_geometry": "",
    "theme": "dark",
    "mark_settings": True,
    "history": [],
    "clear_thumb_cache": True,
    "auto_sort": False,
    "sort_audio_dir": "Музыка",
    "sort_video_dir": "Видео",
    "sort_archive_dir": "Архив",
    "sounds_enabled": True,
    "toasts_enabled": True,
    "preview_enabled": True,
    "animations_enabled": True,
    "embed_metadata": True,
    "check_updates": True,
    "embed_metadata": True,
    "auto_update_ytdlp": True,
    "active_icon": "classic",
    "profiles": {},
    "auto_sort": False,
    "sort_audio_dir": "Музыка",
    "sort_video_dir": "Видео",
    "sort_archive_dir": "Архив",
}

def save_profile(settings, name, profile_data):
    """Сохраняет профиль."""
    profiles = settings.get("profiles", {})
    profiles[name] = profile_data
    settings["profiles"] = profiles
    return settings


def delete_profile(settings, name):
    """Удаляет профиль."""
    profiles = settings.get("profiles", {})
    if name in profiles:
        del profiles[name]
        settings["profiles"] = profiles
    return settings

def load():
    """Загружает настройки из config.json. Если файла нет — создаёт с дефолтами."""
    if not os.path.exists(CONFIG_PATH):
        save(DEFAULTS)
        return dict(DEFAULTS)

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # Битый файл — не падаем, а пересоздаём
        save(DEFAULTS)
        return dict(DEFAULTS)

    # Дополняем недостающие ключи дефолтами
    for k, v in DEFAULTS.items():
        data.setdefault(k, v)
    return data


def save(settings):
    """Сохраняет настройки в config.json."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Не удалось сохранить настройки: {e}")


def add_recent_url(settings, url):
    """Добавляет URL в список недавних (без дублей, максимум 10)."""
    recent = settings.get("recent_urls", [])
    if url in recent:
        recent.remove(url)
    recent.insert(0, url)
    settings["recent_urls"] = recent[:10]
    return settings
    
def get_output_dir(settings):
    """Возвращает папку для сохранения: из настроек или дефолтную."""
    path = settings.get("output_dir")
    if path and os.path.isdir(path):
        return path
    return DOWNLOADS_DIR
    
def add_to_history(settings, file_path, url="", title=""):
    """Добавляет запись в историю скачанного."""
    from datetime import datetime
    entry = {
        "file": file_path,
        "url": url,
        "title": title,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    history = settings.get("history", [])
    history.insert(0, entry)
    settings["history"] = history[:50]   # максимум 50
    return settings