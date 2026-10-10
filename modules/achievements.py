"""
Система достижений YouTube Downloader.
"""

from datetime import datetime
import json
import os


# ============================================================
#                    СПИСОК ДОСТИЖЕНИЙ
# ============================================================
ACHIEVEMENTS = {
    # 📥 Скачивание
    "first_download": {
        "name": "🥉 Первый шаг",
        "desc": "Скачай первое видео",
        "category": "download",
        "target": 1,
    },
    "ten_downloads": {
        "name": "🥈 Коллекционер",
        "desc": "Скачай 10 видео",
        "category": "download",
        "target": 10,
    },
    "fifty_downloads": {
        "name": "🥇 Мастер",
        "desc": "Скачай 50 видео",
        "category": "download",
        "target": 50,
    },
    "hundred_downloads": {
        "name": "💎 Легенда",
        "desc": "Скачай 100 видео",
        "category": "download",
        "target": 100,
    },
    "five_hundred_downloads": {
        "name": "👑 Бог",
        "desc": "Скачай 500 видео",
        "category": "download",
        "target": 500,
    },

    # 🎵 Аудио
    "ten_audio": {
        "name": "🎵 Меломан",
        "desc": "Скачай 10 MP3",
        "category": "audio",
        "target": 10,
    },
    "fifty_audio": {
        "name": "🎧 Аудиофил",
        "desc": "Скачай 50 MP3",
        "category": "audio",
        "target": 50,
    },
    "bitrate_320": {
        "name": "🎤 320 kbps",
        "desc": "Скачай в 320 kbps",
        "category": "audio",
        "target": 1,
    },

    # 🎬 Видео
    "ten_video": {
        "name": "📺 Киноман",
        "desc": "Скачай 10 видео",
        "category": "video",
        "target": 10,
    },
    "quality_4k": {
        "name": "🎬 4K",
        "desc": "Скачай 4K видео",
        "category": "video",
        "target": 1,
    },
    "quality_1080": {
        "name": "🎥 1080p",
        "desc": "Скачай 1080p видео",
        "category": "video",
        "target": 1,
    },

    # 🎨 Темы
    "five_themes": {
        "name": "🎨 Художник",
        "desc": "Используй 5 разных тем",
        "category": "theme",
        "target": 5,
    },
    "twenty_themes": {
        "name": "🌈 Радуга",
        "desc": "Используй 20 разных тем",
        "category": "theme",
        "target": 20,
    },
    "frostmourne": {
        "name": "❄️ Король-лич",
        "desc": "Используй тему Frostmourne",
        "category": "theme",
        "target": 1,
    },

    # 🎄 Праздники
    "halloween": {
        "name": "🎃 Хэллоуин",
        "desc": "Скачай в Хэллоуин",
        "category": "holiday",
        "target": 1,
    },
    "newyear": {
        "name": "🎄 Новый год",
        "desc": "Скачай в Новый год",
        "category": "holiday",
        "target": 1,
    },
    "doomsday": {
        "name": "💀 Doomsday",
        "desc": "Скачай в Doomsday",
        "category": "holiday",
        "target": 1,
    },

    # ⏰ Время
    "night_owl": {
        "name": "🌙 Ночной",
        "desc": "Скачай после 23:00",
        "category": "time",
        "target": 1,
    },
    "early_bird": {
        "name": "☀️ Ранняя птичка",
        "desc": "Скачай до 6:00",
        "category": "time",
        "target": 1,
    },

    # 🎮 Секретные
    "admin": {
        "name": "🎤 «К чёрту людей!»",
        "desc": "Открой админку",
        "category": "secret",
        "target": 1,
    },
    "frostmourne_taken": {
        "name": "⚔️ Взял Фростморн",
        "desc": "Нажми «Взять Фростморн»",
        "category": "secret",
        "target": 1,
    },
    "sans_seen": {
        "name": "👁️ Увидел Санса",
        "desc": "чел, я тут",
        "category": "secret",
        "target": 1,
    },
    "gaster_seen": {
        "name": "💀 Гастер найден",
        "desc": """✋︎🕯︎💣︎ ☟︎☜︎☼︎☜︎☞︎✋︎☠︎👎︎ 💣︎☜︎""",
        "category": "secret",
        "target": 1,
    },
}


# ============================================================
#                    ПРОГРЕСС
# ============================================================
def _get_progress(settings):
    """Возвращает словарь прогресса."""
    return settings.get("achievements", {})


def get_progress(settings, ach_id):
    """Возвращает прогресс достижения (число)."""
    progress = _get_progress(settings)
    return progress.get(ach_id, 0)


def is_unlocked(settings, ach_id):
    """Открыто ли достижение?"""
    ach = ACHIEVEMENTS.get(ach_id)
    if not ach:
        return False
    return get_progress(settings, ach_id) >= ach["target"]


def get_unlocked_count(settings):
    """Сколько достижений открыто."""
    count = 0
    for ach_id in ACHIEVEMENTS:
        if is_unlocked(settings, ach_id):
            count += 1
    return count


def get_total_count():
    """Всего достижений."""
    return len(ACHIEVEMENTS)


# ============================================================
#                    РАЗБЛОКИРОВКА
# ============================================================
def unlock(settings, ach_id, value=None):
    """
    Разблокирует достижение (или увеличивает прогресс).
    Возвращает True, если достижение только что открылось.
    """
    if ach_id not in ACHIEVEMENTS:
        return False

    ach = ACHIEVEMENTS[ach_id]
    progress = _get_progress(settings)

    old_value = progress.get(ach_id, 0)
    was_unlocked = old_value >= ach["target"]

    if value is not None:
        # установить конкретное значение (например, счётчик)
        new_value = max(old_value, value)
    else:
        # увеличить на 1
        new_value = old_value + 1

    progress[ach_id] = new_value
    settings["achievements"] = progress

    is_now_unlocked = new_value >= ach["target"]

    # вернуть True, если только что открылось
    return is_now_unlocked and not was_unlocked


def reset_all(settings):
    """Сбрасывает все достижения."""
    settings["achievements"] = {}
    settings["used_themes"] = []  # ← добавить
    return settings


# ============================================================
#                    ИСТОРИЯ ТЕМ
# ============================================================
def track_theme(settings, theme_name):
    """Отслеживает использование темы."""
    used = settings.get("used_themes", [])
    if theme_name not in used:
        used.append(theme_name)
        settings["used_themes"] = used
        print(f"🎨 Тема засчитана: {theme_name} (всего: {len(used)})")

    count = len(used)
    unlocked = []
    if unlock(settings, "five_themes", count):
        unlocked.append("five_themes")
    if unlock(settings, "twenty_themes", count):
        unlocked.append("twenty_themes")

    if theme_name == "frostmourne":
        if unlock(settings, "frostmourne"):
            unlocked.append("frostmourne")

    return unlocked

# ============================================================
#                    ИСТОРИЯ СКАЧИВАНИЙ
# ============================================================
def track_download(settings, fmt, mode):
    """
    Отслеживает скачивание.
    fmt — формат (dict с height, abr, filesize)
    mode — 'audio' / 'video'
    """
    unlocked = []

    # отдельный счётчик (не зависит от history[:50])
    counts = settings.get("download_counts", {})
    counts["total"] = counts.get("total", 0) + 1
    if mode == "audio":
        counts["audio"] = counts.get("audio", 0) + 1
    else:
        counts["video"] = counts.get("video", 0) + 1
    settings["download_counts"] = counts

    total = counts["total"]
    audio_count = counts.get("audio", 0)
    video_count = counts.get("video", 0)

    if unlock(settings, "first_download", total):
        unlocked.append("first_download")
    if unlock(settings, "ten_downloads", total):
        unlocked.append("ten_downloads")
    if unlock(settings, "fifty_downloads", total):
        unlocked.append("fifty_downloads")
    if unlock(settings, "hundred_downloads", total):
        unlocked.append("hundred_downloads")
    if unlock(settings, "five_hundred_downloads", total):
        unlocked.append("five_hundred_downloads")

    if mode == "audio":
        if unlock(settings, "ten_audio", audio_count):
            unlocked.append("ten_audio")
        if unlock(settings, "fifty_audio", audio_count):
            unlocked.append("fifty_audio")

        abr = fmt.get("abr") or 0
        if abr >= 320:
            if unlock(settings, "bitrate_320"):
                unlocked.append("bitrate_320")

    if mode == "video":
        if unlock(settings, "ten_video", video_count):
            unlocked.append("ten_video")

        height = fmt.get("height") or 0
        if height >= 2160:
            if unlock(settings, "quality_4k"):
                unlocked.append("quality_4k")
        elif height >= 1080:
            if unlock(settings, "quality_1080"):
                unlocked.append("quality_1080")

    now = datetime.now()
    if now.hour >= 23 or now.hour < 1:
        if unlock(settings, "night_owl"):
            unlocked.append("night_owl")
    if now.hour < 6:
        if unlock(settings, "early_bird"):
            unlocked.append("early_bird")

    if now.month == 10 and now.day == 31:
        if unlock(settings, "halloween"):
            unlocked.append("halloween")
    if now.month == 12 and now.day == 31:
        if unlock(settings, "newyear"):
            unlocked.append("newyear")
    if now.month == 12 and now.day == 21:
        if unlock(settings, "doomsday"):
            unlocked.append("doomsday")

    return unlocked


# ============================================================
#                    СЕКРЕТНЫЕ
# ============================================================
def track_admin(settings):
    """Отслеживает открытие админки."""
    unlocked = []
    if unlock(settings, "admin"):
        unlocked.append("admin")
    return unlocked


def track_frostmourne_taken(settings):
    """Отслеживает нажатие «Взять Фростморн»."""
    unlocked = []
    if unlock(settings, "frostmourne_taken"):
        unlocked.append("frostmourne_taken")
    return unlocked
    
def track_sans_seen(settings):
    """Отслеживает, что игрок увидел Санса."""
    unlocked = []
    if unlock(settings, "sans_seen"):
        unlocked.append("sans_seen")
    return unlocked


def track_gaster_seen(settings):
    """Отслеживает, что игрок увидел Гастера."""
    unlocked = []
    if unlock(settings, "gaster_seen"):
        unlocked.append("gaster_seen")
    return unlocked