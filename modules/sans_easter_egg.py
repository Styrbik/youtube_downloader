"""
Пасхалка: три звонка.
1. Санс #1 (гифка sans.gif + звук sans.mp3)
2. Санс #2 (видео sans_call.mp4, взрыв встроен)
3. Папирус (видео papyrus_call.mp4)
"""

import os
import random
from PyQt6.QtWidgets import QWidget, QLabel, QApplication
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QMovie
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


_sans_instance = None

# Настройки
BOTTOM_MARGIN = 30
RINGTONE_DURATION = 1500

# Паузы между звонками
PAUSE_BEFORE_SANS_2 = 7000     # после Санса #1
PAUSE_BEFORE_PAPYRUS = 4000    # после Санса #2

# Имена файлов (без расширения)
RINGTONE_NAME = "phone_ring"    # рингтон
SANS_GIF_NAME = "sans"          # гифка Санса #1
SANS_SOUND_NAME = "sans"        # звук Санса #1
SANS_VIDEO_NAME = "sans_call"   # видео Санса #2
PAPYRUS_VIDEO_NAME = "papyrus_call"  # видео Папируса


def show_sans(parent_window):
    """Запускает сценку с тремя звонками."""
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
    Сценка:
      1. Рингтон → Санс #1 (гифка + звук)
      2. Пауза 10 сек
      3. Рингтон → Санс #2 (видео sans_call, взрыв)
      4. Пауза 10 сек
      5. Рингтон → Папирус (видео papyrus_call)
      6. Конец
    """

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Медиа
        self._sound_player = None
        self._sound_audio = None
        self._video_player = None
        self._video_audio = None
        self._video_widget = None
        self._gif_movie = None
        self._gif_label = None

        # Текущий воспроизводимый звук (для stop)
        self._current_sound = None

        self._setup_ui()
        QTimer.singleShot(100, self._phase_1_ringtone)

    # ============================================================
    #                    UI
    # ============================================================
    def _setup_ui(self):
        from PyQt6.QtWidgets import QVBoxLayout

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Гифка (Санс #1)
        self._gif_label = QLabel(self)
        self._gif_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._gif_label.setStyleSheet("background: transparent;")
        self._gif_label.setVisible(False)
        layout.addWidget(self._gif_label)

        # Видео (Санс #2 и Папирус)
        self._video_widget = QVideoWidget(self)
        self._video_widget.setMinimumHeight(0)
        self._video_widget.setVisible(False)
        layout.addWidget(self._video_widget)

        self.setFixedSize(582, 156)
        self._reposition()

        if self.parent_window:
            self.parent_window.installEventFilter(self)

    def _reposition(self):
        if not self.parent_window:
            return
        parent_geo = self.parent_window.geometry()
        w = self.width()
        h = self.height()
        x = (parent_geo.width() - w) // 2
        y = parent_geo.height() - h - BOTTOM_MARGIN
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        self.setGeometry(x, y, w, h)

    def eventFilter(self, obj, event):
        if obj is self.parent_window and event.type() == event.Type.Resize:
            QTimer.singleShot(50, self._reposition)
        return super().eventFilter(obj, event)

    # ============================================================
    #                    ФАЗА 1: РИНГТОН #1
    # ============================================================
    def _phase_1_ringtone(self):
        print("📞 Звонок #1: рингтон")
        ringtone_path = self._find_sound(RINGTONE_NAME)
        if not ringtone_path:
            print("⚠️ Рингтон не найден, пропускаю")
            self._phase_2_sans_1()
            return
        self._play_sound_once(ringtone_path)
        QTimer.singleShot(RINGTONE_DURATION, self._phase_2_sans_1)

    # ============================================================
    #                    ФАЗА 2: САНС #1 (ГИФКА + ЗВУК)
    # ============================================================
    def _phase_2_sans_1(self):
        print("👁 Звонок #1: Санс (гифка + звук)")
        gif_path = self._find_gif(SANS_GIF_NAME)
        if not gif_path:
            print(f"⚠️ Гифка '{SANS_GIF_NAME}' не найдена, пропускаю")
            self._phase_3_pause_before_sans_2()
            return

        # Загружаем звук
        sans_sound = self._find_sound(SANS_SOUND_NAME)

        # Загружаем гифку
        self._gif_movie = QMovie(gif_path)
        self._gif_movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self._gif_movie.jumpToFrame(0)

        pix = self._gif_movie.currentPixmap()
        if pix.width() > 0:
            self.setFixedSize(pix.width(), pix.height())
            self._reposition()

        self._gif_label.setMovie(self._gif_movie)
        self._gif_label.setFixedSize(pix.width(), pix.height())
        self._gif_label.setVisible(True)

        # Запускаем гифку и звук одновременно
        def _start_both():
            self._gif_movie.start()
            if sans_sound:
                self._play_sound_once(sans_sound)

        QTimer.singleShot(30, _start_both)

        # Длительность гифки
        gif_duration = self._get_gif_duration(self._gif_movie)
        if gif_duration <= 0:
            gif_duration = 3000

        print(f"👁 Санс #1: показ {gif_duration} мс")
        QTimer.singleShot(gif_duration + 200, self._phase_3_pause_before_sans_2)

    def _get_gif_duration(self, movie):
        try:
            total = 0
            frame_count = movie.frameCount()
            for i in range(frame_count):
                movie.jumpToFrame(i)
                total += movie.nextFrameDelay()
            movie.jumpToFrame(0)
            return total if total > 0 else 3000
        except Exception:
            return 3000

    # ============================================================
    #                    ФАЗА 3: ПАУЗА ПЕРЕД САНСОМ #2
    # ============================================================
    def _phase_3_pause_before_sans_2(self):
        print(f"⏸ Пауза {PAUSE_BEFORE_SANS_2} мс перед Сансом #2")
        self._gif_label.setVisible(False)
        if self._gif_movie:
            self._gif_movie.stop()

        QTimer.singleShot(PAUSE_BEFORE_SANS_2, self._phase_4_ringtone_2)

    # ============================================================
    #                    ФАЗА 4: РИНГТОН #2
    # ============================================================
    def _phase_4_ringtone_2(self):
        print("📞 Звонок #2: рингтон")
        ringtone_path = self._find_sound(RINGTONE_NAME)
        if ringtone_path:
            self._play_sound_once(ringtone_path)
        QTimer.singleShot(RINGTONE_DURATION, self._phase_5_sans_2)

    # ============================================================
    #                    ФАЗА 5: САНС #2 (ВИДЕО)
    # ============================================================
    def _phase_5_sans_2(self):
        print("📺 Звонок #2: Санс (видео sans_call)")
        video_path = self._find_video(SANS_VIDEO_NAME)
        if not video_path:
            print(f"⚠️ Видео '{SANS_VIDEO_NAME}' не найдено, пропускаю")
            self._phase_6_pause_before_papyrus()
            return

        self._gif_label.setVisible(False)
        self._video_widget.setVisible(True)

        self._video_player = QMediaPlayer()
        self._video_audio = QAudioOutput()
        self._video_player.setAudioOutput(self._video_audio)
        self._video_player.setVideoOutput(self._video_widget)
        self._video_audio.setVolume(0.9)

        self._video_player.setSource(QUrl.fromLocalFile(video_path))
        self._video_player.play()

        self._video_player.mediaStatusChanged.connect(self._on_sans2_status)

    def _on_sans2_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            print("📺 Санс #2: видео закончилось")
            QTimer.singleShot(500, self._phase_6_pause_before_papyrus)

    # ============================================================
    #                    ФАЗА 6: ПАУЗА ПЕРЕД ПАПИРУСОМ
    # ============================================================
    def _phase_6_pause_before_papyrus(self):
        print(f"⏸ Пауза {PAUSE_BEFORE_PAPYRUS} мс перед Папирусом")
        self._video_widget.setVisible(False)
        if self._video_player:
            try:
                self._video_player.stop()
            except Exception:
                pass
        QTimer.singleShot(PAUSE_BEFORE_PAPYRUS, self._phase_7_ringtone_3)

    # ============================================================
    #                    ФАЗА 7: РИНГТОН #3
    # ============================================================
    def _phase_7_ringtone_3(self):
        print("📞 Звонок #3: рингтон")
        ringtone_path = self._find_sound(RINGTONE_NAME)
        if ringtone_path:
            self._play_sound_once(ringtone_path)
        QTimer.singleShot(RINGTONE_DURATION, self._phase_8_papyrus)

    # ============================================================
    #                    ФАЗА 8: ПАПИРУС
    # ============================================================
    def _phase_8_papyrus(self):
        print("📺 Звонок #3: Папирус")
        video_path = self._find_video(PAPYRUS_VIDEO_NAME)
        if not video_path:
            print(f"⚠️ Видео '{PAPYRUS_VIDEO_NAME}' не найдено, пропускаю")
            self._cleanup()
            return

        self._video_widget.setVisible(True)

        self._video_player = QMediaPlayer()
        self._video_audio = QAudioOutput()
        self._video_player.setAudioOutput(self._video_audio)
        self._video_player.setVideoOutput(self._video_widget)
        self._video_audio.setVolume(0.9)

        self._video_player.setSource(QUrl.fromLocalFile(video_path))
        self._video_player.play()

        self._video_player.mediaStatusChanged.connect(self._on_papyrus_status)

    def _on_papyrus_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            print("📺 Папирус: видео закончилось")
            QTimer.singleShot(500, self._cleanup)

    # ============================================================
    #                    ФАЙЛЫ
    # ============================================================
    def _find_sound(self, name):
        from config import BASE_DIR
        candidates = [
            os.path.join(BASE_DIR, "assets", "sounds", f"{name}.mp3"),
            os.path.join(BASE_DIR, "assets", "sounds", f"{name}.wav"),
            os.path.join(BASE_DIR, "assets", "sounds", name),
        ]
        for p in candidates:
            if os.path.exists(p):
                print(f"✅ Найден звук: {p}")
                return p
        print(f"❌ Звук '{name}' не найден в assets/sounds/")
        return None

    def _find_gif(self, name):
        from config import BASE_DIR
        candidates = [
            os.path.join(BASE_DIR, "assets", "gifs", f"{name}.gif"),
            os.path.join(BASE_DIR, "assets", f"{name}.gif"),
        ]
        for p in candidates:
            if os.path.exists(p):
                print(f"✅ Найдена гифка: {p}")
                return p
        print(f"❌ Гифка '{name}' не найдена в assets/gifs/")
        return None

    def _find_video(self, name):
        from config import BASE_DIR
        candidates = [
            os.path.join(BASE_DIR, "assets", "videos", f"{name}.mp4"),
            os.path.join(BASE_DIR, "assets", "videos", f"{name}.webm"),
            os.path.join(BASE_DIR, "assets", "videos", f"{name}.mkv"),
            os.path.join(BASE_DIR, "assets", "videos", name),
        ]
        for p in candidates:
            if os.path.exists(p):
                print(f"✅ Найдено видео: {p}")
                return p
        print(f"❌ Видео '{name}' не найдено в assets/videos/")
        return None

    # ============================================================
    #                    ЗВУК
    # ============================================================
    def _play_sound_once(self, path):
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            self._current_sound = path
            print(f"🔊 Играю: {os.path.basename(path)}")
        except Exception as e:
            print(f"⚠️ pygame: {e}")
            try:
                if self._sound_player is None:
                    self._sound_player = QMediaPlayer()
                    self._sound_audio = QAudioOutput()
                    self._sound_player.setAudioOutput(self._sound_audio)
                    self._sound_audio.setVolume(0.9)
                self._sound_player.setSource(QUrl.fromLocalFile(path))
                self._sound_player.play()
                print(f"🔊 Играю (Qt): {os.path.basename(path)}")
            except Exception as e2:
                print(f"⚠️ QMediaPlayer: {e2}")

    # ============================================================
    #                    ЗАВЕРШЕНИЕ
    # ============================================================
    def _cleanup(self):
        global _sans_instance
        print("🎬 Сценка: завершение")

        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass

        try:
            if self._sound_player:
                self._sound_player.stop()
        except Exception:
            pass

        try:
            if self._video_player:
                self._video_player.stop()
        except Exception:
            pass

        try:
            if self._gif_movie:
                self._gif_movie.stop()
        except Exception:
            pass

        try:
            self.hide()
            self.close()
            self.deleteLater()
        except Exception:
            pass

        _sans_instance = None

    def restart(self):
        self._cleanup()
        if self.parent_window:
            QTimer.singleShot(100, lambda: show_sans(self.parent_window))


def is_sans_active():
    return _sans_instance is not None and _sans_instance.isVisible()


def hide_sans():
    global _sans_instance
    if _sans_instance is not None:
        try:
            _sans_instance._cleanup()
        except Exception:
            pass