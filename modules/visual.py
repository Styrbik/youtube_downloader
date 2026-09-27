from PIL import Image, ImageDraw, ImageFont
from config import COVER_PATH, GRADIENT_START, GRADIENT_END, COVER_SIZE


def _lerp(c1, c2, t):
    """Линейная интерполяция между двумя цветами."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _gradient(size, c1, c2):
    """Создаёт диагональный градиент."""
    img = Image.new('RGB', (size, size))
    px = img.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size)
            px[x, y] = _lerp(c1, c2, t)
    return img


def _rounded_mask(size, radius):
    """Маска со скруглёнными углами."""
    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size, size), radius=radius, fill=255)
    return mask


def make_cover(path=COVER_PATH):
    """Генерирует обложку для MP3."""
    size = COVER_SIZE
    grad = _gradient(size, GRADIENT_START, GRADIENT_END)
    mask = _rounded_mask(size, int(size * 0.22))

    cover = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    cover.paste(grad, (0, 0), mask)
    draw = ImageDraw.Draw(cover)

    # Треугольник Play
    cx, cy = size // 2, size // 2 - 30
    p = 110
    triangle = [(cx - p + 20, cy - p), (cx - p + 20, cy + p), (cx + p, cy)]
    draw.polygon(triangle, fill=(255, 255, 255, 255))

    # «YT» в треугольнике
    try:
        font_yt = ImageFont.truetype("arialbd.ttf", 70)
    except Exception:
        font_yt = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "YT", font=font_yt)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - 25 - tw // 2 - bbox[0], cy - th // 2 - bbox[1]),
              "YT", font=font_yt, fill=(230, 33, 23, 255))

    # Надпись MUSIC снизу
    try:
        font_music = ImageFont.truetype("arial.ttf", 34)
    except Exception:
        font_music = ImageFont.load_default()
    text = "MUSIC"
    bbox = draw.textbbox((0, 0), text, font=font_music)
    tw = bbox[2] - bbox[0]
    draw.text(((size - tw) // 2, size - 100), text, font=font_music, fill=(255, 255, 255, 255))

    cover.convert('RGB').save(path, 'PNG')
    print(f"✅ Обложка создана: {path}")
    return path