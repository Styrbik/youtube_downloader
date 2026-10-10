import json
import os
from config import CONFIG_PATH, DOWNLOADS_DIR

# Значения по умолчанию
DEFAULTS = {
    "mode": "video",
    "container": "mp4",
    "audio_codec": "aac",
    "audio_mode": "best",
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
    "auto_update_ytdlp": True,
    "active_icon": "classic",
    "profiles": {},
    "custom_themes": {},   # ← НОВОЕ
    "liquid_glass": False,        # ← добавить
    "liquid_opacity": 70,         # ← добавить (в процентах)
    "liquid_blur": 20,
    "admin_mode": False,
    "admin_forced_holiday": None,
    "debug_logs": False,
    "debug_ids": False,
    "debug_paths": False,
    "achievements": {},
    "used_themes": [],
    "download_counts": {"total": 0, "audio": 0, "video": 0},
    "gaster_chance": 5,
    "player_folder_audio": "",
    "player_folder_video": "",
    "player_scan_subfolders": True,
    "random_theme_on_start": False,
}


def save_profile(settings, name, profile_data):
    profiles = settings.get("profiles", {})
    profiles[name] = profile_data
    settings["profiles"] = profiles
    return settings


def delete_profile(settings, name):
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
        save(DEFAULTS)
        return dict(DEFAULTS)

    # Дополняем недостающие ключи дефолтами
    for k, v in DEFAULTS.items():
        data.setdefault(k, v)
    return data


def save(settings):
    try:
        current = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    current = json.load(f)
            except Exception:
                current = {}

        # защита: если в settings есть custom_themes — берём из settings.
        # если НЕТ — оставляем из current (файла), чтобы не потерять.
        if "custom_themes" not in settings:
            current.pop("custom_themes", None)  # уберём из копии, чтобы update не затронул
            # НО! Мы хотим СОХРАНИТЬ custom_themes из файла.
            # Значит — просто пропускаем merge для custom_themes
            pass

        # merge БЕЗ custom_themes, если его нет в settings
        settings_no_ct = {k: v for k, v in settings.items() if k != "custom_themes"}
        if "custom_themes" in settings:
            current.update(settings)
        else:
            current.update(settings_no_ct)
            # current всё ещё содержит custom_themes из файла — они сохранятся

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Не удалось сохранить настройки: {e}")


def add_recent_url(settings, url):
    recent = settings.get("recent_urls", [])
    if url in recent:
        recent.remove(url)
    recent.insert(0, url)
    settings["recent_urls"] = recent[:10]
    return settings


def get_output_dir(settings):
    path = settings.get("output_dir")
    if path and os.path.isdir(path):
        return path
    return DOWNLOADS_DIR


def add_to_history(settings, file_path, url="", title=""):
    from datetime import datetime
    entry = {
        "file": file_path,
        "url": url,
        "title": title,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    history = settings.get("history", [])
    history.insert(0, entry)
    settings["history"] = history[:50]
    return settings