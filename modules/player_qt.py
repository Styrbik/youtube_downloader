"""
Встроенный плеер для MP3 и видео.
QMediaPlayer + QVideoWidget.
- Overlay в fullscreen через отдельное frameless-окно (Windows-friendly)
- Overlay всплывает при движении мыши через глобальный таймер QCursor.pos()
- Перемотка без крашей
- Repeat ONE без дёрганья
- Переключение видео ↔ аудио без зависаний
"""

import os
import ctypes
import random
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QListWidget, QSlider, QSizePolicy, QTabWidget, QMenu,
    QFileDialog, QApplication, QFrame,
)
from PyQt6.QtCore import Qt, QUrl, QTimer, QEvent, QPoint, QRect
from PyQt6.QtGui import (
    QPixmap, QFontDatabase, QFont, QShortcut, QKeySequence,
    QCursor,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


# ============================================================
#                CLICKABLE VIDEO WIDGET
# ============================================================
class ClickableVideoWidget(QVideoWidget):
    """QVideoWidget, который ловит движение мыши и клики."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._on_mouse_move = None
        self._on_double_click = None
        self._on_click = None

    def mouseMoveEvent(self, event):
        if self._on_mouse_move:
            self._on_mouse_move()
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self._on_double_click:
            self._on_double_click()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._on_click:
            self._on_click()
        super().mousePressEvent(event)


# ============================================================
#                    OVERLAY WINDOW
# ============================================================
class OverlayWindow(QWidget):
    """Отдельное frameless-окно поверх главного."""
    def __init__(self, parent_player):
        super().__init__(None)
        self.parent_player = parent_player

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame()
        self.card.setObjectName("overlay_card")
        self.card.setStyleSheet("""
            QFrame#overlay_card {
                background-color: rgba(0, 0, 0, 210);
                border-radius: 12px;
            }
        """)
        self.card.setMouseTracking(True)
        outer.addWidget(self.card)

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(8)

        # Прогресс
        prog_row = QHBoxLayout()

        self.pos_label = QLabel("0:00")
        self.pos_label.setStyleSheet(
            "color: #fff; font-size: 12px; background: transparent;"
        )
        self.pos_label.setFixedWidth(48)
        prog_row.addWidget(self.pos_label)

        self.progress = QSlider(Qt.Orientation.Horizontal)
        self.progress.setRange(0, 1000)
        self.progress.sliderReleased.connect(
            lambda: self.parent_player._on_seek(self.progress.value())
        )
        self.progress.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(255,255,255,60);
                height: 5px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #e62117;
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover { background: #ff3b30; }
        """)
        prog_row.addWidget(self.progress, stretch=1)

        self.dur_label = QLabel("0:00")
        self.dur_label.setStyleSheet(
            "color: #fff; font-size: 12px; background: transparent;"
        )
        self.dur_label.setFixedWidth(48)
        prog_row.addWidget(self.dur_label)

        layout.addLayout(prog_row)

        # Кнопки
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setFixedSize(44, 44)
        self.btn_prev.setToolTip("Предыдущий")
        self.btn_prev.clicked.connect(self.parent_player._on_prev)
        self._style_btn(self.btn_prev)
        btn_row.addWidget(self.btn_prev)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(60, 60)
        self.btn_play.setToolTip("Играть / Пауза (Space)")
        self.btn_play.clicked.connect(self.parent_player._on_play_pause)
        self._style_btn(self.btn_play, big=True)
        btn_row.addWidget(self.btn_play)

        self.btn_next = QPushButton("⏭")
        self.btn_next.setFixedSize(44, 44)
        self.btn_next.setToolTip("Следующий")
        self.btn_next.clicked.connect(self.parent_player._on_next)
        self._style_btn(self.btn_next)
        btn_row.addWidget(self.btn_next)

        btn_row.addStretch()

        # Громкость
        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet(
            "color: #fff; background: transparent; font-size: 16px;"
        )
        btn_row.addWidget(vol_icon)

        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(70)
        self.volume.setFixedWidth(120)
        self.volume.valueChanged.connect(self.parent_player._on_volume)
        self.volume.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(255,255,255,60);
                height: 5px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #e62117;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
        """)
        btn_row.addWidget(self.volume)

        # Кнопка выхода
        self.btn_exit = QPushButton("⛶")
        self.btn_exit.setFixedSize(44, 44)
        self.btn_exit.setToolTip("Выйти из полного экрана (Esc / F11)")
        self.btn_exit.clicked.connect(self.parent_player._on_fullscreen_toggle)
        self._style_btn(self.btn_exit)
        btn_row.addWidget(self.btn_exit)

        layout.addLayout(btn_row)

    def _style_btn(self, btn, big=False):
        radius = 30 if big else 22
        font_size = "20px" if big else "16px"
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 40);
                color: #ffffff;
                border: none;
                border-radius: {radius}px;
                font-size: {font_size};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(230, 33, 23, 200);
            }}
            QPushButton:pressed {{
                background-color: rgba(180, 20, 20, 230);
            }}
        """)

    def update_progress(self, position_ms, duration_ms):
        if self.progress.isSliderDown():
            return
        if duration_ms > 0:
            val = int(position_ms * 1000 / duration_ms)
            self.progress.setValue(val)
        self.pos_label.setText(self.parent_player._fmt_time(position_ms))
        self.dur_label.setText(self.parent_player._fmt_time(duration_ms))

    def set_playing(self, playing):
        self.btn_play.setText("⏸" if playing else "▶")

    def mouseMoveEvent(self, event):
        self.parent_player._schedule_overlay_hide()
        super().mouseMoveEvent(event)


# ============================================================
#                    PLAYER WINDOW
# ============================================================
class PlayerWindow(QWidget):
    def __init__(self, parent_app=None):
        super().__init__(None, Qt.WindowType.Window)
        self.parent_app = parent_app

        self._apply_theme()

        self.setWindowTitle("🎵 Плеер")
        self.resize(700, 800)
        self.setMinimumSize(500, 600)

        # ---------- Состояние ----------
        self.tracks = []
        self.current_index = -1
        self.current_kind = None
        self.shuffle_on = False
        self.repeat_mode = 0
        self.is_fullscreen = False
        self._normal_geometry = None

        self._seeking = False
        self._repeating = False
        self._cursor_hidden = False
        self._last_cursor_pos = None

        # ---------- Плеер ----------
        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(0.7)

        # ---------- Таймеры ----------
        self._hide_controls_timer = QTimer(self)
        self._hide_controls_timer.setSingleShot(True)
        self._hide_controls_timer.timeout.connect(self._auto_hide_controls)

        self._overlay_watch_timer = QTimer(self)
        self._overlay_watch_timer.setInterval(150)
        self._overlay_watch_timer.timeout.connect(self._check_overlay_hover)

        # ---------- Overlay ----------
        self.overlay = OverlayWindow(self)
        self.overlay.volume.setValue(70)

        # ---------- UI ----------
        self._build_ui()

        # ---------- Сигналы ----------
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.mediaStatusChanged.connect(self._on_status_changed)
        self.player.errorOccurred.connect(self._on_error)

        # ---------- Хоткеи ----------
        QShortcut(QKeySequence("Escape"), self, self._on_escape)
        QShortcut(QKeySequence("F11"), self, self._on_fullscreen_toggle)
        QShortcut(QKeySequence("Space"), self, self._on_play_pause)
        QShortcut(QKeySequence("Left"), self, lambda: self._seek_relative(-5000))
        QShortcut(QKeySequence("Right"), self, lambda: self._seek_relative(5000))

        self.setMouseTracking(True)
        self._load_tracks()
        self.setStyleSheet(self._build_qss())

    # ============================================================
    #                    UI
    # ============================================================
    def _build_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(20, 20, 20, 20)
        self.root_layout.setSpacing(12)

        self.header_label = QLabel("🎵 Плеер")
        self.header_label.setStyleSheet(
            f"color: {self._theme['FG']}; font-size: 18px; font-weight: bold;"
        )
        self.root_layout.addWidget(self.header_label)

        # ---------- ВИДЕО ----------
        self.video_container = QWidget()
        self.video_grid = QGridLayout(self.video_container)
        self.video_grid.setContentsMargins(0, 0, 0, 0)
        self.video_grid.setSpacing(0)

        self.video_widget = self._create_video_widget()
        self.video_grid.addWidget(self.video_widget, 0, 0)

        self.video_container.setFixedHeight(240)
        self.root_layout.addWidget(self.video_container)

        # ---------- ОБЛОЖКА ----------
        self.cover_label = QLabel()
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setMinimumHeight(0)
        self.cover_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.cover_label.setScaledContents(False)
        self.cover_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cover_label.mouseDoubleClickEvent = self._on_cover_click
        self.cover_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.cover_label.customContextMenuRequested.connect(self._on_cover_context_menu)

        self.cover_container = QWidget()
        self.cover_container.setMinimumHeight(0)
        self.cover_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        cover_layout = QVBoxLayout(self.cover_container)
        cover_layout.setContentsMargins(0, 0, 0, 0)
        cover_layout.addWidget(self.cover_label)
        self.root_layout.addWidget(self.cover_container, stretch=1)

        self._current_cover_pixmap = None

        # ---------- Название ----------
        self.title_label = QLabel("Ничего не выбрано")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(
            f"color: {self._theme['FG']}; font-size: 14px; font-weight: bold;"
        )
        self.title_label.setWordWrap(True)
        self.root_layout.addWidget(self.title_label)

        self.artist_label = QLabel("")
        self.artist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.artist_label.setStyleSheet(
            f"color: {self._theme['FG_DIM']}; font-size: 11px;"
        )
        self.root_layout.addWidget(self.artist_label)

        # ---------- Прогресс ----------
        self.progress_row_widget = QWidget()
        progress_row = QHBoxLayout(self.progress_row_widget)
        progress_row.setContentsMargins(0, 0, 0, 0)

        self.pos_label = QLabel("0:00")
        self.pos_label.setStyleSheet(
            f"color: {self._theme['FG_DIM']}; font-size: 10px;"
        )
        self.pos_label.setFixedWidth(40)
        progress_row.addWidget(self.pos_label)

        self.progress = QSlider(Qt.Orientation.Horizontal)
        self.progress.setRange(0, 1000)
        self.progress.sliderReleased.connect(
            lambda: self._on_seek(self.progress.value())
        )
        progress_row.addWidget(self.progress, stretch=1)

        self.dur_label = QLabel("0:00")
        self.dur_label.setStyleSheet(
            f"color: {self._theme['FG_DIM']}; font-size: 10px;"
        )
        self.dur_label.setFixedWidth(40)
        progress_row.addWidget(self.dur_label)

        self.root_layout.addWidget(self.progress_row_widget)

        # ---------- Кнопки ----------
        self.btn_row_widget = QWidget()
        btn_row = QHBoxLayout(self.btn_row_widget)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)
        btn_row.addStretch()

        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setFixedSize(48, 48)
        self.btn_prev.clicked.connect(self._on_prev)
        btn_row.addWidget(self.btn_prev)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(64, 64)
        self.btn_play.clicked.connect(self._on_play_pause)
        btn_row.addWidget(self.btn_play)

        self.btn_next = QPushButton("⏭")
        self.btn_next.setFixedSize(48, 48)
        self.btn_next.clicked.connect(self._on_next)
        btn_row.addWidget(self.btn_next)

        btn_row.addStretch()

        self.btn_shuffle = QPushButton("🔀")
        self.btn_shuffle.setFixedSize(42, 42)
        self.btn_shuffle.setCheckable(True)
        self.btn_shuffle.setToolTip("Перемешать")
        self.btn_shuffle.clicked.connect(self._on_shuffle_toggle)
        btn_row.addWidget(self.btn_shuffle)

        self.btn_repeat = QPushButton("🔁")
        self.btn_repeat.setFixedSize(42, 42)
        self.btn_repeat.setCheckable(True)
        self.btn_repeat.setToolTip("Повтор")
        self.btn_repeat.clicked.connect(self._on_repeat_toggle)
        btn_row.addWidget(self.btn_repeat)

        self.btn_fullscreen = QPushButton("⛶")
        self.btn_fullscreen.setFixedSize(42, 42)
        self.btn_fullscreen.setToolTip("На весь экран (F11)")
        self.btn_fullscreen.clicked.connect(self._on_fullscreen_toggle)
        btn_row.addWidget(self.btn_fullscreen)

        self.root_layout.addWidget(self.btn_row_widget)

        # ---------- Громкость ----------
        self.vol_row_widget = QWidget()
        vol_row = QHBoxLayout(self.vol_row_widget)
        vol_row.setContentsMargins(0, 0, 0, 0)

        vol_row.addWidget(QLabel("🔊"))
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(70)
        self.volume.valueChanged.connect(self._on_volume)
        vol_row.addWidget(self.volume, stretch=1)

        self.root_layout.addWidget(self.vol_row_widget)

        # ---------- Плейлист ----------
        self.playlist_label = QLabel("Плейлист")
        self.playlist_label.setStyleSheet(
            f"color: {self._theme['FG_DIM']}; font-size: 11px; font-weight: bold;"
        )
        self.root_layout.addWidget(self.playlist_label)

        self.tabs = QTabWidget()
        self.root_layout.addWidget(self.tabs, stretch=1)

        self.playlist_all = QListWidget()
        self.playlist_all.itemDoubleClicked.connect(self._on_playlist_click)
        self.playlist_all.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_all.customContextMenuRequested.connect(
            lambda pos: self._on_playlist_context_menu(pos, self.playlist_all)
        )
        self.tabs.addTab(self.playlist_all, "🎵 Всё")

        self.playlist_audio = QListWidget()
        self.playlist_audio.itemDoubleClicked.connect(self._on_playlist_click)
        self.tabs.addTab(self.playlist_audio, "♪ Музыка")

        self.playlist_video = QListWidget()
        self.playlist_video.itemDoubleClicked.connect(self._on_playlist_click)
        self.tabs.addTab(self.playlist_video, "▶ Видео")

        # ---------- Низ ----------
        self.bottom_row_widget = QWidget()
        bottom_row = QHBoxLayout(self.bottom_row_widget)
        bottom_row.setContentsMargins(0, 0, 0, 0)

        self.btn_folder_audio = QPushButton("🎵 Папка")
        self.btn_folder_audio.clicked.connect(lambda: self._on_choose_folder("audio"))
        bottom_row.addWidget(self.btn_folder_audio)

        self.btn_folder_video = QPushButton("🎬 Папка")
        self.btn_folder_video.clicked.connect(lambda: self._on_choose_folder("video"))
        bottom_row.addWidget(self.btn_folder_video)

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setFixedWidth(42)
        self.btn_refresh.clicked.connect(self._on_refresh)
        bottom_row.addWidget(self.btn_refresh)

        bottom_row.addStretch()

        b_close = QPushButton("Закрыть")
        b_close.clicked.connect(self.close)
        bottom_row.addWidget(b_close)

        self.root_layout.addWidget(self.bottom_row_widget)

    def _create_video_widget(self):
        vw = ClickableVideoWidget()
        vw.setMinimumHeight(0)
        vw.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        vw._on_mouse_move = self._on_video_mouse_move
        vw._on_double_click = self._on_fullscreen_toggle
        vw._on_click = self._on_video_click
        return vw

    def _on_video_mouse_move(self):
        """Мышь над видео — показать overlay (в fullscreen)."""
        if self.is_fullscreen:
            self._show_overlay()

    def _on_video_click(self):
        """Одиночный клик по видео — play/pause (в fullscreen)."""
        if self.is_fullscreen:
            self._on_play_pause()

    # ============================================================
    #                    ТЕМА
    # ============================================================
    def _apply_theme(self):
        try:
            from modules.themes import get_theme, get_theme_font
            from modules import settings as _s

            s = _s.load()
            theme_name = s.get("theme", "dark")
            forced = s.get("admin_forced_holiday")
            actual = forced if forced else theme_name

            t = get_theme(actual)
            self._theme = {
                "BG": t.get("BG", "#1e1e1e"),
                "BG_CARD": t.get("BG_CARD", "#2a2a2a"),
                "BG_INPUT": t.get("BG_INPUT", "#333333"),
                "FG": t.get("FG", "#e0e0e0"),
                "FG_DIM": t.get("FG_DIM", "#888888"),
                "ACCENT": t.get("ACCENT", "#e62117"),
                "ACCENT_HOVER": t.get("ACCENT_HOVER", "#ff3b30"),
                "BORDER": t.get("BORDER", "#3a3a3a"),
            }

            font_path = get_theme_font(actual)
            if font_path and os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id >= 0:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        self._theme_font = families[0]
                        font = QFont(families[0])
                        font.setPointSize(10)
                        self.setFont(font)
            else:
                self._theme_font = "Segoe UI"

            print(f"🎨 Плеер: тема «{actual}»")

        except Exception as e:
            print(f"⚠️ Ошибка применения темы: {e}")
            self._theme = {
                "BG": "#1e1e1e",
                "BG_CARD": "#2a2a2a",
                "BG_INPUT": "#333333",
                "FG": "#e0e0e0",
                "FG_DIM": "#888888",
                "ACCENT": "#e62117",
                "ACCENT_HOVER": "#ff3b30",
                "BORDER": "#3a3a3a",
            }
            self._theme_font = "Segoe UI"

    def _build_qss(self):
        t = self._theme
        font = self._theme_font
        return f"""
            QWidget {{
                background-color: {t["BG"]};
                color: {t["FG"]};
                font-family: "{font}", "Segoe UI Emoji";
            }}
            QLabel {{ background: transparent; color: {t["FG"]}; }}
            QPushButton {{
                background-color: {t["BG_CARD"]};
                color: {t["FG"]};
                border: 1px solid {t["BORDER"]};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {t["BORDER"]};
                border: 1px solid {t["ACCENT"]};
            }}
            QPushButton:pressed {{ background-color: {t["ACCENT"]}; color: white; }}
            QListWidget {{
                background-color: {t["BG_INPUT"]};
                color: {t["FG"]};
                border: 1px solid {t["BORDER"]};
                border-radius: 8px;
                padding: 4px;
            }}
            QListWidget::item {{ padding: 6px 8px; border-radius: 4px; }}
            QListWidget::item:hover {{ background-color: {t["BORDER"]}; }}
            QListWidget::item:selected {{ background-color: {t["ACCENT"]}; color: white; }}
            QSlider::groove:horizontal {{ background: {t["BG_INPUT"]}; height: 6px; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: {t["ACCENT"]}; width: 14px; margin: -5px 0; border-radius: 7px; }}
            QSlider::handle:horizontal:hover {{ background: {t["ACCENT_HOVER"]}; }}
            QTabWidget::pane {{ border: 1px solid {t["BORDER"]}; border-radius: 8px; background: {t["BG_CARD"]}; }}
            QTabBar::tab {{
                background: {t["BG_INPUT"]}; color: {t["FG_DIM"]};
                padding: 8px 14px; margin-right: 2px;
                border-top-left-radius: 6px; border-top-right-radius: 6px;
                font-size: 12px; font-weight: bold;
            }}
            QTabBar::tab:selected {{ background: {t["ACCENT"]}; color: white; }}
            QTabBar::tab:hover {{ background: {t["BORDER"]}; color: {t["FG"]}; }}
        """

    # ============================================================
    #                    FULLSCREEN
    # ============================================================
    def _on_fullscreen_toggle(self):
        if self.current_kind != "video":
            print("⚠️ Полный экран только для видео")
            return

        if self.is_fullscreen:
            self._exit_fullscreen()
        else:
            self._enter_fullscreen()

    def _enter_fullscreen(self):
        self._normal_geometry = self.geometry()
        self.is_fullscreen = True
        self._last_cursor_pos = None

        self.header_label.setVisible(False)
        self.cover_container.setVisible(False)
        self.title_label.setVisible(False)
        self.artist_label.setVisible(False)
        self.progress_row_widget.setVisible(False)
        self.btn_row_widget.setVisible(False)
        self.vol_row_widget.setVisible(False)
        self.playlist_label.setVisible(False)
        self.tabs.setVisible(False)
        self.bottom_row_widget.setVisible(False)

        self.video_container.setFixedHeight(16777215)
        self.video_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        self.showFullScreen()

        # Стартовое положение мыши
        self._last_cursor_pos = QCursor.pos()
        # Сразу показать overlay
        QTimer.singleShot(100, self._show_overlay)
        # Запустить глобальный таймер
        self._overlay_watch_timer.start()

    def _exit_fullscreen(self):
        self._hide_controls_timer.stop()
        self._overlay_watch_timer.stop()
        self.overlay.hide()
        self._last_cursor_pos = None

        self.showNormal()
        if self._normal_geometry:
            self.setGeometry(self._normal_geometry)
        self.is_fullscreen = False

        self.root_layout.setContentsMargins(20, 20, 20, 20)
        self.root_layout.setSpacing(12)

        self.header_label.setVisible(True)
        self.cover_container.setVisible(True)
        self.title_label.setVisible(True)
        self.artist_label.setVisible(True)
        self.progress_row_widget.setVisible(True)
        self.btn_row_widget.setVisible(True)
        self.vol_row_widget.setVisible(True)
        self.playlist_label.setVisible(True)
        self.tabs.setVisible(True)
        self.bottom_row_widget.setVisible(True)

        self.video_container.setFixedHeight(240)
        self.video_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

    # ============================================================
    #                    OVERLAY
    # ============================================================
    def _show_overlay(self):
        """Показать overlay внизу главного окна."""
        if not self.is_fullscreen:
            return

        main_geo = self.geometry()
        ov_height = 130
        ov_width = main_geo.width() - 80
        ov_x = main_geo.x() + 40
        ov_y = main_geo.y() + main_geo.height() - ov_height - 40

        self.overlay.setGeometry(ov_x, ov_y, ov_width, ov_height)
        self.overlay.show()
        self.overlay.raise_()

        self._hide_controls_timer.start(3000)

    def _schedule_overlay_hide(self):
        """Продлить показ overlay (при движении над ним)."""
        if self.is_fullscreen and self.overlay.isVisible():
            self._hide_controls_timer.start(3000)

    def _check_overlay_hover(self):
        """
        Каждые 150мс проверяем глобальную позицию мыши.
        Если она изменилась — показываем overlay.
        """
        if not self.is_fullscreen:
            return

        try:
            cursor_pos = QCursor.pos()
        except Exception:
            return

        # Мышь сдвинулась?
        if self._last_cursor_pos is None or cursor_pos != self._last_cursor_pos:
            self._last_cursor_pos = cursor_pos

            if not self.overlay.isVisible():
                self._show_overlay()
            else:
                self._hide_controls_timer.start(3000)
            return

        # Мышь не двигается — если над overlay, продлить
        if self.overlay.isVisible():
            ov_geo = self.overlay.geometry()
            if ov_geo.contains(cursor_pos):
                self._hide_controls_timer.start(3000)

    def _auto_hide_controls(self):
        """Скрыть overlay."""
        if not self.is_fullscreen:
            return
        self.overlay.hide()

    def _on_escape(self):
        if self.is_fullscreen:
            self._exit_fullscreen()
        else:
            self.close()

    # ============================================================
    #                    ВОСПРОИЗВЕДЕНИЕ
    # ============================================================
    def _play_index(self, idx):
        if idx < 0 or idx >= len(self.tracks):
            return

        self.current_index = idx
        track = self.tracks[idx]
        kind = track.get('kind', 'audio')

        if self.current_kind != kind:
            print(f"🔄 Переключаю на {kind}")

            try:
                self.player.setVideoOutput(None)
            except Exception as e:
                print(f"⚠️ setVideoOutput(None): {e}")

            try:
                self.player.stop()
            except Exception:
                pass

            if kind == "video":
                self.video_container.setVisible(True)
                self.cover_container.setVisible(False)
                self.video_container.setFixedHeight(240)
            else:
                self.video_container.setVisible(False)
                self.cover_container.setVisible(True)

            self.current_kind = kind

            QTimer.singleShot(100, lambda: self._do_load_track(track, kind))
            return

        self._do_load_track(track, kind)

    def _do_load_track(self, track, kind):
        self._update_track_info(track)
        self.btn_play.setText("⏸")
        self.overlay.set_playing(True)

        try:
            self.player.stop()
        except Exception:
            pass

        file_url = QUrl.fromLocalFile(track['file'])

        def _do_play():
            try:
                self.player.setSource(file_url)

                if kind == "video":
                    try:
                        self.player.setVideoOutput(self.video_widget)
                    except Exception as e:
                        print(f"⚠️ setVideoOutput(video): {e}")

                self.player.play()
            except Exception as e:
                print(f"⚠️ Ошибка play: {e}")

        QTimer.singleShot(50, _do_play)

    def _on_play_pause(self):
        if self.player is None:
            return

        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶")
            self.overlay.set_playing(False)
        else:
            if self.current_index < 0 and self.tracks:
                self._play_index(0)
            else:
                self.player.play()
                self.btn_play.setText("⏸")
                self.overlay.set_playing(True)

    def _on_prev(self):
        if not self.tracks:
            return
        idx = self._get_prev_index()
        if idx < 0:
            return
        self._play_index(idx)

    def _on_next(self):
        if not self.tracks:
            return
        if self.player is None:
            return
        try:
            self.player.stop()
        except Exception:
            pass
        idx = self._get_next_index()
        if idx < 0:
            self.btn_play.setText("▶")
            self.overlay.set_playing(False)
            return
        QTimer.singleShot(50, lambda: self._play_index(idx))

    def _on_volume(self, value):
        self.audio.setVolume(value / 100.0)
        if self.sender() is self.volume:
            if self.overlay.volume.value() != value:
                self.overlay.volume.setValue(value)
        elif self.sender() is self.overlay.volume:
            if self.volume.value() != value:
                self.volume.setValue(value)

    # ============================================================
    #                    БЕЗОПАСНАЯ ПЕРЕМОТКА
    # ============================================================
    def _on_seek(self, value):
        if self.player is None or self._seeking:
            return

        try:
            duration = self.player.duration()
            if duration <= 0:
                return
            pos_ms = int(duration * value / 1000)

            was_playing = (self.player.playbackState()
                           == QMediaPlayer.PlaybackState.PlayingState)

            self._seeking = True

            current_file = None
            if 0 <= self.current_index < len(self.tracks):
                current_file = self.tracks[self.current_index]['file']

            if not current_file or not os.path.exists(current_file):
                self._seeking = False
                return

            try:
                self.player.stop()
            except Exception:
                pass

            file_url = QUrl.fromLocalFile(current_file)

            def _step1_set_source():
                try:
                    self.player.setSource(file_url)
                except Exception as e:
                    print(f"⚠️ setSource: {e}")
                    self._seeking = False
                    return
                QTimer.singleShot(200, _step2_set_position)

            def _step2_set_position():
                try:
                    self.player.setPosition(pos_ms)
                except Exception as e:
                    print(f"⚠️ setPosition: {e}")
                QTimer.singleShot(150, _step3_play)

            def _step3_play():
                try:
                    if was_playing:
                        self.player.play()
                        self.btn_play.setText("⏸")
                        self.overlay.set_playing(True)
                    else:
                        self.btn_play.setText("▶")
                        self.overlay.set_playing(False)
                except Exception as e:
                    print(f"⚠️ play: {e}")
                self._seeking = False

            QTimer.singleShot(50, _step1_set_source)

        except Exception as e:
            print(f"⚠️ Ошибка перемотки: {e}")
            self._seeking = False

    def _seek_relative(self, delta_ms):
        if self.player is None:
            return
        duration = self.player.duration()
        if duration <= 0:
            return
        cur = self.player.position()
        target = max(0, min(duration, cur + delta_ms))
        value = int(target * 1000 / duration)
        self._on_seek(value)

    def _on_duration_changed(self, duration):
        self.dur_label.setText(self._fmt_time(duration))
        self.overlay.dur_label.setText(self._fmt_time(duration))

    def _on_position_changed(self, position):
        if not self.progress.isSliderDown():
            if self.player.duration() > 0:
                val = int(position * 1000 / self.player.duration())
                self.progress.setValue(val)
        self.pos_label.setText(self._fmt_time(position))

        self.overlay.update_progress(position, self.player.duration())

    def _on_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.repeat_mode == 1 and self.current_index >= 0:
                if self._repeating:
                    return
                self._repeating = True

                try:
                    self.player.stop()
                except Exception:
                    pass

                current_file = self.tracks[self.current_index]['file']
                file_url = QUrl.fromLocalFile(current_file)

                def _do_repeat():
                    try:
                        self.player.setSource(file_url)
                        self.player.setPosition(0)
                        self.player.play()
                        self.btn_play.setText("⏸")
                        self.overlay.set_playing(True)
                    except Exception as e:
                        print(f"⚠️ repeat: {e}")
                    self._repeating = False

                QTimer.singleShot(150, _do_repeat)
                return

            QTimer.singleShot(300, self._on_next)

    def _on_error(self, error, msg):
        print(f"⚠️ Ошибка плеера: {error} — {msg}")
        self.title_label.setText(f"❌ Ошибка: {msg}")

    def _fmt_time(self, ms):
        if not ms:
            return "0:00"
        secs = ms // 1000
        mins = secs // 60
        secs = secs % 60
        return f"{mins}:{secs:02d}"

    # ============================================================
    #                    SHUFFLE / REPEAT
    # ============================================================
    def _on_shuffle_toggle(self):
        self.shuffle_on = self.btn_shuffle.isChecked()
        if self.shuffle_on:
            self.btn_shuffle.setStyleSheet(
                f"background-color: {self._theme['ACCENT']}; color: white;"
            )
        else:
            self.btn_shuffle.setStyleSheet("")

    def _on_repeat_toggle(self):
        self.repeat_mode = (self.repeat_mode + 1) % 3
        if self.repeat_mode == 0:
            self.btn_repeat.setText("🔁")
            self.btn_repeat.setStyleSheet("")
        elif self.repeat_mode == 1:
            self.btn_repeat.setText("🔂")
            self.btn_repeat.setStyleSheet(
                f"background-color: {self._theme['ACCENT']}; color: white;"
            )
        else:
            self.btn_repeat.setText("🔁")
            self.btn_repeat.setStyleSheet(
                f"background-color: {self._theme['ACCENT']}; color: white;"
            )

    def _get_next_index(self):
        if not self.tracks:
            return -1
        if self.repeat_mode == 1 and self.current_index >= 0:
            return self.current_index
        if self.shuffle_on:
            available = [i for i in range(len(self.tracks)) if i != self.current_index]
            if not available:
                return self.current_index
            return random.choice(available)
        idx = self.current_index + 1
        if idx >= len(self.tracks):
            if self.repeat_mode == 2:
                idx = 0
            else:
                idx = -1
        return idx

    def _get_prev_index(self):
        if not self.tracks:
            return -1
        if self.shuffle_on:
            available = [i for i in range(len(self.tracks)) if i != self.current_index]
            if not available:
                return self.current_index
            return random.choice(available)
        idx = self.current_index - 1
        if idx < 0:
            if self.repeat_mode == 2:
                idx = len(self.tracks) - 1
            else:
                idx = 0
        return idx

    # ============================================================
    #                    ПЛЕЙЛИСТ
    # ============================================================
    def _load_tracks(self):
        from config import DOWNLOADS_DIR
        from modules import settings as _s

        s = _s.load()
        settings = self.parent_app.settings if self.parent_app else s

        self.tracks = []
        seen_files = set()

        scan_sub = settings.get("player_scan_subfolders", True)

        audio_folder = settings.get("player_folder_audio", "")
        if not audio_folder:
            if settings.get("auto_sort", False):
                audio_folder = os.path.join(
                    DOWNLOADS_DIR,
                    settings.get("sort_audio_dir", "Музыка"),
                )
            else:
                audio_folder = DOWNLOADS_DIR

        if audio_folder and os.path.isdir(audio_folder):
            print(f"🎵 Сканирую аудио: {audio_folder}")
            self._scan_folder(audio_folder, scan_sub, seen_files, kind="audio")

        video_folder = settings.get("player_folder_video", "")
        if not video_folder:
            if settings.get("auto_sort", False):
                video_folder = os.path.join(
                    DOWNLOADS_DIR,
                    settings.get("sort_video_dir", "Видео"),
                )
            else:
                video_folder = DOWNLOADS_DIR

        if video_folder and os.path.isdir(video_folder):
            print(f"🎬 Сканирую видео: {video_folder}")
            self._scan_folder(video_folder, scan_sub, seen_files, kind="video")

        history = settings.get("history", [])
        for entry in history:
            fp = entry.get("file", "")
            if fp and os.path.exists(fp):
                if fp not in seen_files:
                    seen_files.add(fp)
                    kind = "audio" if fp.lower().endswith(".mp3") else "video"
                    self.tracks.append({
                        "file": fp,
                        "title": entry.get("title") or os.path.splitext(os.path.basename(fp))[0],
                        "kind": kind,
                    })

        self.tracks.sort(key=lambda t: (t['kind'], t['title'].lower()))
        self._populate_playlists()
        print(f"🎵 Всего треков: {len(self.tracks)}")

    def _scan_folder(self, folder, scan_sub, seen_files, kind="audio"):
        if kind == "audio":
            exts = (".mp3", ".m4a", ".flac", ".wav", ".ogg")
        else:
            exts = (".mp4", ".mkv", ".webm", ".avi", ".mov")

        if scan_sub:
            for root, dirs, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(exts):
                        fp = os.path.join(root, f)
                        if fp not in seen_files:
                            seen_files.add(fp)
                            self.tracks.append({
                                "file": fp,
                                "title": os.path.splitext(f)[0],
                                "kind": kind,
                            })
        else:
            for f in os.listdir(folder):
                fp = os.path.join(folder, f)
                if os.path.isfile(fp) and f.lower().endswith(exts):
                    if fp not in seen_files:
                        seen_files.add(fp)
                        self.tracks.append({
                            "file": fp,
                            "title": os.path.splitext(f)[0],
                            "kind": kind,
                        })

    def _populate_playlists(self):
        self.playlist_all.clear()
        for t in self.tracks:
            icon = "♪" if t['kind'] == "audio" else "▶"
            self.playlist_all.addItem(f"{icon} {t['title']}")

        self.playlist_audio.clear()
        for t in self.tracks:
            if t['kind'] == "audio":
                self.playlist_audio.addItem(f"♪ {t['title']}")

        self.playlist_video.clear()
        for t in self.tracks:
            if t['kind'] == "video":
                self.playlist_video.addItem(f"▶ {t['title']}")

    def _on_playlist_click(self, item):
        current_tab = self.tabs.currentIndex()
        if current_tab == 0:
            idx = self.playlist_all.row(item)
        elif current_tab == 1:
            audio_tracks = [i for i, t in enumerate(self.tracks) if t['kind'] == "audio"]
            local_idx = self.playlist_audio.row(item)
            if local_idx < 0 or local_idx >= len(audio_tracks):
                return
            idx = audio_tracks[local_idx]
        else:
            video_tracks = [i for i, t in enumerate(self.tracks) if t['kind'] == "video"]
            local_idx = self.playlist_video.row(item)
            if local_idx < 0 or local_idx >= len(video_tracks):
                return
            idx = video_tracks[local_idx]

        self._play_index(idx)

    def _on_refresh(self):
        current_file = None
        if self.current_index >= 0 and self.current_index < len(self.tracks):
            current_file = self.tracks[self.current_index]['file']

        self._load_tracks()

        if current_file:
            for i, t in enumerate(self.tracks):
                if t['file'] == current_file:
                    self.playlist_all.setCurrentRow(i)
                    break

        print(f"🎵 Треков: {len(self.tracks)}")

    def _on_choose_folder(self, kind):
        from modules import settings as _s
        from config import DOWNLOADS_DIR

        key = f"player_folder_{kind}"
        label = "музыкой" if kind == "audio" else "видео"

        current = self.parent_app.settings.get(key, "")
        if not current or not os.path.isdir(current):
            current = DOWNLOADS_DIR

        chosen = QFileDialog.getExistingDirectory(
            self, f"Выбери папку с {label}", current
        )
        if chosen:
            self.parent_app.settings[key] = chosen
            _s.save(self.parent_app.settings)
            self._on_refresh()

    def _on_cover_click(self, event):
        if self.current_index < 0 or self.current_index >= len(self.tracks):
            return
        track = self.tracks[self.current_index]
        file_path = track['file']
        if not os.path.exists(file_path):
            return
        try:
            import subprocess
            subprocess.Popen([
                "explorer", "/select,", os.path.normpath(file_path)
            ])
        except Exception as e:
            print(f"⚠️ Проводник: {e}")

    def _on_cover_context_menu(self, pos):
        if self.current_index < 0 or self.current_index >= len(self.tracks):
            return
        track = self.tracks[self.current_index]
        file_path = track['file']

        menu = QMenu(self)
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            menu.addAction("⏸ Пауза", self._on_play_pause)
        else:
            menu.addAction("▶ Играть", self._on_play_pause)
        menu.addSeparator()
        menu.addAction("📂 Показать в проводнике",
                       lambda: self._show_in_explorer(file_path))
        menu.addAction("🎵 Открыть в плеере",
                       lambda: self._open_in_default_player(file_path))
        menu.addSeparator()
        menu.addAction("📋 Копировать название",
                       lambda: self._copy_title(track['title']))
        menu.exec(self.cover_label.mapToGlobal(pos))

    def _on_playlist_context_menu(self, pos, list_widget):
        item = list_widget.itemAt(pos)
        if not item:
            return

        current_tab = self.tabs.currentIndex()
        if current_tab == 0:
            idx = self.playlist_all.row(item)
        elif current_tab == 1:
            audio_tracks = [i for i, t in enumerate(self.tracks) if t['kind'] == "audio"]
            local_idx = self.playlist_audio.row(item)
            if local_idx < 0 or local_idx >= len(audio_tracks):
                return
            idx = audio_tracks[local_idx]
        else:
            video_tracks = [i for i, t in enumerate(self.tracks) if t['kind'] == "video"]
            local_idx = self.playlist_video.row(item)
            if local_idx < 0 or local_idx >= len(video_tracks):
                return
            idx = video_tracks[local_idx]

        if idx < 0 or idx >= len(self.tracks):
            return

        track = self.tracks[idx]
        file_path = track['file']

        menu = QMenu(self)
        menu.addAction("▶ Играть", lambda: self._play_index(idx))
        menu.addSeparator()
        menu.addAction("📂 Показать в проводнике",
                       lambda: self._show_in_explorer(file_path))
        menu.addAction("🎵 Открыть в плеере",
                       lambda: self._open_in_default_player(file_path))
        menu.addSeparator()
        menu.addAction("📋 Копировать название",
                       lambda: self._copy_title(track['title']))
        menu.exec(list_widget.mapToGlobal(pos))

    def _show_in_explorer(self, file_path):
        import subprocess
        if not os.path.exists(file_path):
            return
        try:
            subprocess.Popen(["explorer", "/select,", os.path.normpath(file_path)])
        except Exception as e:
            print(f"⚠️ Проводник: {e}")

    def _open_in_default_player(self, file_path):
        if not os.path.exists(file_path):
            return
        try:
            os.startfile(file_path)
        except Exception as e:
            print(f"⚠️ Открытие файла: {e}")

    def _copy_title(self, title):
        QApplication.clipboard().setText(title)
        print(f"📋 Скопировано: {title}")

    def _update_track_info(self, track):
        self.title_label.setText(track['title'])
        self.artist_label.setText(os.path.basename(track['file']))

        if track.get('kind') == "video":
            self._current_cover_pixmap = None
            self.cover_label.clear()
            return

        try:
            from mutagen.mp3 import MP3
            from mutagen.id3 import APIC
        except ImportError:
            self._current_cover_pixmap = None
            self.cover_label.clear()
            return

        try:
            audio = MP3(track['file'])
            if audio.tags:
                for tag in audio.tags.values():
                    if isinstance(tag, APIC):
                        pix = QPixmap()
                        pix.loadFromData(tag.data)
                        if not pix.isNull():
                            self._current_cover_pixmap = pix
                            QTimer.singleShot(50, self._render_cover)
                            return
            self._current_cover_pixmap = None
            self.cover_label.clear()
        except Exception as e:
            print(f"⚠️ Обложка: {e}")
            self._current_cover_pixmap = None
            self.cover_label.clear()

    def _render_cover(self):
        if not self._current_cover_pixmap:
            return
        w = self.cover_label.width()
        h = self.cover_label.height()
        if w < 50 or h < 50:
            w = self.cover_container.width()
            h = self.cover_container.height()
        if w < 50 or h < 50:
            return
        scaled = self._current_cover_pixmap.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.cover_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_kind == "audio":
            QTimer.singleShot(50, self._render_cover)
        if self.is_fullscreen and self.overlay.isVisible():
            QTimer.singleShot(20, self._show_overlay)

    def moveEvent(self, event):
        super().moveEvent(event)
        if self.is_fullscreen and self.overlay.isVisible():
            QTimer.singleShot(20, self._show_overlay)

    def showEvent(self, event):
        super().showEvent(event)
        if self.current_kind == "audio":
            QTimer.singleShot(100, self._render_cover)

    def closeEvent(self, event):
        try:
            if self.overlay:
                self.overlay.hide()
                self.overlay.close()
        except Exception:
            pass
        try:
            if self.player is not None:
                self.player.stop()
        except Exception:
            pass
        super().closeEvent(event)