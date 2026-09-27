"""
Автообновление yt-dlp.
Качает свежий .whl с PyPI, распаковывает в %APPDATA%/YouTubeDownloader/yt_dlp_cache.
При старте подключает кэш через sys.path, если там что-то есть.
"""

import os
import sys
import json
import zipfile
import urllib.request
import tempfile


def get_cache_dir():
    """Папка для кэша yt-dlp."""
    appdata = os.environ.get("APPDATA") or tempfile.gettempdir()
    path = os.path.join(appdata, "YouTubeDownloader", "yt_dlp_cache")
    os.makedirs(path, exist_ok=True)
    return path


def get_current_version():
    """Версия yt_dlp, которая сейчас загружена."""
    try:
        import yt_dlp
        try:
            from yt_dlp.version import __version__
            return __version__
        except Exception:
            pass
        return getattr(yt_dlp.version, "__version__", "unknown")
    except Exception as e:
        print(f"⚠️ Не могу получить версию yt_dlp: {e}")
        return "unknown"


def get_latest_version():
    """Последняя версия yt-dlp на PyPI."""
    try:
        url = "https://pypi.org/pypi/yt-dlp/json"
        req = urllib.request.Request(url, headers={"User-Agent": "YTDownloader"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["info"]["version"]
    except Exception as e:
        print(f"⚠️ Не удалось получить версию с PyPI: {e}")
        return None


def download_ytdlp(version):
    """Качает .whl yt-dlp и распаковывает в кэш."""
    try:
        url = f"https://pypi.org/pypi/yt-dlp/{version}/json"
        req = urllib.request.Request(url, headers={"User-Agent": "YTDownloader"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        wheel_url = None
        for file_info in data["urls"]:
            if file_info["filename"].endswith(".whl"):
                wheel_url = file_info["url"]
                break

        if not wheel_url:
            print("⚠️ Не найден .whl yt-dlp")
            return False

        cache_dir = get_cache_dir()
        tmp_whl = os.path.join(tempfile.gettempdir(), f"yt_dlp_{version}.whl")

        print(f"⬇️ Качаю yt-dlp {version}...")
        urllib.request.urlretrieve(wheel_url, tmp_whl)

        with zipfile.ZipFile(tmp_whl, "r") as z:
            z.extractall(cache_dir)

        try:
            os.remove(tmp_whl)
        except Exception:
            pass

        print(f"✅ yt-dlp {version} распакован в {cache_dir}")
        return True
    except Exception as e:
        print(f"⚠️ Ошибка скачивания yt-dlp: {e}")
        return False


def check_and_update(silent=True):
    """
    Проверяет и обновляет yt-dlp.
    Возвращает True, если обновление скачано.
    """
    current = get_current_version()
    latest = get_latest_version()

    print(f"🔍 Текущая версия yt-dlp: {current}")
    print(f"🔍 Последняя на PyPI: {latest}")

    if not latest:
        return False

    # нормализуем версии (2026.8.19 == 2026.08.19)
    def _normalize(v):
        try:
            return tuple(int(p) for p in v.split("."))
        except Exception:
            return v

    if _normalize(current) == _normalize(latest):
        print(f"✅ Уже актуально ({current})")
        return False

    print(f"📦 Обновление: {current} → {latest}")
    return download_ytdlp(latest)


def load_cached():
    """
    Подключает кэш yt_dlp в sys.path, если он есть.
    Вызывается ДО import yt_dlp.
    """
    cache_dir = get_cache_dir()
    print(f"🔍 Проверяю кэш: {cache_dir}")
    if not os.path.isdir(cache_dir):
        print(f"❌ Кэш не найден")
        return False

    ytdlp_dir = os.path.join(cache_dir, "yt_dlp")
    print(f"🔍 yt_dlp в кэше: {ytdlp_dir} (exists={os.path.isdir(ytdlp_dir)})")
    if not os.path.isdir(ytdlp_dir):
        print(f"❌ yt_dlp не найден в кэше")
        return False

    if cache_dir in sys.path:
        sys.path.remove(cache_dir)
    sys.path.insert(0, cache_dir)
    print(f"📦 Подключён кэш yt-dlp: {cache_dir}")
    return True