"""
Пасхалка: Санс из Undertale.
По URL ?sans — показывает гифку Санса внизу окна + звук.
Без масштабирования, оригинальный размер.
"""

import os
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer, QUrl, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QMovie
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput


# Ссылка на текущий экземпляр
_sans_instance = None

# Настройки
BOTTOM_MARGIN = 30       # отступ снизу (гифка выше низа окна)
SANS_DURATION = 8600     # время показа гифки (мс)
SOUND_VOLUME = 0.8       # громкость звука (0.0 - 1.0)


def show_sans(parent_window):
    """Показывает Санса внизу главного окна."""
    global _sans_instance

    if _sans_instance is not None:
        try:
            _sans_instance.restart()
            return
        except Exception:
            _sans_instance = None

    _sans_instance = SansEasterEgg(parent_window)
    _sans_instance.show()


class SansEasterEgg(QWidget):
    """
    Прозрачный виджет с гифкой Санса, прилеплен к низу окна.
    Звук играет один раз, синхронно с показом.
    """

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window

        # Прозрачный фон, ловит клики
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Звук — создаём СРАЗУ, но играем после показа
        self._player = None
        self._audio = None

        # ---------- Гифка ----------
        self.label = QLabel(self)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background: transparent;")

        gif_path = self._find_gif()

        self.movie = None
        self._original_size = (582, 156)  # fallback

        if gif_path and os.path.exists(gif_path):
            self.movie = QMovie(gif_path)
            self.movie.setCacheMode(QMovie.CacheMode.CacheAll)

            # Забираем оригинальный размер
            self.movie.jumpToFrame(0)
            pix = self.movie.currentPixmap()
            if pix.width() > 0:
                self._original_size = (pix.width(), pix.height())

            self.label.setMovie(self.movie)
            self.movie.start()
            print(f"👁️ Санс загружен: {gif_path} {self._original_size}")
        else:
            print(f"⚠️ Гифка Санса не найдена")

        # ---------- Размер и позиция ----------
        self._setup_size()

        # ---------- Автоскрытие ----------
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)
        self._hide_timer.start(SANS_DURATION)

        # ---------- Звук (запускаем чуть позже, чтобы гифка успела появиться) ----------
        QTimer.singleShot(100, self._play_sound)

        # ---------- Реакция на resize ----------
        parent_window.installEventFilter(self)

    def _find_gif(self):
        """Ищет гифку Санса."""
        from config import BASE_DIR

        candidates = [
            os.path.join(BASE_DIR, "assets", "gifs", "sans.gif"),
            os.path.join(BASE_DIR, "assets", "sans.gif"),
            os.path.join(BASE_DIR, "admin_assets", "sans.gif"),
            os.path.join(BASE_DIR, "admin_assets", "gifs", "sans.gif"),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return None

    def _find_sound(self):
        """Ищет файл звука."""
        from config import BASE_DIR

        candidates = [
            os.path.join(BASE_DIR, "assets", "sounds", "sans_voice.wav"),
            os.path.join(BASE_DIR, "assets", "sounds", "sans_voice.mp3"),
            os.path.join(BASE_DIR, "assets", "sounds", "sans.wav"),
            os.path.join(BASE_DIR, "assets", "sounds", "sans.mp3"),
            os.path.join(BASE_DIR, "admin_assets", "sounds", "sans_voice.wav"),
            os.path.join(BASE_DIR, "admin_assets", "sounds", "sans_voice.mp3"),
            os.path.join(BASE_DIR, "admin_assets", "sounds", "sans.wav"),
            os.path.join(BASE_DIR, "admin_assets", "sounds", "sans.mp3"),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return None

    def _play_sound(self):
        """
        Играет звук Санса ОДИН РАЗ.
        6 секунд — ровно столько же, сколько видна гифка.
        """
        try:
            sound_path = self._find_sound()
            if not sound_path:
                print("⚠️ Звук Санса не найден")
                return

            # Создаём плеер
            self._player = QMediaPlayer()
            self._audio = QAudioOutput()
            self._player.setAudioOutput(self._audio)
            self._audio.setVolume(SOUND_VOLUME)

            # Загружаем и играем
            self._player.setSource(QUrl.fromLocalFile(sound_path))
            self._player.play()
            print(f"🔊 Голос Санса: {sound_path} (один раз)")

        except Exception as e:
            print(f"⚠️ Звук Санса: {e}")

    def _setup_size(self):
        """Задаёт размер виджета под оригинальный размер гифки."""
        ow, oh = self._original_size
        self.setFixedSize(ow, oh)
        self.label.setFixedSize(ow, oh)
        self._reposition()

    def _reposition(self):
        """Позиционирует гифку внизу окна по центру."""
        if not self.parent_window:
            return

        parent_geo = self.parent_window.geometry()

        ow, oh = self._original_size
        w = ow
        h = oh

        # По центру по X
        x = (parent_geo.width() - w) // 2
        # Снизу с отступом
        y = parent_geo.height() - h - BOTTOM_MARGIN

        if x < 0:
            x = 0
        if y < 0:
            y = 0

        self.setGeometry(x, y, w, h)
        self.label.setGeometry(0, 0, w, h)

    def eventFilter(self, obj, event):
        """Реагируем на resize главного окна."""
        if obj is self.parent_window and event.type() == event.Type.Resize:
            QTimer.singleShot(50, self._reposition)
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        """Клик — убрать Санса."""
        print("👁️ Санс ушёл: 'okey-dokey'")
        self._fade_out()

    def _fade_out(self):
        """Плавно убираем гифку + сразу глушим звук."""
        try:
            self._hide_timer.stop()
        except Exception:
            pass

        # Останавливаем звук
        try:
            if self._player:
                self._player.stop()
        except Exception:
            pass

        # Останавливаем гифку
        try:
            if self.movie:
                self.movie.stop()
        except Exception:
            pass

        # Плавное исчезновение
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(500)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_anim.finished.connect(self._cleanup)
        self._fade_anim.start()

    def _cleanup(self):
        """Убираем ресурсы."""
        global _sans_instance
        try:
            self.hide()
            self.close()
            self.deleteLater()
        except Exception:
            pass
        _sans_instance = None

    def restart(self):
        """Перезапуск если Санс уже висит."""
        if self.movie:
            self.movie.stop()
            self.movie.start()

        # Перезапуск звука
        try:
            if self._player:
                self._player.stop()
                self._player.setPosition(0)
                self._player.play()
            else:
                self._play_sound()
        except Exception:
            self._play_sound()

        try:
            self._hide_timer.start(SANS_DURATION)
        except Exception:
            pass


def is_sans_active():
    return _sans_instance is not None and _sans_instance.isVisible()


def hide_sans():
    global _sans_instance
    if _sans_instance is not None:
        try:
            _sans_instance._fade_out()
        except Exception:
            pass