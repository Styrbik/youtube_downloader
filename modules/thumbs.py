"""
Кэш миниатюр для истории.
Сохраняет маленькие превью (200x130) для каждого скачанного файла.
"""

import os
import hashlib
from config import BASE_DIR


THUMBS_DIR = os.path.join(BASE_DIR, "cache", "thumbs")


def ensure_thumbs_dir():
    """Создаёт папку для превью, если её нет."""
    os.makedirs(THUMBS_DIR, exist_ok=True)


def _make_thumb_name(file_path):
    """Уникальное имя для превью по пути к файлу."""
    h = hashlib.md5(file_path.encode("utf-8")).hexdigest()[:16]
    return f"{h}.png"


def save_thumb(source_path, file_path):
    """
    Сохраняет уменьшенную копию картинки.
    source_path — исходная картинка (jpg/png/webp).
    file_path — путь к скачанному файлу (для уникального имени).
    Возвращает путь к сохранённой миниатюре или None.
    """
    if not source_path or not os.path.exists(source_path):
        return None

    try:
        from PIL import Image

        ensure_thumbs_dir()
        thumb_name = _make_thumb_name(file_path)
        thumb_path = os.path.join(THUMBS_DIR, thumb_name)

        # если уже есть — не пересоздаём
        if os.path.exists(thumb_path):
            return thumb_path

        img = Image.open(source_path).convert("RGB")

        # ресайз до 200x130 (примерно 16:10)
        img.thumbnail((200, 130), Image.LANCZOS)

        img.save(thumb_path, "PNG")
        print(f"🖼 Превью сохранено: {thumb_path}")
        return thumb_path
    except Exception as e:
        print(f"⚠️ Не удалось сохранить превью: {e}")
        return None


def get_thumb(file_path):
    """Возвращает путь к превью для файла, если оно есть."""
    thumb_name = _make_thumb_name(file_path)
    thumb_path = os.path.join(THUMBS_DIR, thumb_name)
    if os.path.exists(thumb_path):
        return thumb_path
    return None


def cleanup_orphans(history):
    """
    Удаляет превью, которых нет в истории.
    history — список записей из config.json.
    """
    ensure_thumbs_dir()

    # какие превью должны быть
    needed = set()
    for entry in history:
        fp = entry.get("file", "")
        if fp:
            needed.add(_make_thumb_name(fp))

    # что есть
    for f in os.listdir(THUMBS_DIR):
        if f.endswith(".png") and f not in needed:
            try:
                os.remove(os.path.join(THUMBS_DIR, f))
                print(f"🗑 Удалено превью: {f}")
            except Exception:
                pass