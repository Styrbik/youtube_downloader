"""
Скрипт для релиза новой версии.
Что делает:
1. Спрашивает новую версию и название сборки.
2. Обновляет APP_VERSION и APP_BUILD_NAME в config.py.
3. Добавляет шапку "## vX.Y.Z — Name" в CHANGELOG.md (если её ещё нет).
4. Пересоздаёт version_info.txt.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.py")
CHANGELOG_PATH = os.path.join(BASE_DIR, "CHANGELOG.md")


def update_config(version, build_name):
    """Обновляет APP_VERSION и APP_BUILD_NAME в config.py."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(
        r'APP_VERSION\s*=\s*"[^"]*"',
        f'APP_VERSION = "{version}"',
        content,
    )
    content = re.sub(
        r'APP_BUILD_NAME\s*=\s*"[^"]*"',
        f'APP_BUILD_NAME = "{build_name}"',
        content,
    )

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ config.py обновлён: v{version} — {build_name}")


def update_changelog(version, build_name):
    """Добавляет шапку новой версии в CHANGELOG.md."""
    if not os.path.exists(CHANGELOG_PATH):
        with open(CHANGELOG_PATH, "w", encoding="utf-8") as f:
            f.write("# Changelog\n\n")
        print("📝 CHANGELOG.md создан")

    with open(CHANGELOG_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    header = f'## v{version} — "{build_name}"\n'
    if header in content:
        print(f"⚠️ Запись для v{version} уже есть в CHANGELOG.md")
        return

    # вставляем новую запись сразу после "# Changelog\n"
    marker = "# Changelog\n"
    if marker in content:
        new_content = content.replace(
            marker,
            marker + "\n" + header + "- \n",
            1,
        )
    else:
        new_content = "# Changelog\n\n" + header + "- \n"

    with open(CHANGELOG_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ CHANGELOG.md обновлён: v{version} — {build_name}")
    print(f"   ⚠️ Не забудь дописать пункты изменений в {CHANGELOG_PATH}")


def regen_version_info():
    """Пересоздаёт version_info.txt через make_version_info.py."""
    try:
        import make_version_info
        make_version_info.main()
    except Exception as e:
        print(f"⚠️ Не удалось обновить version_info.txt: {e}")


def main():
    print("=== Релиз новой версии ===\n")

    version = input("Версия (например, 0.4.0): ").strip()
    if not version:
        print("❌ Версия не указана")
        return

    build_name = input("Название сборки (например, 'Big Update'): ").strip()
    if not build_name:
        build_name = "Release"

    print()
    update_config(version, build_name)
    update_changelog(version, build_name)
    regen_version_info()

    print("\n🚀 Готово!")
    print("1. Допиши пункты в CHANGELOG.md")
    print("2. Собери exe:")
    print("   pyinstaller --version-file=version_info.txt ...")


if __name__ == "__main__":
    main()