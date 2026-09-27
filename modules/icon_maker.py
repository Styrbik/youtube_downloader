"""
Процедурный генератор иконок.
Рисует иконку по параметрам: стиль, цвет, форма, текст, скругление.
Экспорт в PNG и ICO.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont


# ===== Пресеты цветов =====
COLOR_PRESETS = {
    "red":     ((255, 40, 40), (150, 0, 0)),
    "blue":    ((60, 130, 255), (20, 60, 180)),
    "green":   ((80, 220, 120), (20, 130, 60)),
    "purple":  ((180, 80, 255), (90, 20, 160)),
    "orange":  ((255, 160, 60), (200, 80, 20)),
    "dark":    ((60, 60, 60), (20, 20, 20)),
}

# ===== Шрифты =====
FONT_PATHS = [
    "arialbd.ttf",
    "arial.ttf",
    "seguisb.ttf",
    "segoeuib.ttf",
]


def _load_font(size):
    """Пытается загрузить жирный шрифт."""
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _lerp(c1, c2, t):
    """Линейная интерполяция между двумя цветами."""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _make_gradient(size, c1, c2, style="diagonal"):
    """Создаёт градиент."""
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        for x in range(size):
            if style == "diagonal":
                t = (x + y) / (2 * size)
            elif style == "radial":
                dx = x - size / 2
                dy = y - size / 2
                d = math.sqrt(dx * dx + dy * dy)
                t = min(1.0, d / (size * 0.7))
            else:
                t = y / size
            px[x, y] = _lerp(c1, c2, t)
    return img


def _make_rounded_mask(size, radius):
    """Создаёт маску со скруглёнными углами."""
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size, size), radius=radius, fill=255
    )
    return mask


def _draw_shape(draw, size, shape, color):
    """Рисует форму в центре иконки."""
    cx, cy = size // 2, size // 2 - size // 14
    s = size // 4  # размер фигуры

    if shape == "triangle":
        points = [
            (cx - s + s // 3, cy - s),
            (cx - s + s // 3, cy + s),
            (cx + s, cy),
        ]
        draw.polygon(points, fill=color)
    elif shape == "circle":
        draw.ellipse([cx - s, cy - s, cx + s, cy + s], fill=color)
    elif shape == "square":
        draw.rectangle([cx - s, cy - s, cx + s, cy + s], fill=color)
    elif shape == "hexagon":
        pts = []
        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 2
            pts.append((cx + s * math.cos(angle), cy + s * math.sin(angle)))
        draw.polygon(pts, fill=color)
    elif shape == "play":
        # только треугольник play (как сейчас)
        points = [
            (cx - s + s // 3, cy - s),
            (cx - s + s // 3, cy + s),
            (cx + s, cy),
        ]
        draw.polygon(points, fill=color)


def _draw_text(draw, size, text, color):
    """Рисует текст в нижней части иконки."""
    if not text:
        return
    font = _load_font(size // 8)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (size - tw) // 2
    y = size - size // 4 - th // 2
    draw.text((x - bbox[0], y - bbox[1]), text, font=font, fill=color)


def make_icon(
    size=256,
    style="gradient",       # flat | gradient | neon | dark
    color_preset="red",     # ключ из COLOR_PRESETS
    custom_colors=None,     # ((r,g,b), (r,g,b)) — перебивает preset
    shape="triangle",       # triangle | circle | square | hexagon | play
    shape_color=(255, 255, 255),
    text="",
    text_color=(255, 255, 255),
    radius_percent=22,      # 0-30
    gradient_style="diagonal",  # diagonal | radial | vertical
):
    """Возвращает PIL.Image с иконкой."""
    radius = int(size * radius_percent / 100)

    # --- фон ---
    if custom_colors:
        c1, c2 = custom_colors
    else:
        c1, c2 = COLOR_PRESETS.get(color_preset, COLOR_PRESETS["red"])

    if style == "flat":
        bg = Image.new("RGB", (size, size), c1)
    elif style == "neon":
        bg = _make_gradient(size, c1, (0, 0, 0), style="radial")
    elif style == "dark":
        bg = _make_gradient(size, (40, 40, 40), (10, 10, 10))
    else:  # gradient
        bg = _make_gradient(size, c1, c2, style=gradient_style)

    # --- маска ---
    mask = _make_rounded_mask(size, radius)

    # --- иконка ---
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    icon.paste(bg, (0, 0), mask)

    draw = ImageDraw.Draw(icon)

    # --- форма ---
    _draw_shape(draw, size, shape, shape_color)

    # --- текст ---
    _draw_text(draw, size, text, text_color)

    return icon


def save_icon(icon, png_path=None, ico_path=None):
    """Сохраняет иконку в PNG и ICO."""
    if png_path:
        icon.save(png_path, "PNG")
        print(f"✅ PNG сохранён: {png_path}")

    if ico_path:
        icon.save(
            ico_path,
            format="ICO",
            sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
        print(f"✅ ICO сохранён: {ico_path}")


def preview(icon, max_size=180):
    """Возвращает уменьшенную копию для превью в Tkinter."""
    return icon.resize((max_size, max_size), Image.LANCZOS)