"""
Менеджер иконок.
- Копирует .ico из папки icons/ в основной icon.ico (активная).
- Позволяет добавлять/удалять/генерировать иконки.
"""

import os
import shutil
from config import ICONS_DIR, ICON_PATH


def ensure_icons_dir():
    """Создаёт папку icons/, если её нет."""
    os.makedirs(ICONS_DIR, exist_ok=True)


def list_icons():
    """Возвращает список (name, path) всех .ico в папке."""
    ensure_icons_dir()
    result = []
    for f in sorted(os.listdir(ICONS_DIR)):
        if f.lower().endswith(".ico"):
            name = os.path.splitext(f)[0]
            result.append((name, os.path.join(ICONS_DIR, f)))
    return result


def get_active_icon_name():
    """Определяет, какая иконка сейчас активна (сравнивая с icon.ico)."""
    if not os.path.exists(ICON_PATH):
        return None
    try:
        with open(ICON_PATH, "rb") as f1:
            active_data = f1.read()
    except Exception:
        return None

    for name, path in list_icons():
        try:
            with open(path, "rb") as f2:
                if f2.read() == active_data:
                    return name
        except Exception:
            continue
    return None


def apply_icon(name):
    """Копирует icons/<name>.ico в основной icon.ico."""
    src = os.path.join(ICONS_DIR, f"{name}.ico")
    if not os.path.exists(src):
        return False
    try:
        shutil.copy2(src, ICON_PATH)
        print(f"🎨 Иконка применена: {name}")
        return True
    except Exception as e:
        print(f"⚠️ Не удалось применить иконку: {e}")
        return False


def add_icon(src_path, name=None):
    """Добавляет .ico в папку icons/."""
    ensure_icons_dir()
    if not os.path.exists(src_path):
        return False
    if not name:
        name = os.path.splitext(os.path.basename(src_path))[0]
    dst = os.path.join(ICONS_DIR, f"{name}.ico")
    try:
        shutil.copy2(src_path, dst)
        print(f"➕ Иконка добавлена: {name}")
        return True
    except Exception as e:
        print(f"⚠️ Не удалось добавить иконку: {e}")
        return False


def delete_icon(name):
    """Удаляет icons/<name>.ico."""
    path = os.path.join(ICONS_DIR, f"{name}.ico")
    if not os.path.exists(path):
        return False
    try:
        os.remove(path)
        print(f"🗑 Иконка удалена: {name}")
        return True
    except Exception as e:
        print(f"⚠️ Не удалось удалить иконку: {e}")
        return False


def save_generated_icon(pil_image, name):
    """Сохраняет сгенерированную PIL-иконку в icons/<name>.ico."""
    ensure_icons_dir()
    dst = os.path.join(ICONS_DIR, f"{name}.ico")
    try:
        pil_image.save(
            dst,
            format="ICO",
            sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        )
        print(f"💾 Сгенерированная иконка сохранена: {name}")
        return True
    except Exception as e:
        print(f"⚠️ Не удалось сохранить иконку: {e}")
        return False