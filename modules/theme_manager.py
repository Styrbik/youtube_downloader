"""
Менеджер кастомных тем.
- Сохранение/загрузка в config.json → custom_themes
- Вычисление цветов из базовых
- Регистрация тем в THEMES
"""

import json
import os
import re

from config import CONFIG_PATH


# ============================================================
#                    ЦВЕТОВЫЕ УТИЛИТЫ
# ============================================================

def _hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _lighten(hex_color, amount):
    r, g, b = _hex_to_rgb(hex_color)
    r = int(r + (255 - r) * amount)
    g = int(g + (255 - g) * amount)
    b = int(b + (255 - b) * amount)
    return _rgb_to_hex((r, g, b))


def _darken(hex_color, amount):
    r, g, b = _hex_to_rgb(hex_color)
    r = int(r * (1 - amount))
    g = int(g * (1 - amount))
    b = int(b * (1 - amount))
    return _rgb_to_hex((r, g, b))


def build_full_theme(base_colors):
    """Из базовых (BG, ACCENT, FG) собирает полную палитру."""
    bg = base_colors.get("BG", "#1e1e1e")
    accent = base_colors.get("ACCENT", "#e62117")
    fg = base_colors.get("FG", "#e0e0e0")

    result = {
        "BG": bg,
        "BG_CARD": _lighten(bg, 0.08),
        "BG_INPUT": _lighten(bg, 0.15),
        "FG": fg,
        "FG_DIM": _darken(fg, 0.45),
        "ACCENT": accent,
        "ACCENT_HOVER": _lighten(accent, 0.15),
        "ACCENT_PRESS": _darken(accent, 0.2),
        "BORDER": _lighten(bg, 0.12),
        "BORDER_HOVER": accent,
        "DISABLED": _lighten(bg, 0.08),
        "DISABLED_FG": _darken(fg, 0.55),
    }

    # override
    for k, v in base_colors.items():
        if v:
            result[k] = v

    return result


# ============================================================
#                    CONFIG
# ============================================================

def _load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ _load_config error: {e}")
        return {}


def _save_config(data):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[_save_config] OK: {CONFIG_PATH}")
        return True
    except Exception as e:
        print(f"[_save_config] ERROR: {e}")
        return False


# ============================================================
#                    ID
# ============================================================

def _make_id(name, existing_ids):
    trans = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    }
    clean = "".join(trans.get(c.lower(), c.lower()) for c in name)
    clean = re.sub(r'[^a-z0-9]+', '_', clean).strip('_')
    if not clean:
        clean = "custom"
    base = f"custom_{clean}"
    cand = base
    n = 2
    while cand in existing_ids:
        cand = f"{base}_{n}"
        n += 1
    return cand


# ============================================================
#                    API
# ============================================================

def list_custom_themes():
    data = _load_config()
    custom = data.get("custom_themes", {})
    result = []
    for tid, tdata in custom.items():
        result.append({
            "id": tid,
            "name": tdata.get("name", tid),
            "colors": tdata.get("colors", {}),
        })
    return result


def get_custom_theme(theme_id):
    for t in list_custom_themes():
        if t["id"] == theme_id:
            return t
    return None


def save_custom_theme(name, base_colors, theme_id=None):
    data = _load_config()
    custom = data.get("custom_themes", {})

    if not theme_id:
        theme_id = _make_id(name, set(custom.keys()))

    custom[theme_id] = {
        "name": name,
        "colors": base_colors,
    }
    data["custom_themes"] = custom

    print(f"[SAVE_CUSTOM] saving theme_id={theme_id}, name={name}")

    if _save_config(data):
        return theme_id
    return None


def delete_custom_theme(theme_id):
    data = _load_config()
    custom = data.get("custom_themes", {})
    if theme_id in custom:
        del custom[theme_id]
        data["custom_themes"] = custom
        return _save_config(data)
    return False


def register_custom_themes(themes_dict):
    for t in list_custom_themes():
        full = build_full_theme(t["colors"])
        full["name"] = t["name"]
        themes_dict[t["id"]] = full