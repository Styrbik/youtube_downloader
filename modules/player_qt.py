"""
Встроенный плеер для MP3 и видео.
- Видео/обложка слева, плейлист справа (как YouTube Music)
- Красный слайдер как в YouTube
- Плавный overlay в fullscreen (для видео И аудио)
- Сворачиваемые папки в плейлисте
- Рандом/next/prev учитывают активную вкладку и свёрнутые папки
- Кроп видео через QGraphicsVideoItem
"""

import os
import random
from collections import OrderedDict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSlider, QSizePolicy, QTabWidget, QMenu,
    QFileDialog, QApplication, QFrame,
    QGraphicsView, QGraphicsScene,
    QDialog, QMessageBox, QProgressBar, QAbstractItemView, QLineEdit,
)
from PyQt6.QtMultimediaWidgets import QGraphicsVideoItem
from PyQt6.QtCore import (
    Qt, QUrl, QTimer, QEvent, QPoint, QRect, QSizeF,
    QPropertyAnimation, QEasingCurve,
)
from PyQt6.QtGui import (
    QPixmap, QFontDatabase, QFont, QShortcut, QKeySequence,
    QCursor, QColor, QPainter, QBrush, QLinearGradient, QPen, QImage,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

# ============================================================
#                    VIDEO VIEW С КРОПОМ
# ============================================================
class CropVideoView(QGraphicsView):
    """Видео вписывается по высоте, контейнер подстраивается по ширине."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._video_item = QGraphicsVideoItem()
        self._scene.addItem(self._video_item)
        self._video_item.nativeSizeChanged.connect(
            self._on_native_size_changed
        )

        self.setStyleSheet("background-color: #000000; border: none;")
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform, True
        )
        self.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )

        self._aspect = 16 / 9
        self._on_mouse_move = None
        self._on_double_click = None
        self._on_click = None

        self._fullscreen_mode = False
        self._updating_width = False

        # В обычном режиме ширина определяется пропорциями видео.
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Expanding,
        )

    @property
    def video_item(self):
        return self._video_item

    def set_fullscreen_mode(self, enabled):
        """В fullscreen видео сохраняет пропорции и помещается на экран."""
        self._fullscreen_mode = enabled

        if enabled:
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
            self.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding,
            )
        else:
            self.setSizePolicy(
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Expanding,
            )
            self._update_container_width()

        self._update_crop()

    def set_aspect(self, aspect: float):
        if aspect > 0:
            self._aspect = aspect
            self._update_container_width()
            self._update_crop()

    def _on_native_size_changed(self, size):
        if size.width() > 0 and size.height() > 0:
            self._aspect = size.width() / size.height()
            self._update_container_width()
            self._update_crop()

    def _update_container_width(self):
        """Подбирает ширину контейнера по его высоте и пропорциям видео."""
        if self._fullscreen_mode or self._updating_width:
            return

        if self._aspect <= 0:
            return

        parent = self.parentWidget()
        if parent is None:
            return

        # В обычном режиме виджет находится в левой колонке плеера.
        player = parent
        left_layout = getattr(player, "left_col", None)

        if left_layout is not None:
            available_width = left_layout.geometry().width()
        else:
            available_width = parent.width()

        height = self.height()

        if available_width < 2 or height < 2:
            return

        # Видео целиком помещается по высоте.
        # Ширина ограничивается доступным местом слева.
        target_width = min(
            int(round(height * self._aspect)),
            available_width,
        )
        target_width = max(1, target_width)

        self._updating_width = True
        self.setFixedWidth(target_width)
        self._updating_width = False

    def _update_crop(self):
        """Сохраняет пропорции видео и обрезает края только при необходимости."""
        vw = self.viewport().width()
        vh = self.viewport().height()

        if vw < 2 or vh < 2 or self._aspect <= 0:
            return

        if self._fullscreen_mode:
            # В fullscreen видео целиком помещается на экран.
            video_w = vw
            video_h = int(round(vw / self._aspect))

            if video_h > vh:
                video_h = vh
                video_w = int(round(vh * self._aspect))
        else:
            # В обычном режиме сохраняется прежнее поведение:
            # видео заполняет контейнер, лишние края обрезаются.
            container_ratio = vw / vh

            if self._aspect >= container_ratio:
                video_h = vh
                video_w = int(round(vh * self._aspect))
            else:
                video_w = vw
                video_h = int(round(vw / self._aspect))

        self._video_item.setSize(QSizeF(video_w, video_h))
        self._video_item.setPos(
            (vw - video_w) / 2,
            (vh - video_h) / 2,
        )

        self._scene.setSceneRect(0, 0, vw, vh)
        self.horizontalScrollBar().setValue(0)
        self.verticalScrollBar().setValue(0)
        self.viewport().update()

    def clear(self):
        """Сбрасывает пропорции для следующего видео."""
        self._aspect = 16 / 9
        self._update_container_width()
        self._update_crop()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if not self._fullscreen_mode:
            self._update_container_width()

        self._update_crop()

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
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self._on_click
        ):
            self._on_click()
        super().mousePressEvent(event)


# ============================================================
#                    КРАСНЫЙ СЛАЙДЕР (YouTube-style)
# ============================================================
class YouTubeSlider(QSlider):
    """Слайдер с красной заливкой слева от handle."""
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setRange(0, 1000)
        self.setMinimumHeight(20)
        self._progress_color = QColor("#ff0000")
        self._bg_color = QColor(255, 255, 255, 50)
        self._handle_color = QColor("#ff0000")
        self._show_handle = True

    def set_progress_color(self, color):
        self._progress_color = QColor(color)
        self.update()

    def set_bg_color(self, color):
        self._bg_color = QColor(color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()
        cy = h // 2
        groove_h = 4

        span = self.maximum() - self.minimum()
        pos_ratio = 0.0 if span == 0 else (self.value() - self.minimum()) / span
        fill_x = int(w * pos_ratio)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._bg_color))
        painter.drawRoundedRect(0, cy - groove_h // 2, w, groove_h,
                                 groove_h // 2, groove_h // 2)

        painter.setBrush(QBrush(self._progress_color))
        if fill_x > 0:
            painter.drawRoundedRect(0, cy - groove_h // 2, fill_x, groove_h,
                                     groove_h // 2, groove_h // 2)

        if self._show_handle:
            handle_r = 6
            painter.setBrush(QBrush(self._handle_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(fill_x, cy), handle_r, handle_r)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setSliderDown(True)
            val = self._pos_to_value(event.position().x())
            self.setValue(val)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            val = self._pos_to_value(event.position().x())
            self.setValue(val)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isSliderDown():
            self.setSliderDown(False)
            self.sliderReleased.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _pos_to_value(self, x):
        w = self.width()
        if w <= 0:
            return self.minimum()
        ratio = max(0.0, min(1.0, x / w))
        return int(self.minimum() + ratio * (self.maximum() - self.minimum()))


# ============================================================
#                    OVERLAY WINDOW
# ============================================================
class OverlayWindow(QWidget):
    """Отдельное frameless-окно поверх полного экрана."""
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
                background-color: rgba(0, 0, 0, 220);
                border-radius: 12px;
            }
        """)
        self.card.setMouseTracking(True)
        outer.addWidget(self.card)

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(10)

        self.filename_label = QLabel("")
        self.filename_label.setStyleSheet(
            "color: #ffffff; font-size: 14px; font-weight: bold; "
            "background: transparent;"
        )
        self.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.filename_label)

        prog_row = QHBoxLayout()
        prog_row.setSpacing(12)

        self.pos_label = QLabel("0:00")
        self.pos_label.setStyleSheet(
            "color: #fff; font-size: 12px; background: transparent;"
        )
        self.pos_label.setFixedWidth(48)
        prog_row.addWidget(self.pos_label)

        self.progress = YouTubeSlider()
        self.progress.sliderReleased.connect(
            lambda: self.parent_player._on_seek(self.progress.value())
        )
        prog_row.addWidget(self.progress, stretch=1)

        self.dur_label = QLabel("0:00")
        self.dur_label.setStyleSheet(
            "color: #fff; font-size: 12px; background: transparent;"
        )
        self.dur_label.setFixedWidth(48)
        prog_row.addWidget(self.dur_label)

        layout.addLayout(prog_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setFixedSize(44, 44)
        self.btn_prev.clicked.connect(self.parent_player._on_prev)
        self._style_btn(self.btn_prev)
        btn_row.addWidget(self.btn_prev)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(60, 60)
        self.btn_play.clicked.connect(self.parent_player._on_play_pause)
        self._style_btn(self.btn_play, big=True)
        btn_row.addWidget(self.btn_play)

        self.btn_next = QPushButton("⏭")
        self.btn_next.setFixedSize(44, 44)
        self.btn_next.clicked.connect(self.parent_player._on_next)
        self._style_btn(self.btn_next)
        btn_row.addWidget(self.btn_next)

        btn_row.addStretch()

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
                height: 5px; border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #e62117; width: 12px;
                margin: -4px 0; border-radius: 6px;
            }
        """)
        btn_row.addWidget(self.volume)

        self.btn_exit = QPushButton("⛶")
        self.btn_exit.setFixedSize(44, 44)
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

    def set_filename(self, name):
        self.filename_label.setText(name)

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
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)

        # ---------- Состояние ----------
        self.tracks = []
        self.current_index = -1
        self.current_kind = None
        self.shuffle_on = False
        self.repeat_mode = 0
        self.is_fullscreen = False
        self._normal_geometry = None

        self._seeking = False
        self._ignore_position = False
        self._repeating = False
        self._last_cursor_pos = None

        self._collapsed_folders = {}
        self._video_aspect = 16 / 9

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
        self.overlay.setWindowOpacity(0.0)

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

        self._update_repeat_icon()

    # ============================================================
    #                    UI
    # ============================================================
    def _build_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(16, 16, 16, 16)
        self.root_layout.setSpacing(10)

        self.header_label = QLabel("🎵 Плеер")
        self.header_label.setStyleSheet(
            f"color: {self._theme['FG']}; font-size: 16px; font-weight: bold;"
        )
        self.root_layout.addWidget(self.header_label)

        # ============================================================
        #        ВЕРХНЯЯ ЧАСТЬ
        # ============================================================
        self.top_layout = QHBoxLayout()
        self.top_layout.setSpacing(12)
        self.root_layout.addLayout(self.top_layout, stretch=1)

        # ---------- ЛЕВАЯ КОЛОНКА ----------
        self.left_col = QVBoxLayout()
        self.left_col.setSpacing(8)
        self.top_layout.addLayout(self.left_col, stretch=2)

        # Видео-виджет с кропом
        self.video_widget = CropVideoView()
        self.video_widget.setMinimumHeight(200)
        self.video_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.video_widget._on_mouse_move = self._on_video_mouse_move
        self.video_widget._on_double_click = self._on_fullscreen_toggle
        self.video_widget._on_click = self._on_video_click
        self.left_col.addWidget(
            self.video_widget,
            stretch=1,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )

        # Подключаем video_item к плееру ОДИН раз
        self.player.setVideoOutput(self.video_widget.video_item)

        # Обложка (для аудио)
        self.cover_label = QLabel()
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.cover_label.setScaledContents(False)
        self.cover_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cover_label.setVisible(False)
        self.cover_label.mouseDoubleClickEvent = self._on_cover_click
        self.cover_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.cover_label.customContextMenuRequested.connect(self._on_cover_context_menu)
        self.left_col.addWidget(self.cover_label, stretch=1)

        self._current_cover_pixmap = None

        # Название + артист
        self.title_label = QLabel("Ничего не выбрано")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(
            f"color: {self._theme['FG']}; font-size: 14px; font-weight: bold;"
        )
        self.title_label.setWordWrap(True)
        self.left_col.addWidget(self.title_label)

        self.artist_label = QLabel("")
        self.artist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.artist_label.setStyleSheet(
            f"color: {self._theme['FG_DIM']}; font-size: 11px;"
        )
        self.left_col.addWidget(self.artist_label)

        # ---------- ПРАВАЯ КОЛОНКА ----------
        self.right_col = QVBoxLayout()
        self.right_col.setSpacing(8)
        self.top_layout.addLayout(self.right_col, stretch=1)

        self.playlist_label = QLabel("Плейлист")
        self.playlist_label.setStyleSheet(
            f"color: {self._theme['FG_DIM']}; font-size: 11px; font-weight: bold;"
        )
        self.right_col.addWidget(self.playlist_label)

        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.right_col.addWidget(self.tabs, stretch=1)

        self.playlist_all = QListWidget()
        self.playlist_all.itemDoubleClicked.connect(self._on_playlist_click)
        self.playlist_all.itemClicked.connect(self._on_playlist_item_clicked)
        self.playlist_all.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_all.customContextMenuRequested.connect(
            lambda pos: self._on_playlist_context_menu(pos, self.playlist_all)
        )
        self.tabs.addTab(self.playlist_all, "🎵 Всё")

        self.playlist_audio = QListWidget()
        self.playlist_audio.itemDoubleClicked.connect(self._on_playlist_click)
        self.playlist_audio.itemClicked.connect(self._on_playlist_item_clicked)
        self.tabs.addTab(self.playlist_audio, "♪ Музыка")

        self.playlist_video = QListWidget()
        self.playlist_video.itemDoubleClicked.connect(self._on_playlist_click)
        self.playlist_video.itemClicked.connect(self._on_playlist_item_clicked)
        self.tabs.addTab(self.playlist_video, "▶ Видео")

        # ============================================================
        #        НИЖНЯЯ ЧАСТЬ
        # ============================================================
        self.bottom_section = QVBoxLayout()
        self.bottom_section.setSpacing(8)
        self.root_layout.addLayout(self.bottom_section)

        # Прогресс
        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)

        self.pos_label = QLabel("0:00")
        self.pos_label.setStyleSheet(
            f"color: {self._theme['FG_DIM']}; font-size: 11px;"
        )
        self.pos_label.setFixedWidth(44)
        progress_row.addWidget(self.pos_label)

        self.progress = YouTubeSlider()
        self.progress.set_progress_color(QColor(self._theme["ACCENT"]))
        self.progress.sliderReleased.connect(
            lambda: self._on_seek(self.progress.value())
        )
        progress_row.addWidget(self.progress, stretch=1)

        self.dur_label = QLabel("0:00")
        self.dur_label.setStyleSheet(
            f"color: {self._theme['FG_DIM']}; font-size: 11px;"
        )
        self.dur_label.setFixedWidth(44)
        progress_row.addWidget(self.dur_label)

        self.bottom_section.addLayout(progress_row)

        # Кнопки
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_folder_audio = QPushButton("🎵 Папка")
        self.btn_folder_audio.clicked.connect(lambda: self._on_choose_folder("audio"))
        btn_row.addWidget(self.btn_folder_audio)

        self.btn_folder_video = QPushButton("🎬 Папка")
        self.btn_folder_video.clicked.connect(lambda: self._on_choose_folder("video"))
        btn_row.addWidget(self.btn_folder_video)

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setFixedWidth(42)
        self.btn_refresh.clicked.connect(self._on_refresh)
        btn_row.addWidget(self.btn_refresh)

        # YT Music — лайкнутые
        self.btn_ytmusic = QPushButton("🎵 YT Music")
        self.btn_ytmusic.setToolTip("Скачать лайкнутые из YouTube Music")
        self.btn_ytmusic.clicked.connect(self._open_ytmusic_picker)
        btn_row.addWidget(self.btn_ytmusic)

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
        self.btn_repeat.setToolTip("Повтор (выкл → один → все)")
        self.btn_repeat.clicked.connect(self._on_repeat_toggle)
        btn_row.addWidget(self.btn_repeat)

        self.btn_fullscreen = QPushButton("⛶")
        self.btn_fullscreen.setFixedSize(42, 42)
        self.btn_fullscreen.setToolTip("На весь экран (F11)")
        self.btn_fullscreen.clicked.connect(self._on_fullscreen_toggle)
        btn_row.addWidget(self.btn_fullscreen)

        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet(
            f"color: {self._theme['FG']}; font-size: 14px;"
        )
        btn_row.addWidget(vol_icon)

        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(70)
        self.volume.setFixedWidth(120)
        self.volume.valueChanged.connect(self._on_volume)
        btn_row.addWidget(self.volume)

        self.btn_show_main = QPushButton("🎬 Качалка")
        self.btn_show_main.setToolTip("Вернуть главное окно")
        self.btn_show_main.clicked.connect(self._show_main_window)
        btn_row.addWidget(self.btn_show_main)

        b_close = QPushButton("Закрыть")
        b_close.clicked.connect(self.close)
        btn_row.addWidget(b_close)

        self.bottom_section.addLayout(btn_row)

    def _on_video_mouse_move(self):
        if self.is_fullscreen:
            self._show_overlay()

    def _on_video_click(self):
        if self.is_fullscreen:
            self._on_play_pause()

    def _show_main_window(self):
        parent = self.parent_app
        if parent is not None:
            parent.show()
            parent.raise_()
            parent.activateWindow()

    def _on_tab_changed(self, index):
        print(f"🔀 Вкладка изменена: {index}")

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
                "BG": "#1e1e1e", "BG_CARD": "#2a2a2a", "BG_INPUT": "#333333",
                "FG": "#e0e0e0", "FG_DIM": "#888888", "ACCENT": "#e62117",
                "ACCENT_HOVER": "#ff3b30", "BORDER": "#3a3a3a",
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
                padding: 6px 10px; margin-right: 2px;
                border-top-left-radius: 6px; border-top-right-radius: 6px;
                font-size: 11px; font-weight: bold;
            }}
            QTabBar::tab:selected {{ background: {t["ACCENT"]}; color: white; }}
            QTabBar::tab:hover {{ background: {t["BORDER"]}; color: {t["FG"]}; }}
        """

    # ============================================================
    #                    FULLSCREEN
    # ============================================================
    def _on_fullscreen_toggle(self):
        if self.current_kind is None:
            print("⚠️ Нет трека для fullscreen")
            return
        if self.is_fullscreen:
            self._exit_fullscreen()
        else:
            self._enter_fullscreen()

    def _enter_fullscreen(self):
        self._normal_geometry = self.geometry()
        self.is_fullscreen = True
        self.video_widget.set_fullscreen_mode(True)
        self._last_cursor_pos = None

        self.header_label.setVisible(False)
        self.title_label.setVisible(False)
        self.artist_label.setVisible(False)

        for i in range(self.bottom_section.count()):
            item = self.bottom_section.itemAt(i)
            if item is None:
                continue
            if item.widget():
                item.widget().setVisible(False)
            elif item.layout():
                for j in range(item.layout().count()):
                    sub = item.layout().itemAt(j)
                    if sub and sub.widget():
                        sub.widget().setVisible(False)

        self.tabs.setVisible(False)
        self.playlist_label.setVisible(False)

        self.left_col.removeWidget(self.video_widget)
        self.left_col.removeWidget(self.cover_label)

        self.video_widget.setParent(None)
        self.cover_label.setParent(None)

        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        if self.current_kind == "video":
            self.root_layout.addWidget(self.video_widget, stretch=1)
            self.video_widget.setVisible(True)
            self.cover_label.setVisible(False)
        else:
            self.root_layout.addWidget(self.cover_label, stretch=1)
            self.video_widget.setVisible(False)
            self.cover_label.setVisible(True)

        self.showFullScreen()

        self._last_cursor_pos = QCursor.pos()
        QTimer.singleShot(100, self._show_overlay)
        self._overlay_watch_timer.start()

        QTimer.singleShot(100, self.video_widget._update_crop)

        if self.current_kind == "audio":
            QTimer.singleShot(100, self._render_cover)

    def _exit_fullscreen(self):
        self._hide_controls_timer.stop()
        self._overlay_watch_timer.stop()
        self._fade_out_overlay()
        self._last_cursor_pos = None

        self.root_layout.removeWidget(self.video_widget)
        self.root_layout.removeWidget(self.cover_label)

        self.video_widget.setParent(None)
        self.cover_label.setParent(None)

        self.left_col.insertWidget(
            0,
            self.video_widget,
            stretch=1,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )
        self.left_col.insertWidget(
            1,
            self.cover_label,
            stretch=1,
            alignment=Qt.AlignmentFlag.AlignHCenter
        )

        if self.current_kind == "video":
            self.video_widget.setVisible(True)
            self.cover_label.setVisible(False)
        else:
            self.video_widget.setVisible(False)
            self.cover_label.setVisible(True)

        self.showNormal()

        if self._normal_geometry:
            self.setGeometry(self._normal_geometry)

        self.is_fullscreen = False
        self.video_widget.set_fullscreen_mode(False)

        self.root_layout.setContentsMargins(16, 16, 16, 16)
        self.root_layout.setSpacing(10)

        self.header_label.setVisible(True)
        self.title_label.setVisible(True)
        self.artist_label.setVisible(True)

        for i in range(self.bottom_section.count()):
            item = self.bottom_section.itemAt(i)

            if item is None:
                continue

            if item.widget():
                item.widget().setVisible(True)

            elif item.layout():
                for j in range(item.layout().count()):
                    sub = item.layout().itemAt(j)

                    if sub and sub.widget():
                        sub.widget().setVisible(True)

        self.tabs.setVisible(True)
        self.playlist_label.setVisible(True)

        QTimer.singleShot(
            150,
            lambda: (
                self.video_widget._update_container_width(),
                self.left_col.setAlignment(
                    self.video_widget,
                    Qt.AlignmentFlag.AlignHCenter
                ),
                self.video_widget._update_crop()
            )
        )

        QTimer.singleShot(
            200,
            self.video_widget._update_crop
        )

        if self.current_kind == "audio":
            QTimer.singleShot(100, self._render_cover)

    # ============================================================
    #                    OVERLAY
    # ============================================================
    def _show_overlay(self):
        if not self.is_fullscreen:
            return

        main_geo = self.geometry()
        ov_height = 160
        ov_width = min(900, main_geo.width() - 80)
        ov_x = main_geo.x() + (main_geo.width() - ov_width) // 2
        ov_y = main_geo.y() + main_geo.height() - ov_height - 40

        self.overlay.setGeometry(ov_x, ov_y, ov_width, ov_height)

        if not self.overlay.isVisible():
            self.overlay.setWindowOpacity(0.0)
            self.overlay.show()
            self.overlay.raise_()
            self._fade_in_overlay()

        self._hide_controls_timer.start(3000)

    def _fade_in_overlay(self):
        self._overlay_fade_in = QPropertyAnimation(self.overlay, b"windowOpacity")
        self._overlay_fade_in.setDuration(250)
        self._overlay_fade_in.setStartValue(self.overlay.windowOpacity())
        self._overlay_fade_in.setEndValue(1.0)
        self._overlay_fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._overlay_fade_in.start()

    def _fade_out_overlay(self):
        if not self.overlay.isVisible():
            return
        self._overlay_fade_out = QPropertyAnimation(self.overlay, b"windowOpacity")
        self._overlay_fade_out.setDuration(250)
        self._overlay_fade_out.setStartValue(self.overlay.windowOpacity())
        self._overlay_fade_out.setEndValue(0.0)
        self._overlay_fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._overlay_fade_out.finished.connect(self.overlay.hide)
        self._overlay_fade_out.start()

    def _schedule_overlay_hide(self):
        if self.is_fullscreen and self.overlay.isVisible():
            self._hide_controls_timer.start(3000)

    def _check_overlay_hover(self):
        if not self.is_fullscreen:
            return

        try:
            cursor_pos = QCursor.pos()
        except Exception:
            return

        if self._last_cursor_pos is None or cursor_pos != self._last_cursor_pos:
            self._last_cursor_pos = cursor_pos

            if not self.overlay.isVisible():
                self._show_overlay()
            else:
                self._hide_controls_timer.start(3000)
            return

        if self.overlay.isVisible():
            ov_geo = self.overlay.geometry()
            if ov_geo.contains(cursor_pos):
                self._hide_controls_timer.start(3000)

    def _auto_hide_controls(self):
        if not self.is_fullscreen:
            return
        self._fade_out_overlay()

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

        self.overlay.set_filename(track['title'])

        if self.current_kind != kind:
            print(f"🔄 Переключаю на {kind}")

            try:
                self.player.stop()
            except Exception:
                pass

            if kind == "video":
                self.video_widget.setVisible(True)
                self.cover_label.setVisible(False)
            else:
                self.video_widget.setVisible(False)
                self.cover_label.setVisible(True)

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
                self.player.play()
                if kind == "video":
                    QTimer.singleShot(150, self.video_widget._update_crop)
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
    #                    ПЕРЕМОТКА
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
            self._ignore_position = True

            current_file = None
            if 0 <= self.current_index < len(self.tracks):
                current_file = self.tracks[self.current_index]['file']

            if not current_file or not os.path.exists(current_file):
                self._seeking = False
                self._ignore_position = False
                return

            QTimer.singleShot(3000, self._force_reset_seeking)

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
                    self._ignore_position = False
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

                QTimer.singleShot(100, self._release_position_lock)

            QTimer.singleShot(50, _step1_set_source)

        except Exception as e:
            print(f"⚠️ Ошибка перемотки: {e}")
            self._seeking = False
            self._ignore_position = False

    def _release_position_lock(self):
        self._seeking = False
        self._ignore_position = False

    def _force_reset_seeking(self):
        if self._seeking or self._ignore_position:
            self._seeking = False
            self._ignore_position = False

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
        if self._ignore_position:
            return

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
        self._update_repeat_icon()

    def _update_repeat_icon(self):
        accent = self._theme["ACCENT"]

        if self.repeat_mode == 0:
            self.btn_repeat.setText("🔁")
            self.btn_repeat.setToolTip("Повтор выключен")
            self.btn_repeat.setStyleSheet("")
        elif self.repeat_mode == 1:
            self.btn_repeat.setText("🔂")
            self.btn_repeat.setToolTip("Повтор одного трека")
            self.btn_repeat.setStyleSheet(
                f"background-color: {accent}; color: white; font-weight: bold;"
            )
        else:
            self.btn_repeat.setText("🔁")
            self.btn_repeat.setToolTip("Повтор всего плейлиста")
            self.btn_repeat.setStyleSheet(
                f"background-color: {accent}; color: white; font-weight: bold;"
            )

    # ============================================================
    #                    ПУЛ ВИДИМЫХ ТРЕКОВ
    # ============================================================
    def _get_visible_tracks(self):
        current_tab = self.tabs.currentIndex()
        if current_tab == 0:
            base = list(self.tracks)
        elif current_tab == 1:
            base = [t for t in self.tracks if t['kind'] == "audio"]
        else:
            base = [t for t in self.tracks if t['kind'] == "video"]

        collapsed = getattr(self, "_collapsed_folders", {})
        if not collapsed:
            return base

        visible = []
        for t in base:
            folder = os.path.dirname(t['file'])
            if collapsed.get(folder, False):
                continue
            visible.append(t)

        return visible

    # ============================================================
    #                    NEXT / PREV
    # ============================================================
    def _get_next_index(self):
        if not self.tracks:
            return -1

        if self.repeat_mode == 1 and self.current_index >= 0:
            return self.current_index

        visible = self._get_visible_tracks()
        if not visible:
            return -1

        current_file = None
        if 0 <= self.current_index < len(self.tracks):
            current_file = self.tracks[self.current_index]['file']

        if self.shuffle_on:
            candidates = [t for t in visible if t['file'] != current_file]
            if not candidates:
                return self.current_index
            chosen = random.choice(candidates)
            for i, t in enumerate(self.tracks):
                if t['file'] == chosen['file']:
                    return i
            return -1

        if current_file is None:
            for i, t in enumerate(self.tracks):
                if t['file'] == visible[0]['file']:
                    return i
            return -1

        current_idx_in_visible = None
        for i, t in enumerate(visible):
            if t['file'] == current_file:
                current_idx_in_visible = i
                break

        if current_idx_in_visible is None:
            for i, t in enumerate(self.tracks):
                if t['file'] == visible[0]['file']:
                    return i
            return -1

        next_idx = current_idx_in_visible + 1
        if next_idx >= len(visible):
            if self.repeat_mode == 2:
                next_idx = 0
            else:
                return -1

        next_file = visible[next_idx]['file']
        for i, t in enumerate(self.tracks):
            if t['file'] == next_file:
                return i
        return -1

    def _get_prev_index(self):
        if not self.tracks:
            return -1

        visible = self._get_visible_tracks()
        if not visible:
            return -1

        current_file = None
        if 0 <= self.current_index < len(self.tracks):
            current_file = self.tracks[self.current_index]['file']

        if self.shuffle_on:
            candidates = [t for t in visible if t['file'] != current_file]
            if not candidates:
                return self.current_index
            chosen = random.choice(candidates)
            for i, t in enumerate(self.tracks):
                if t['file'] == chosen['file']:
                    return i
            return -1

        if current_file is None:
            for i, t in enumerate(self.tracks):
                if t['file'] == visible[-1]['file']:
                    return i
            return -1

        current_idx_in_visible = None
        for i, t in enumerate(visible):
            if t['file'] == current_file:
                current_idx_in_visible = i
                break

        if current_idx_in_visible is None:
            for i, t in enumerate(self.tracks):
                if t['file'] == visible[-1]['file']:
                    return i
            return -1

        prev_idx = current_idx_in_visible - 1
        if prev_idx < 0:
            if self.repeat_mode == 2:
                prev_idx = len(visible) - 1
            else:
                prev_idx = 0

        prev_file = visible[prev_idx]['file']
        for i, t in enumerate(self.tracks):
            if t['file'] == prev_file:
                return i
        return -1

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
        self._populate_grouped(self.playlist_all, self.tracks)

        audio_tracks = [t for t in self.tracks if t['kind'] == "audio"]
        self._populate_grouped(self.playlist_audio, audio_tracks)

        video_tracks = [t for t in self.tracks if t['kind'] == "video"]
        self._populate_grouped(self.playlist_video, video_tracks)

    def _populate_grouped(self, list_widget, tracks):
        list_widget.clear()

        groups = OrderedDict()
        for t in tracks:
            folder = os.path.dirname(t['file'])
            if folder not in groups:
                groups[folder] = []
            groups[folder].append(t)

        sorted_folders = sorted(groups.keys())

        for folder in sorted_folders:
            folder_tracks = groups[folder]
            folder_name = os.path.basename(folder) or folder

            collapsed = self._collapsed_folders.get(folder, False)
            arrow = "▶" if collapsed else "▼"
            header_text = f"{arrow} 📁 {folder_name}  ({len(folder_tracks)})"

            header = QListWidgetItem(header_text)
            header.setForeground(QColor(self._theme["ACCENT"]))
            font = header.font()
            font.setBold(True)
            header.setFont(font)

            header.setData(Qt.ItemDataRole.UserRole, None)
            header.setData(Qt.ItemDataRole.UserRole + 1, folder)
            header.setData(Qt.ItemDataRole.UserRole + 2, "header")

            list_widget.addItem(header)

            if collapsed:
                continue

            for t in folder_tracks:
                icon = "♪" if t['kind'] == "audio" else "▶"
                item = QListWidgetItem(f"     {icon} {t['title']}")
                item.setData(Qt.ItemDataRole.UserRole, t['file'])
                item.setData(Qt.ItemDataRole.UserRole + 2, "track")
                list_widget.addItem(item)

    def _find_track_index_by_item(self, item):
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if not file_path:
            return -1
        for i, t in enumerate(self.tracks):
            if t['file'] == file_path:
                return i
        return -1

    def _on_playlist_click(self, item):
        item_type = item.data(Qt.ItemDataRole.UserRole + 2)
        if item_type != "track":
            return
        idx = self._find_track_index_by_item(item)
        if idx >= 0:
            self._play_index(idx)

    def _on_playlist_item_clicked(self, item):
        item_type = item.data(Qt.ItemDataRole.UserRole + 2)
        if item_type != "header":
            return

        folder = item.data(Qt.ItemDataRole.UserRole + 1)
        if folder is None:
            return

        collapsed = self._collapsed_folders.get(folder, False)
        self._collapsed_folders[folder] = not collapsed

        self._populate_playlists()

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
            subprocess.Popen(["explorer", "/select,", os.path.normpath(file_path)])
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

        item_type = item.data(Qt.ItemDataRole.UserRole + 2)
        if item_type != "track":
            return

        idx = self._find_track_index_by_item(item)
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

    def _update_track_info(self, track):
        self.title_label.setText(track['title'])
        self.artist_label.setText(os.path.basename(track['file']))

        # СБРОС ОБЛОЖКИ ПЕРЕД НОВЫМ ТРЕКОМ
        self._current_cover_pixmap = None
        self.cover_label.clear()

        if track.get('kind') == "video":
            return

        try:
            from mutagen.mp3 import MP3
            from mutagen.id3 import APIC
        except ImportError:
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
        except Exception as e:
            print(f"⚠️ Обложка: {e}")

    def _render_cover(self):
        w = self.cover_label.width()
        h = self.cover_label.height()

        if w < 50 or h < 50:
            return

        if not self._current_cover_pixmap or self._current_cover_pixmap.isNull():
            self.cover_label.clear()
            return

        scaled = self._current_cover_pixmap.scaled(
            w,
            h,
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

        parent = self.parent_app
        if parent is not None and not parent.isVisible():
            print("🎵 Плеер закрыт, главное окно скрыто — выходим")
            QApplication.quit()

        super().closeEvent(event)

    def _open_ytmusic_picker(self):
        dlg = YTMusicPickerDialog(parent_app=self.parent_app, parent_window=self)
        dlg.exec()
        

class YTMusicPickerDialog(QDialog):
    """
    Окно выбора треков из YouTube Music.
    С ExtendedSelection — можно выделять много треков (Ctrl/Shift/мышь).
    """
    def __init__(self, parent_app=None, parent_window=None):
        super().__init__(parent_window)
        self.setWindowTitle("🎵 YouTube Music — Лайкнутые")
        self.setFixedSize(700, 600)
        self.parent_app = parent_app

        self._all_tracks = []       # все загруженные
        self._downloading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Заголовок
        title = QLabel("🎵 Лайкнутые треки из YouTube Music")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        # Поиск/фильтр
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("🔍"))
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Фильтр по названию или артисту...")
        self.filter_input.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.filter_input, stretch=1)
        layout.addLayout(filter_row)

        # Список треков — ExtendedSelection!
        self.list = QListWidget()
        self.list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.list.setIconSize(self.list.iconSize())
        layout.addWidget(self.list, stretch=1)

        # Подсказка
        hint = QLabel(
            "💡 Ctrl+клик — добавить к выбору • Shift+клик — диапазон • "
            "Зажать мышь — протянуть выделение"
        )
        hint.setStyleSheet("color: #888; font-size: 10px; font-style: italic;")
        layout.addWidget(hint)

        # Прогресс
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.status_label)

        # Кнопки
        btn_row = QHBoxLayout()

        self.btn_load = QPushButton("📥 Загрузить лайкнутые")
        self.btn_load.clicked.connect(self._load_liked)
        btn_row.addWidget(self.btn_load)

        self.btn_select_all = QPushButton("☑ Выделить все")
        self.btn_select_all.clicked.connect(self._select_all)
        btn_row.addWidget(self.btn_select_all)

        self.btn_clear_sel = QPushButton("☐ Снять выделение")
        self.btn_clear_sel.clicked.connect(self.list.clearSelection)
        btn_row.addWidget(self.btn_clear_sel)

        btn_row.addStretch()

        self.btn_download = QPushButton("⬇ Скачать выделенные")
        self.btn_download.setObjectName("primary")
        self.btn_download.clicked.connect(self._download_selected)
        self.btn_download.setEnabled(False)
        btn_row.addWidget(self.btn_download)

        b_close = QPushButton("Закрыть")
        b_close.clicked.connect(self.close)
        btn_row.addWidget(b_close)

        layout.addLayout(btn_row)

    def _load_liked(self):
        """Загружает лайкнутые треки."""
        self.btn_load.setEnabled(False)
        self.status_label.setText("⏳ Загружаю лайкнутые...")
        QApplication.processEvents()

        try:
            from modules import ytmusic_library
            tracks = ytmusic_library.get_liked_songs(limit=500)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить:\n{e}")
            self.btn_load.setEnabled(True)
            return

        if not tracks:
            self.status_label.setText("⚠️ Лайкнутых не найдено (проверь куки)")
            self.btn_load.setEnabled(True)
            return

        self._all_tracks = tracks
        self._populate_list(tracks)
        self.status_label.setText(f"✅ Загружено {len(tracks)} треков")
        self.btn_load.setEnabled(True)
        self.btn_download.setEnabled(True)

    def _populate_list(self, tracks):
        """Заполняет список."""
        self.list.clear()
        for t in tracks:
            display = f"{t['title']}"
            if t['artists']:
                display += f" — {t['artists']}"
            if t['duration']:
                display += f"  [{t['duration']}]"

            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, t)
            self.list.addItem(item)

    def _apply_filter(self, text):
        """Фильтрует список по тексту."""
        text = text.strip().lower()
        if not text:
            self._populate_list(self._all_tracks)
            return

        filtered = [
            t for t in self._all_tracks
            if text in t['title'].lower() or text in t['artists'].lower()
        ]
        self._populate_list(filtered)

    def _select_all(self):
        """Выделяет все элементы."""
        self.list.selectAll()

    def _download_selected(self):
        """Скачивает выделенные треки через core.download_audio."""
        selected = self.list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Ничего не выбрано", "Выдели хотя бы один трек.")
            return

        tracks = [item.data(Qt.ItemDataRole.UserRole) for item in selected]

        # Папка
        from modules import settings as _s
        from config import DOWNLOADS_DIR
        output_dir = os.path.join(DOWNLOADS_DIR, "Музыка", "YT Music Liked")
        os.makedirs(output_dir, exist_ok=True)

        self._downloading = True
        self.btn_download.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)

        self._download_queue = tracks
        self._download_index = 0
        self._download_ok = 0
        self._download_fail = 0

        QTimer.singleShot(50, self._download_next)

    def _download_next(self):
        """Берёт следующий трек из очереди и запускает скачивание."""
        if self._download_index >= len(self._download_queue):
            # Готово
            self.progress.setVisible(False)
            self.btn_download.setEnabled(True)
            self._downloading = False
            self.status_label.setText(
                f"✅ Готово: {self._download_ok} ок, {self._download_fail} ошибок"
            )
            QMessageBox.information(
                self, "Готово",
                f"Скачано: {self._download_ok}\nОшибок: {self._download_fail}"
            )
            return

        track = self._download_queue[self._download_index]
        total = len(self._download_queue)
        current = self._download_index + 1

        self.status_label.setText(
            f"⬇ {current}/{total}: {track['title']}"
        )
        self.progress.setValue(int(current / total * 100))
        QApplication.processEvents()

        # Скачивание в отдельном потоке
        import threading
        threading.Thread(
            target=self._download_one, args=(track,), daemon=True
        ).start()

    def _download_one(self, track):
        """Скачивает один трек с полной постобработкой."""
        success = False
        try:
            from modules import core, embed, settings as _s
            from config import DOWNLOADS_DIR, COVER_PATH

            # тот же путь, что в DownloaderApp
            settings_data = self.parent_app.settings if self.parent_app else _s.load()
            base = _s.get_output_dir(settings_data)

            if settings_data.get("auto_sort", False):
                output_dir = os.path.join(
                    base,
                    settings_data.get("sort_audio_dir", "Музыка"),
                    "YT Music Liked",
                )
            else:
                output_dir = os.path.join(base, "YT Music Liked")

            os.makedirs(output_dir, exist_ok=True)

            url = f"https://music.youtube.com/watch?v={track['videoId']}"

            # --- скачиваем ---
            final_path = core.download_audio(
                url,
                format_id=None,
                output_dir=output_dir,
                codec="mp3",
                bitrate="320",
                name_suffix="",
                rename_if_exists=True,
            )

            mp3_path = final_path or embed.find_latest_mp3(output_dir)

            if mp3_path and os.path.exists(mp3_path):
                # --- обложка ---
                thumb = embed.find_thumbnail(mp3_path)
                cover = thumb if thumb else (COVER_PATH if os.path.exists(COVER_PATH) else None)
                if cover:
                    embed.embed_cover(mp3_path, cover)

                # --- метаданные ---
                meta = {
                    "title": track.get("title", ""),
                    "artist": track.get("artists", ""),
                    "album": track.get("album", ""),
                    "upload_date": "",
                    "track": "",
                }
                if settings_data.get("embed_metadata", True):
                    embed.embed_metadata(mp3_path, meta)

                # --- добавляем в историю (чтобы плеер видел) ---
                try:
                    from modules import thumbs
                    thumb_path = thumbs.get_thumb(mp3_path)
                    _s.add_to_history(
                        settings_data, mp3_path,
                        url=url,
                        title=track.get("title", ""),
                        thumb_path=thumb_path,
                    )
                    _s.save(settings_data)
                except Exception as e:
                    print(f"⚠️ История: {e}")

            # --- чистим временные ---
            try:
                embed.cleanup_temp_files(output_dir)
            except Exception:
                pass

            success = True
            print(f"✅ {track['title']}")

        except Exception as e:
            print(f"⚠️ Ошибка {track['title']}: {e}")

        # --- всё в главном потоке ---
        QTimer.singleShot(0, lambda s=success: self._on_one_done(s))

    def _on_one_done(self, success):
        """Обновляет счётчики в главном потоке."""
        if success:
            self._download_ok += 1
        else:
            self._download_fail += 1
        self._download_index += 1
        QTimer.singleShot(50, self._download_next)