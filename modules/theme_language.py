"""
Языки для тем — кастомные фразы в UI.
Undertale и Minecraft говорят на своём языке.
"""

# ============================================================
#                    UNDERTALE
# ============================================================
UNDERTALE = {
    "title": "❤️ YouTube Downloader",
    "placeholder": "бро, просто вставь ссылку",
    "status_ready": "❤️ * Вы чувствуете, что готовы скачивать",
    "status_fetching": "❤️ * Получаем души...",
    "status_found": "❤️ * found: {} Душ",
    "status_downloading": "❤️ * Скачивание, не теряй надежды",
    "status_done": "❤️ * Файл скачан, вы наполнились РЕШИМОСТЬЮ",
    "status_error": "❤️ * но никто не пришёл...",
    "status_cancel": "❤️ * ты проиграл, всё ок",
    "btn_download": "СКАЧАТЬ",
    "btn_fetch": "Скан",
    "btn_cancel": "Стоп",
    "btn_choose_dir": "Папка",
    "toast_saved": "❤️ * бро, ты смог",
    "toast_error": "💀 * Ты не можешь сдаться сейчас...",
    "playlist_empty": "❤️ * Пусто... как и в подземелье",
}

# ============================================================
#                    MINECRAFT
# ============================================================
MINECRAFT = {
    "title": "⛏️ YouTube Downloader",
    "placeholder": "это новый мод",
    "status_ready": "⛏️ Готов копать!",
    "status_fetching": "⛏️ Копаем шахты...",
    "status_found": "💎 Found {} алмаза!",
    "status_downloading": "⛏️ Копаем, следи за огурцами",
    "status_done": "✅ Достижение разблокировано: Алмазы!",
    "status_error": "💥 Крипер всё взорвал...",
    "status_cancel": "🚪 выходим из шахты...",
    "btn_download": "⛏️ КОПАТЬ",
    "btn_fetch": "🔍 СКАН",
    "btn_cancel": "🛑 СТОП",
    "btn_choose_dir": "📁 ПАПКА",
    "toast_saved": "💎 Ачивка: Майнкрафт",
    "toast_error": "💥 Бум! всё взорвалось",
    "playlist_empty": "⛏️ здесь больше нет блоков...",
}

# ============================================================
#                    DEFAULT (для других тем)
# ============================================================
DEFAULT = {
    "title": "YouTube Downloader",
    "placeholder": "https://youtube.com/watch?v=...",
    "status_ready": "Готов к работе",
    "status_fetching": "Получаю форматы...",
    "status_found": "Найдено: {}",
    "status_downloading": "Скачиваю...",
    "status_done": "✅ Готово!",
    "status_error": "Ошибка скачивания",
    "status_cancel": "⏹ Отменено",
    "btn_download": "Скачать",
    "btn_fetch": "Получить форматы",
    "btn_cancel": "Отмена",
    "btn_choose_dir": "Выбрать",
    "toast_saved": "✅ Файл сохранён",
    "toast_error": "❌ Ошибка",
    "playlist_empty": "История пуста",
}

# ============================================================
#                    API
# ============================================================
def get_language(theme_name):
    """Возвращает словарь фраз для темы."""
    if theme_name == "undertale":
        return UNDERTALE
    if theme_name == "minecraft":
        return MINECRAFT
    return DEFAULT


def t(theme_name, key, *args):
    """
    Возвращает фразу по ключу с подстановкой args.
    Пример: t("undertale", "status_found", 15) → "❤️ * found: 15 Душ"
    """
    lang = get_language(theme_name)
    phrase = lang.get(key, DEFAULT.get(key, key))
    if args:
        try:
            return phrase.format(*args)
        except Exception:
            return phrase
    return phrase