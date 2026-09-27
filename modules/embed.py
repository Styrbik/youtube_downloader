import os
from mutagen.mp3 import MP3
from mutagen.id3 import APIC
from PIL import Image

from modules.icons import _detect_letterbox


def _prepare_cover(cover_path, output_path):
    """
    Готовит обложку для вшивания:
    1. Обрезает размытую заливку.
    2. Режет до квадрата (если не квадрат).
    3. Сохраняет в JPG 95%.
    Оригинал НЕ удаляет — это делает embed_cover после вшивания.
    """
    img = Image.open(cover_path).convert("RGB")
    orig_size = img.size

    w0, h0 = img.size
    ratio = w0 / h0

    # если почти квадрат — не трогаем
    if abs(ratio - 1.0) < 0.05:
        print(f"✅ Уже квадрат {w0}×{h0} — заливки быть не может")
        if w0 > 1000:
            img = img.resize((1000, 1000), Image.LANCZOS)
        img.save(output_path, "JPEG", quality=95)
    else:
        # обрезаем заливку
        try:
            l, t, r, b = _detect_letterbox(img)
            if (l, t, r, b) != (0, 0, img.size[0], img.size[1]):
                img = img.crop((l, t, r, b))
                print(f"✂️ Обрезана заливка: {orig_size} → {img.size}")
        except Exception as e:
            print(f"⚠️ Ошибка детекции: {e}")

        # кроп до квадрата — всегда, если стороны не равны
        w, h = img.size
        if w != h:
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            img = img.crop((left, top, left + side, top + side))
            print(f"🔲 Кроп до квадрата {w}×{h} → {side}×{side}")
        else:
            print(f"✅ Идеальный квадрат {w}×{h}")

        if img.size[0] > 1000:
            img = img.resize((1000, 1000), Image.LANCZOS)

        img.save(output_path, "JPEG", quality=95)

    print(f"💾 Сохранил: {output_path} (существует: {os.path.exists(output_path)})")
    return output_path


def embed_cover(mp3_path, cover_path):
    """Готовит обложку и вшивает в MP3. Удаляет все старые APIC-теги."""
    if not os.path.exists(mp3_path) or not os.path.exists(cover_path):
        return False

    tmp_path = None
    cover_path_used = cover_path
    mime = 'image/jpeg'

    try:
        tmp_path = os.path.splitext(cover_path)[0] + "_prepared.jpg"
        _prepare_cover(cover_path, tmp_path)
        if os.path.exists(tmp_path):
            cover_path_used = tmp_path
            mime = 'image/jpeg'
        else:
            print(f"⚠️ _prepared.jpg не создан, вшиваю оригинал")
            cover_path_used = cover_path
            mime = 'image/jpeg' if cover_path.lower().endswith(('.jpg', '.jpeg')) else 'image/png'
    except Exception as e:
        print(f"⚠️ Не удалось подготовить обложку: {e}")
        cover_path_used = cover_path
        mime = 'image/jpeg' if cover_path.lower().endswith(('.jpg', '.jpeg')) else 'image/png'

    try:
        audio = MP3(mp3_path)
        if audio.tags is None:
            audio.add_tags()
        try:
            audio.tags.delall('APIC')
        except Exception:
            pass
        with open(cover_path_used, 'rb') as img:
            audio.tags.add(APIC(encoding=3, mime=mime, type=3,
                                desc='Cover', data=img.read()))
        audio.save()
        print(f"🖼 Обложка вшита в {os.path.basename(mp3_path)}")

        # обновляем дату модификации, чтобы плееры сбросили кэш
        try:
            os.utime(mp3_path, None)
            print(f"🕐 Обновлена дата файла")
        except Exception as e:
            print(f"⚠️ Не удалось обновить дату: {e}")

        # удаляем оригинал — только после успешного вшивания
        if (os.path.exists(cover_path)
                and cover_path != tmp_path
                and os.path.basename(cover_path) != "cover.png"):
            try:
                os.remove(cover_path)
                print(f"🗑 Удалён оригинал: {cover_path}")
            except Exception:
                pass

        return True
    except Exception as e:
        print(f"⚠️ Не удалось вшить обложку: {e}")
        return False
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                print(f"🗑 Удалён временный: {tmp_path}")
            except Exception:
                pass
                
def embed_metadata(mp3_path, meta):
    """
    Вшивает метаданные в MP3.
    meta = {'title': ..., 'artist': ..., 'album': ..., 'upload_date': 'YYYYMMDD', 'track': ...}
    """
    if not os.path.exists(mp3_path) or not meta:
        return False

    try:
        from mutagen.id3 import TIT2, TPE1, TALB, TDRC, TRCK

        audio = MP3(mp3_path)
        if audio.tags is None:
            audio.add_tags()

        title = meta.get('title') or ''
        artist = meta.get('artist') or ''
        album = meta.get('album') or ''
        date_raw = meta.get('upload_date') or ''
        track = meta.get('track') or ''

        # дата YYYYMMDD → YYYY-MM-DD
        if len(date_raw) == 8 and date_raw.isdigit():
            date_str = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
        else:
            date_str = date_raw

        if title:
            audio.tags.add(TIT2(encoding=3, text=title))
        if artist:
            audio.tags.add(TPE1(encoding=3, text=artist))
        if album:
            audio.tags.add(TALB(encoding=3, text=album))
        if date_str:
            audio.tags.add(TDRC(encoding=3, text=date_str))
        if track:
            audio.tags.add(TRCK(encoding=3, text=str(track)))

        audio.save()
        print(f"🏷 Метаданные вшиты: {artist} — {title}")
        return True
    except Exception as e:
        print(f"⚠️ Не удалось вшить метаданные: {e}")
        return False

def find_latest_mp3(folder):
    """Находит самый свежий MP3 в папке."""
    if not os.path.isdir(folder):
        return None
    files = [f for f in os.listdir(folder) if f.lower().endswith('.mp3')]
    if not files:
        return None
    files.sort(key=lambda x: os.path.getmtime(os.path.join(folder, x)), reverse=True)
    return os.path.join(folder, files[0])


def cleanup_temp_files(folder, keep_mp3=True):
    """Удаляет временные файлы и лишние картинки."""
    if not os.path.isdir(folder):
        return 0
    removed = 0
    for f in os.listdir(folder):
        path = os.path.join(folder, f)
        if not os.path.isfile(path):
            continue
        low = f.lower()

        if low.endswith(('.webp', '.part', '.ytdl', '.tmp')):
            try:
                os.remove(path)
                removed += 1
            except Exception:
                pass

        elif low.endswith(('.jpg', '.jpeg', '.png')):
            if low.endswith(('_prepared.jpg', '_square.jpg', '_conv.jpg')):
                try:
                    os.remove(path)
                    removed += 1
                except Exception:
                    pass
            else:
                base = os.path.splitext(path)[0]
                if os.path.exists(base + '.mp3'):
                    try:
                        os.remove(path)
                        removed += 1
                    except Exception:
                        pass
    return removed


def find_thumbnail(mp3_path):
    """Ищет thumbnail рядом с MP3."""
    base = os.path.splitext(mp3_path)[0]
    for ext in ('.webp', '.jpg', '.jpeg', '.png'):
        candidate = base + ext
        if os.path.exists(candidate):
            return candidate
    return None