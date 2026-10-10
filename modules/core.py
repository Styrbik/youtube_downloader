import yt_dlp
import os
import re
from config import DOWNLOADS_DIR, FFMPEG_PATH

# Глобальный колбэк прогресса. GUI подставит свою функцию.
PROGRESS_CALLBACK = None

# Флаг отмены загрузки
CANCEL_FLAG = False

COOKIES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "cookies.txt"
)


def _get_cookie_opts():
    if os.path.exists(COOKIES_FILE):
        print(f"🍪 Куки из файла: {COOKIES_FILE}")
        return {'cookiefile': COOKIES_FILE}
    return {}


def cancel_download():
    """Устанавливает флаг отмены. Следующий progress_hook прервёт загрузку."""
    global CANCEL_FLAG
    CANCEL_FLAG = True

# Последний путь, куда yt-dlp сохранил файл (для точного возврата)
LAST_FILE_PATH = None


def _make_hook():
    """Создаёт хук для yt-dlp, который зовёт PROGRESS_CALLBACK."""
    def hook(d):
        global LAST_FILE_PATH, CANCEL_FLAG
        if CANCEL_FLAG:
            raise yt_dlp.utils.DownloadCancelled("Отменено пользователем")
        if d.get('status') == 'finished':
            fp = d.get('filename')
            if fp:
                LAST_FILE_PATH = fp
        if PROGRESS_CALLBACK:
            try:
                PROGRESS_CALLBACK(d)
            except Exception:
                pass
    return hook


def _make_postprocessor_hook():
    """Ловит финальный путь после постпроцессинга (когда mp4/mp3 готов)."""
    def hook(d):
        global LAST_FILE_PATH
        try:
            info = d.get('info_dict') or {}
            fp = info.get('filepath') or info.get('_filename')
            if fp:
                LAST_FILE_PATH = fp
        except Exception:
            pass
    return hook


def base_opts(output_dir):
    """Базовые опции yt-dlp с указанной папкой сохранения."""
    opts = {
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'quiet': False,
        'noprogress': False,
        'retries': 10,
        'socket_timeout': 60,
        'progress_hooks': [_make_hook()],
        'postprocessor_hooks': [_make_postprocessor_hook()],
    }
    opts.update(_get_cookie_opts())
    if os.path.exists(FFMPEG_PATH):
        opts['ffmpeg_location'] = FFMPEG_PATH
    return opts


def get_formats(url):
    """Получает список форматов."""
    opts = {
        'quiet': True,
        'no_warnings': True,
    }
    opts.update(_get_cookie_opts())
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get('title', 'video')

        # --- превьюха: берём самую крупную ---
        thumbnail = None
        thumbs = info.get('thumbnails') or []
        if thumbs:
            best = max(thumbs, key=lambda t: (t.get('width') or 0) * (t.get('height') or 0))
            thumbnail = best.get('url')
        if not thumbnail:
            thumbnail = info.get('thumbnail')

        videos = []
        for f in info.get('formats', []):
            if f.get('vcodec') != 'none' and f.get('height'):
                videos.append({
                    'id': f['format_id'],
                    'ext': f.get('ext', '?'),
                    'height': f['height'],
                    'fps': f.get('fps') or 0,
                    'filesize': f.get('filesize') or f.get('filesize_approx') or 0,
                })

        audios = []
        for f in info.get('formats', []):
            if f.get('acodec') not in (None, 'none') and f.get('vcodec') in (None, 'none') and f.get('abr'):
                audios.append({
                    'id': f['format_id'],
                    'ext': f.get('ext', '?'),
                    'abr': f.get('abr') or 0,
                    'acodec': f.get('acodec', '?').split('.')[0],
                    'filesize': f.get('filesize') or f.get('filesize_approx') or 0,
                })

        # метаданные для тегов MP3
        meta = {
            'title': title,
            'artist': info.get('artist') or info.get('uploader') or info.get('channel') or '',
            'album': info.get('album') or '',
            'upload_date': info.get('upload_date') or '',  # YYYYMMDD
            'track': info.get('track') or '',
        }

        return title, videos, audios, thumbnail, meta


def _build_outtmpl(output_dir, name_suffix, rename_if_exists):
    """Собирает шаблон имени файла с учётом суффикса и переименования."""
    base = '%(title)s'
    if name_suffix:
        base += f' [{name_suffix}]'
    if rename_if_exists:
        base += '_%(epoch)s'
    return os.path.join(output_dir, base + '.%(ext)s')


def _video_selector(fmt_id):
    """
    Селектор для видео.
    Если fmt_id — конкретный формат, берём его + лучший аудио.
    Иначе — bestvideo+bestaudio.
    """
    if fmt_id:
        return f"{fmt_id}+bestaudio/{fmt_id}/best"
    return "bestvideo+bestaudio/best"


def _build_audio_postprocessors(audio_mode, audio_bitrate, audio_codec, container):
    """
    Собирает постпроцессоры для аудио-дорожки в видео.
    audio_mode: 'best' | 'bitrate' | 'none' | 'custom'
    audio_codec: 'aac' | 'opus' | 'mp3' | None
    """
    if audio_mode == 'none':
        # без звука — выкидываем аудио
        return [{'key': 'FFmpegVideoRemuxer', 'preferedformat': container}], "bestvideo"

    pps = []

    # если нужен конкретный кодек — конвертируем
    if audio_codec in ('aac', 'opus', 'mp3'):
        pps.append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_codec,
            'preferredquality': str(audio_bitrate) if audio_bitrate else '0',
        })
    elif audio_mode == 'bitrate' and audio_bitrate:
        # битрейт без смены кодека — оставляем как есть, yt-dlp сам подберёт
        pass

    # финальный merge в нужный контейнер
    pps.append({
        'key': 'FFmpegVideoRemuxer',
        'preferedformat': container,
    })

    return pps, None


def download_video(url, format_id, output_dir, container='mp4',
                   audio_mode='best', audio_bitrate=None, audio_codec=None,
                   name_suffix="", rename_if_exists=False):
    """Скачивает видео + аудио, собирает в контейнер."""
    global LAST_FILE_PATH, CANCEL_FLAG
    LAST_FILE_PATH = None
    CANCEL_FLAG = False   # ← сбрасываем флаг

    os.makedirs(output_dir, exist_ok=True)
    opts = base_opts(output_dir)
    opts['outtmpl'] = _build_outtmpl(output_dir, name_suffix, rename_if_exists)

    # --- селектор ---
    if audio_mode == 'none':
        if format_id:
            opts['format'] = f"{format_id}/bestvideo"
        else:
            opts['format'] = "bestvideo"
    else:
        opts['format'] = _video_selector(format_id)

    # --- merge в контейнер ---
    if container in ('mp4', 'mkv', 'webm'):
        opts['merge_output_format'] = container

    # --- постпроцессоры (ТОЛЬКО для аудио-битрейта) ---
    # НИКАКИХ FFmpegExtractAudio! Это вырезает видео!
    if audio_mode == 'bitrate' and audio_bitrate:
        # yt-dlp сам подберёт аудио по битрейту через селектор
        opts['format_sort'] = [f'acodec:aac', f'abr:{audio_bitrate}']
    
    # --- качаем ---
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    return LAST_FILE_PATH


def download_audio(url, format_id, output_dir, codec='mp3', bitrate=None,
                   name_suffix="", rename_if_exists=False):
    """Скачивает аудио, конвертирует в нужный кодек, вшивает обложку."""
    global LAST_FILE_PATH, CANCEL_FLAG
    LAST_FILE_PATH = None
    CANCEL_FLAG = False   # ← сбрасываем флаг

    os.makedirs(output_dir, exist_ok=True)
    opts = base_opts(output_dir)
    opts['outtmpl'] = _build_outtmpl(output_dir, name_suffix, rename_if_exists)

    # --- селектор ---
    if format_id:
        opts['format'] = f"{format_id}/bestaudio/best"
    else:
        opts['format'] = "bestaudio/best"

    # --- постпроцессинг ---
    opts.update({
        'writethumbnail': True,
        'embedthumbnail': False,   # ← вот это
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': codec,
                'preferredquality': str(bitrate) if bitrate else '0',
            },
            {
                'key': 'FFmpegThumbnailsConvertor',
                'format': 'jpg',
                'when': 'before_dl',
            },
        ],
    })

    # --- качаем ---
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    return LAST_FILE_PATH


def unique_sorted_video(video_formats):
    """Убирает дубли видео по высоте, оставляя лучший."""
    best = {}
    for f in video_formats:
        h = f['height']
        if h not in best or f['filesize'] > best[h]['filesize']:
            best[h] = f
    return sorted(best.values(), key=lambda x: x['height'], reverse=True)


def unique_sorted_audio(audio_formats):
    """Убирает дубли аудио по битрейту, оставляя лучший."""
    seen = {}
    for f in audio_formats:
        k = int(f['abr'] or 0)
        if k not in seen or f['filesize'] > seen[k]['filesize']:
            seen[k] = f
    return sorted(seen.values(), key=lambda x: x['abr'], reverse=True)


def download_playlist(url, output_dir, mode='audio', codec='mp3',
                     container='mp4', name_suffix=""):
    """Скачивает плейлист в подпапку с нумерацией."""
    os.makedirs(output_dir, exist_ok=True)

    with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        playlist_title = info.get('title', 'playlist')

    safe_title = re.sub(r'[<>:"/\\|?*]', '_', playlist_title).strip()
    playlist_dir = os.path.join(output_dir, safe_title)
    os.makedirs(playlist_dir, exist_ok=True)

    opts = base_opts(playlist_dir)
    tmpl = '%(playlist_index)s - %(title)s'
    if name_suffix:
        tmpl += f' [{name_suffix}]'
    tmpl += '.%(ext)s'
    opts['outtmpl'] = os.path.join(playlist_dir, tmpl)

    if mode == 'audio':
        opts.update({
            'format': 'bestaudio/best',
            'writethumbnail': True,
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': codec,
                    'preferredquality': '0',
                },
                {
                    'key': 'FFmpegThumbnailsConvertor',
                    'format': 'jpg',
                    'when': 'before_dl',
                },
                {
                    'key': 'EmbedThumbnail',
                    'already_have_thumbnail': False,
                },
            ],
        })
    else:
        opts.update({
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': container,
        })

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    return playlist_dir, playlist_title
    
def search_youtube(query, max_results=15):
    """
    Ищет видео на YouTube.
    Возвращает список: [{'id', 'title', 'url', 'thumbnail', 'duration', 'uploader'}]
    """
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,      # ← быстро, только метаданные
        'force_generic_extractor': False,
    }
    opts.update(_get_cookie_opts())

    search_query = f"ytsearch{max_results}:{query}"

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(search_query, download=False)

        results = []
        entries = info.get('entries', [])
        for entry in entries:
            if not entry:
                continue
            results.append({
                'id': entry.get('id', ''),
                'title': entry.get('title', 'Без названия'),
                'url': entry.get('url') or f"https://youtube.com/watch?v={entry.get('id')}",
                'thumbnail': entry.get('thumbnail') or entry.get('thumbnails', [{}])[0].get('url', ''),
                'duration': entry.get('duration') or 0,
                'uploader': entry.get('uploader') or entry.get('channel') or '',
            })
        return results
    except Exception as e:
        print(f"⚠️ Ошибка поиска: {e}")
        return []