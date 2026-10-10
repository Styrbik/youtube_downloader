"""
Пасхалка: диалог Гастера при выборе темы Undertale.
Проигрывает видео-анимку с звуками.
"""

import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QPixmap
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QSizePolicy


def check_gaster_chance():
    """
    Проверяет, должен ли Гастер появиться.
    Возвращает True, если да.
    """
    from modules import settings as _s
    s = _s.load()

    # Шанс из конфига (по умолчанию 1%)
    chance = s.get("gaster_chance", 1)

    import random
    return random.randint(1, 100) <= chance


def show_gaster(parent=None):
    """Показывает пасхалку Гастера."""
    dlg = GasterVideoDialog(parent)
    dlg.exec()


class GasterVideoDialog(QDialog):
    """Полноэкранное видео-диалог Гастера."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("☟︎☜︎☹︎☹︎⚐︎")
        self.setStyleSheet("background-color: black;")
        # Скрыть курсор
        self.setCursor(Qt.CursorShape.BlankCursor)

        # Без рамки, поверх всего
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # ← чтобы не было в таскбаре
        )

        # Получаем размеры основного экрана
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        # Явно разворачиваем
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.showFullScreen()
        self.raise_()
        self.activateWindow()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Видео-виджет
        self.video_widget = QVideoWidget()
        layout.addWidget(self.video_widget)
        self.video_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        # Плеер
        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video_widget)

        # Путь к видео
        from config import BASE_DIR
        video_path = os.path.join(BASE_DIR, "assets", "videos", "gaster.mp4")

        if not os.path.exists(video_path):
            print(f"⚠️ Видео не найдено: {video_path}")
            # Если нет видео — закрываем
            QTimer.singleShot(500, self._close_and_mark)
            return

        # Загружаем
        self.player.setSource(QUrl.fromLocalFile(video_path))
        self.player.mediaStatusChanged.connect(self._on_status)
        self.player.play()

        # Звук — на максимум
        self.audio.setVolume(1.0)

    def _on_status(self, status):
        """Отслеживает окончание видео."""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._close_and_mark()

    def _close_and_mark(self):
        """Закрывает и помечает, что Гастер увиден."""
        try:
            from modules import settings as _s
            s = _s.load()
            _s.save(s)
        except Exception as e:
            print(f"⚠️ Не удалось сохранить gaster_seen: {e}")

        try:
            self.player.stop()
        except Exception:
            pass

        self.accept()

        # «Вылет» приложения (как в Undertale)
        import sys
        print("💀 GASTER FOUND — EXIT")
        sys.exit(0)