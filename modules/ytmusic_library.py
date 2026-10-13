"""
Работа с YouTube Music через ytmusicapi.
Получение лайкнутых треков, плейлистов и т.д.
"""

import os
import json
from config import BASE_DIR


HEADERS_PATH = os.path.join(BASE_DIR, "headers.json")


def _get_ytmusic():
    """Создаёт YTMusic-клиент с headers.json."""
    from ytmusicapi import YTMusic

    if not os.path.exists(HEADERS_PATH):
        print(f"⚠️ headers.json не найден: {HEADERS_PATH}")
        return None

    try:
        yt = YTMusic(HEADERS_PATH)
        print("✅ YTMusic подключён")
        return yt
    except Exception as e:
        print(f"⚠️ Ошибка подключения YTMusic: {e}")
        return None


def get_liked_songs(limit=500):
    """
    Возвращает список лайкнутых треков.
    Каждый трек — dict с полями:
    videoId, title, artists (str), album (str), duration (str)
    """
    yt = _get_ytmusic()
    if yt is None:
        return []

    try:
        print(f"📥 Загружаю лайкнутые (limit={limit})...")
        liked = yt.get_liked_songs(limit=limit)

        tracks = []
        for t in liked.get("tracks", []):
            artists = t.get("artists") or []
            artist_str = ", ".join(a.get("name", "") for a in artists) if artists else ""

            tracks.append({
                "videoId": t.get("videoId"),
                "title": t.get("title", "Без названия"),
                "artists": artist_str,
                "album": (t.get("album") or {}).get("name", "") if t.get("album") else "",
                "duration": t.get("duration", ""),
            })

        print(f"✅ Загружено {len(tracks)} лайкнутых треков")
        return tracks
    except Exception as e:
        print(f"⚠️ Ошибка получения лайкнутых: {e}")
        return []


def get_playlists(limit=25):
    """Возвращает список своих плейлистов."""
    yt = _get_ytmusic()
    if yt is None:
        return []

    try:
        lib = yt.get_library_playlists(limit=limit)
        result = []
        for p in lib:
            result.append({
                "playlistId": p.get("playlistId"),
                "title": p.get("title", "Без названия"),
                "count": p.get("count", 0),
            })
        return result
    except Exception as e:
        print(f"⚠️ Ошибка получения плейлистов: {e}")
        return []


def get_playlist_tracks(playlist_id, limit=500):
    """Возвращает треки плейлиста."""
    yt = _get_ytmusic()
    if yt is None:
        return []

    try:
        playlist = yt.get_playlist(playlist_id, limit=limit)
        tracks = []
        for t in playlist.get("tracks", []):
            if not t.get("videoId"):
                continue
            artists = t.get("artists") or []
            artist_str = ", ".join(a.get("name", "") for a in artists) if artists else ""

            tracks.append({
                "videoId": t.get("videoId"),
                "title": t.get("title", "Без названия"),
                "artists": artist_str,
                "album": (t.get("album") or {}).get("name", "") if t.get("album") else "",
                "duration": t.get("duration", ""),
            })
        return tracks
    except Exception as e:
        print(f"⚠️ Ошибка получения плейлиста: {e}")
        return []