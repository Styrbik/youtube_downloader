import io
import urllib.request
from PIL import Image, ImageDraw, ImageTk

def make_icon(kind, size=24, color="#e62117"):
    """Генерирует простые иконки через Pillow."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    c = color

    if kind == "folder":
        draw.rectangle([3, 7, size-3, size-4], fill=c)
        draw.rectangle([3, 5, 12, 9], fill=c)
    elif kind == "search":
        draw.ellipse([4, 4, size-8, size-8], outline=c, width=3)
        draw.line([size-8, size-8, size-3, size-3], fill=c, width=3)
    elif kind == "download":
        draw.line([size//2, 4, size//2, size-8], fill=c, width=3)
        draw.polygon([(size//2-6, size-10), (size//2+6, size-10), (size//2, size-3)], fill=c)
        draw.line([5, size-3, size-5, size-3], fill=c, width=3)
    elif kind == "play":
        draw.polygon([(8, 5), (8, size-5), (size-5, size//2)], fill=c)
    elif kind == "music":
        draw.line([size-8, 6, size-8, size-6], fill=c, width=3)
        draw.ellipse([size-12, size-10, size-5, size-3], fill=c)
    return img


def icon_photo(kind, size=24, color="#e62117"):
    """Возвращает PhotoImage для Tkinter (нужно хранить ссылку!)."""
    return ImageTk.PhotoImage(make_icon(kind, size, color))

def _detect_letterbox(img, edge_threshold=25, min_band=6, max_scan_ratio=0.35):
    """
    Определяет заливку (letterbox/pillarbox) по резкости краёв.
    У заливки резкость низкая (размытие), у настоящего изображения — высокая.
    Возвращает (left, top, right, bottom) — что оставить.
    """
    import numpy as np

    w, h = img.size
    arr = np.asarray(img.convert("L"), dtype=np.int16)  # grayscale

    # градиент по X и Y — насколько резко меняются пиксели
    grad_x = np.abs(np.diff(arr, axis=1))  # [h, w-1]
    grad_y = np.abs(np.diff(arr, axis=0))  # [h-1, w]

    def column_sharpness(x):
        """Средняя резкость вертикальной полосы на координате x."""
        if x < 0 or x >= grad_x.shape[1]:
            return 0
        return float(grad_x[:, x].mean())

    def row_sharpness(y):
        """Средняя резкость горизонтальной полосы."""
        if y < 0 or y >= grad_y.shape[0]:
            return 0
        return float(grad_y[y, :].mean())

    # --- сканируем слева ---
    max_scan_x = int(w * max_scan_ratio)
    left = 0
    for x in range(0, max_scan_x):
        if column_sharpness(x) > edge_threshold:
            left = x
            break

    # --- справа ---
    right = w
    for x in range(w - 1, w - max_scan_x - 1, -1):
        if column_sharpness(x) > edge_threshold:
            right = x + 1
            break

    # --- сверху ---
    max_scan_y = int(h * max_scan_ratio)
    top = 0
    for y in range(0, max_scan_y):
        if row_sharpness(y) > edge_threshold:
            top = y
            break

    # --- снизу ---
    bottom = h
    for y in range(h - 1, h - max_scan_y - 1, -1):
        if row_sharpness(y) > edge_threshold:
            bottom = y + 1
            break

    # если обрезали слишком мало — не трогаем
    if right - left < min_band * 4:
        left, right = 0, w
    if bottom - top < min_band * 4:
        top, bottom = 0, h

    # если обрезали слишком много (больше 45% с каждой стороны) — не трогаем
    if left > w * 0.45 or (w - right) > w * 0.45:
        left, right = 0, w
    if top > h * 0.45 or (h - bottom) > h * 0.45:
        top, bottom = 0, h

    return left, top, right, bottom


def load_thumbnail(url, target_w=320):
    """
    Качает превьюху, убирает размытую заливку (YouTube Music),
    ресайзит, скругляет углы. Возвращает (PhotoImage, width, height) или None.
    """
    if not url:
        return None
    try:
        import io
        import urllib.request
        from PIL import Image, ImageDraw, ImageTk

        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (YouTubeDownloader)"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        orig_size = img.size

        # --- убираем размытую заливку ---
        try:
            l, t, r, b = _detect_letterbox(img)
            if (l, t, r, b) != (0, 0, orig_size[0], orig_size[1]):
                img = img.crop((l, t, r, b))
                print(f"✂️ Обрезана заливка: {orig_size} → {img.size}")
        except Exception as e:
            print(f"⚠️ Ошибка детекции заливки: {e}")

        # --- ресайз по ширине ---
        w0, h0 = img.size
        ratio = target_w / w0
        new_w = target_w
        new_h = int(h0 * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)

        # --- скругление ---
        radius = 12
        mask = Image.new("L", (new_w, new_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, new_w, new_h), radius=radius, fill=255
        )
        out = Image.new("RGBA", (new_w, new_h), (0, 0, 0, 0))
        out.paste(img, (0, 0), mask)

        photo = ImageTk.PhotoImage(out)
        return photo, new_w, new_h
    except Exception as e:
        print(f"⚠️ Не удалось загрузить превью: {e}")
        return None