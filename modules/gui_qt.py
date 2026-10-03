"""
YouTube Downloader — PyQt6 edition.
С glow-эффектом, тенями, анимациями.
"""
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import sys
import os
import re
import threading
import webbrowser
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yt_dlp
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QScrollArea, QSizePolicy,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QDialog,
    QCheckBox, QRadioButton, QButtonGroup, QListWidget, QListWidgetItem,
    QProgressBar, QMessageBox, QFileDialog, QInputDialog, QMenu,
    QSystemTrayIcon, QTextEdit, QGridLayout, QComboBox, QTabWidget,
    QSlider,
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize, QPoint,
    QParallelAnimationGroup, QSequentialAnimationGroup, pyqtSignal, QRect,
    QObject, QEvent,
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QColor, QPainter, QAction, QFont,
    QLinearGradient, QBrush, QPen, QFontDatabase, QCursor,
)

from modules import core, settings, visual, embed, icon_manager
try:
    from modules.holiday_fx_qt import HolidayLights, HOLIDAY_STYLES
    HAS_HOLIDAY_FX = True
except ImportError:
    HAS_HOLIDAY_FX = False
    from modules import tray as tray_module
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False
from modules.icons import load_thumbnail, make_icon
try:
    from modules.background_widget import BackgroundWidget
    HAS_BACKGROUND = True
except ImportError:
    HAS_BACKGROUND = False
try:
    from modules.frost_fx_qt import FrostFX
    HAS_FROST_FX = True
except ImportError:
    HAS_FROST_FX = False
from modules.themes import THEMES, get_theme
from config import (
    DOWNLOADS_DIR, ICON_PATH, CHANGELOG_PATH, COVER_PATH,
    APP_VERSION, APP_BUILD_NAME, get_active_icon_path,
)

APP_TITLE = f"YouTube Downloader v{APP_VERSION}"

# ============================================================
#                    ЦВЕТА
# ============================================================
BG = "#1e1e1e"
BG_CARD = "#2a2a2a"
BG_INPUT = "#333333"
FG = "#e0e0e0"
FG_DIM = "#888888"
ACCENT = "#e62117"
ACCENT_HOVER = "#ff3b30"
ACCENT_PRESS = "#b71c1c"
BORDER = "#3a3a3a"
TITLEBAR_BG = "#151515"

def enable_acrylic_win10(hwnd, tint_color=(20, 20, 30, 140)):
    """Включает Acrylic (матовое стекло) на Windows 10."""
    import ctypes

    class ACCENT_POLICY(ctypes.Structure):
        _fields_ = [
            ("AccentState", ctypes.c_int),
            ("AccentFlags", ctypes.c_int),
            ("GradientColor", ctypes.c_uint),
            ("AnimationId", ctypes.c_int),
        ]

    class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
        _fields_ = [
            ("Attribute", ctypes.c_int),
            ("Data", ctypes.POINTER(ACCENT_POLICY)),
            ("SizeOfData", ctypes.c_size_t),
        ]

    ACCENT_ENABLE_ACRYLICBLURBEHIND = 4

    r, g, b, a = tint_color
    gradient = (a << 24) | (b << 16) | (g << 8) | r

    accent = ACCENT_POLICY()
    accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
    accent.AccentFlags = 2
    accent.GradientColor = gradient

    data = WINDOWCOMPOSITIONATTRIBDATA()
    data.Attribute = 19  # WCA_ACCENT_POLICY
    data.Data = ctypes.pointer(accent)
    data.SizeOfData = ctypes.sizeof(accent)

    try:
        ctypes.windll.user32.SetWindowCompositionAttribute(
            hwnd, ctypes.byref(data)
        )
        return True
    except Exception as e:
        print(f"⚠️ Acrylic не удалось включить: {e}")
        return False


def disable_acrylic_win10(hwnd):
    """Выключает Acrylic."""
    import ctypes

    class ACCENT_POLICY(ctypes.Structure):
        _fields_ = [
            ("AccentState", ctypes.c_int),
            ("AccentFlags", ctypes.c_int),
            ("GradientColor", ctypes.c_uint),
            ("AnimationId", ctypes.c_int),
        ]

    class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
        _fields_ = [
            ("Attribute", ctypes.c_int),
            ("Data", ctypes.POINTER(ACCENT_POLICY)),
            ("SizeOfData", ctypes.c_size_t),
        ]

    ACCENT_DISABLED = 0

    accent = ACCENT_POLICY()
    accent.AccentState = ACCENT_DISABLED
    accent.AccentFlags = 0
    accent.GradientColor = 0

    data = WINDOWCOMPOSITIONATTRIBDATA()
    data.Attribute = 19
    data.Data = ctypes.pointer(accent)
    data.SizeOfData = ctypes.sizeof(accent)

    try:
        ctypes.windll.user32.SetWindowCompositionAttribute(
            hwnd, ctypes.byref(data)
        )
    except Exception:
        pass

def _hex_to_rgba(hex_color, alpha=1.0):
    """Превращает #RRGGBB в rgba(R, G, B, A)."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def _apply_liquid_glass(enabled, opacity_pct=70, blur_px=20):
    """
    Liquid Glass — прозрачность только для карточек и кнопок.
    Главный BG НЕ трогаем — он сплошной.
    """
    global BG_CARD, BG_INPUT, BORDER, TITLEBAR_BG

    if not enabled:
        return

    alpha = max(0.1, min(1.0, opacity_pct / 100.0))
    soft_alpha = alpha * 0.7
    border_alpha = alpha * 0.35

    BG_CARD = _hex_to_rgba(BG_CARD, alpha)
    BG_INPUT = _hex_to_rgba(BG_INPUT, soft_alpha)
    BORDER = _hex_to_rgba(BORDER, border_alpha)
    TITLEBAR_BG = _hex_to_rgba(TITLEBAR_BG, alpha * 0.9)


def _detect_platform(url):
    u = url.lower()
    if "youtube.com" in u or "youtu.be" in u or "music.youtube" in u:
        return "YouTube"
    if "soundcloud.com" in u:
        return "SoundCloud"
    if "tiktok.com" in u:
        return "TikTok"
    if "rutube.ru" in u:
        return "Rutube"
    if "vk.com" in u or "vkvideo" in u:
        return "VK"
    if "twitter.com" in u or "x.com" in u:
        return "Twitter/X"
    if "instagram.com" in u:
        return "Instagram"
    if "vimeo.com" in u:
        return "Vimeo"
    return "сайт"


def _apply_theme(theme_name):
    global BG, BG_CARD, BG_INPUT, FG, FG_DIM, ACCENT, ACCENT_HOVER, ACCENT_PRESS, BORDER, TITLEBAR_BG
    t = get_theme(theme_name)
    BG = t["BG"]
    BG_CARD = t["BG_CARD"]
    BG_INPUT = t["BG_INPUT"]
    FG = t["FG"]
    FG_DIM = t["FG_DIM"]
    ACCENT = t["ACCENT"]
    ACCENT_HOVER = t["ACCENT_HOVER"]
    ACCENT_PRESS = t["ACCENT_PRESS"]
    BORDER = t["BORDER"]

    def _darker(hex_color, factor=0.7):
        h = hex_color.lstrip("#")
        r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
        return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"

    TITLEBAR_BG = _darker(BG, 0.7)


def build_qss():
    print(f"DEBUG BG={BG}, BG_CARD={BG_CARD}, BORDER={BORDER}")
    return f"""
        QMainWindow {{
            background-color: {BG};
            color: {FG};
            font-family: "Segoe UI", "Segoe UI Emoji";
        }}
        QWidget {{
            background-color: {BG};
            color: {FG};
            font-family: "Segoe UI", "Segoe UI Emoji";
        }}
        QLabel {{ background: transparent; }}
        QFrame#card {{
            background-color: {BG_CARD};
            border: 1px solid {BORDER};
             border-radius: 12px;
        }}
        QFrame#card:hover {{ border: 1px solid {ACCENT}; }}
        QLineEdit {{
            background-color: {BG_INPUT};
            color: {FG};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 13px;
            selection-background-color: {ACCENT};
        }}
        QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
        QPushButton {{
            background-color: {BG_CARD};
            color: {FG};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {BORDER};
            border: 1px solid {ACCENT};
        }}
        QPushButton#primary {{
            background-color: {ACCENT};
            color: white;
            border: none;
            font-weight: bold;
        }}
        QPushButton#primary:hover {{ background-color: {ACCENT_HOVER}; }}
        QPushButton#primary:pressed {{ background-color: {ACCENT_PRESS}; }}
        QPushButton#glow_btn {{
            background-color: {BG_CARD};
            color: {FG};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
        }}
        QPushButton#glow_btn:hover {{ border: 1px solid {ACCENT}; }}
        QPushButton#glow_btn_primary {{
            background-color: {ACCENT};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: bold;
        }}
        QPushButton#glow_btn_primary:hover {{ background-color: {ACCENT_HOVER}; }}
        QPushButton#titlebtn {{
            background-color: {TITLEBAR_BG};
            border: none;
            border-radius: 0;
            padding: 6px 14px;
            font-size: 14px;
            font-family: "Segoe UI Symbol";
        }}
        QPushButton#titlebtn:hover {{ background-color: {BG_CARD}; }}
        QPushButton#closebtn {{
            background-color: {TITLEBAR_BG};
            border: none;
            border-radius: 0;
            padding: 6px 14px;
            font-size: 14px;
            font-family: "Segoe UI Symbol";
        }}
        QPushButton#closebtn:hover {{ background-color: #c0392b; color: white; }}
        QListWidget {{
            background-color: {BG_INPUT};
            color: {FG};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 4px;
        }}
        QListWidget::item {{ padding: 6px 8px; border-radius: 4px; }}
        QListWidget::item:hover {{ background-color: {BORDER}; }}
        QListWidget::item:selected {{ background-color: {ACCENT}; color: white; }}
        QProgressBar {{
            background-color: {BG_CARD};
            border: none;
            border-radius: 6px;
            height: 12px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            border-radius: 6px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {ACCENT}, stop:1 {ACCENT_HOVER});
        }}
        QCheckBox, QRadioButton {{ spacing: 8px; padding: 4px; }}
        QCheckBox::indicator, QRadioButton::indicator {{ width: 16px; height: 16px; }}
        QCheckBox::indicator:unchecked {{
            background-color: {BG_INPUT}; border: 1px solid {BORDER}; border-radius: 3px;
        }}
        QCheckBox::indicator:checked {{
            background-color: {ACCENT}; border: 1px solid {ACCENT}; border-radius: 3px;
        }}
        QRadioButton::indicator:unchecked {{
            background-color: {BG_INPUT}; border: 1px solid {BORDER}; border-radius: 8px;
        }}
        QRadioButton::indicator:checked {{
            background-color: {ACCENT}; border: 1px solid {ACCENT}; border-radius: 8px;
        }}
        QScrollArea {{ background-color: {BG}; border: none; }}
        QScrollBar:vertical {{
            background-color: {BG}; width: 10px; border: none;
        }}
        QScrollBar::handle:vertical {{
            background-color: {BORDER}; border-radius: 5px; min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{ background-color: {ACCENT}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            background: none; height: 0;
        }}
        QTextEdit {{
            background-color: {BG_INPUT}; color: {FG};
            border: 1px solid {BORDER}; border-radius: 8px; padding: 8px;
        }}
    """


# ============================================================
#                    АНИМАЦИИ
# ============================================================

def add_shadow(widget, color="#000000", blur=20, offset=(0, 4), opacity=120):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setColor(QColor(color))
    effect.setOffset(offset[0], offset[1])
    try:
        effect.setOpacity(opacity / 255)
    except Exception:
        pass
    widget.setGraphicsEffect(effect)
    return effect


def animate_slide_in(widget, offset_y=20, duration=400):
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity")
    anim.setDuration(duration)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start()
    widget._opacity_anim = anim
    return anim
    
class AchievementsDialog(QDialog):
    """Окно достижений."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🏆 Достижения")
        self.setFixedSize(600, 720)
        self.parent_app = parent

        from modules import achievements as ach_mod

        # скролл на всю панель
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        outer.addWidget(scroll)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        scroll.setWidget(inner)

        # заголовок + прогресс
        settings_data = self.parent_app.settings
        unlocked = ach_mod.get_unlocked_count(settings_data)
        total = ach_mod.get_total_count()

        title = QLabel(f"🏆 Достижения  [{unlocked}/{total}]")
        title.setStyleSheet(f"color: {FG}; font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # прогресс-бар
        progress = QProgressBar()
        progress.setRange(0, total)
        progress.setValue(unlocked)
        progress.setTextVisible(False)
        progress.setFixedHeight(12)
        layout.addWidget(progress)

        # группируем по категориям
        categories = {
            "download": "📥 Скачивание",
            "audio": "🎵 Аудио",
            "video": "🎬 Видео",
            "theme": "🎨 Темы",
            "holiday": "🎄 Праздники",
            "time": "⏰ Время",
            "secret": "🎮 Секретные",
        }

        for cat_key, cat_name in categories.items():
            # заголовок категории
            cat_label = QLabel(cat_name)
            cat_label.setStyleSheet(f"color: {FG}; font-size: 14px; font-weight: bold; padding-top: 10px;")
            layout.addWidget(cat_label)

            # достижения в категории
            for ach_id, ach in ach_mod.ACHIEVEMENTS.items():
                if ach.get("category") != cat_key:
                    continue

                is_open = ach_mod.is_unlocked(settings_data, ach_id)
                progress_val = ach_mod.get_progress(settings_data, ach_id)
                target = ach["target"]

                # карточка
                card = QFrame()
                card.setObjectName("card")
                card.setStyleSheet(f"""
                    QFrame#card {{
                        background-color: {BG_CARD};
                        border: 1px solid {BORDER};
                        border-radius: 10px;
                    }}
                """)

                card_layout = QHBoxLayout(card)
                card_layout.setContentsMargins(14, 10, 14, 10)
                card_layout.setSpacing(10)

                # иконка статуса
                status_icon = QLabel("✓" if is_open else "🔒")
                status_icon.setStyleSheet(
                    f"color: {'#4ade80' if is_open else FG_DIM}; "
                    f"font-size: 20px; font-weight: bold;"
                )
                status_icon.setFixedWidth(30)
                card_layout.addWidget(status_icon)

                # текст
                text_col = QVBoxLayout()
                text_col.setSpacing(2)

                name_label = QLabel(ach["name"])
                name_label.setStyleSheet(
                    f"color: {FG if is_open else FG_DIM}; "
                    f"font-size: 13px; font-weight: bold;"
                )
                text_col.addWidget(name_label)

                desc_label = QLabel(ach["desc"])
                desc_label.setStyleSheet(
                    f"color: {FG_DIM}; font-size: 11px;"
                )
                text_col.addWidget(desc_label)

                card_layout.addLayout(text_col, stretch=1)

                # прогресс (если не открыто и target > 1)
                if not is_open and target > 1:
                    prog_label = QLabel(f"{progress_val}/{target}")
                    prog_label.setStyleSheet(
                        f"color: {FG_DIM}; font-size: 11px; font-weight: bold;"
                    )
                    card_layout.addWidget(prog_label)
                elif is_open:
                    done_label = QLabel("✓")
                    done_label.setStyleSheet(
                        f"color: #4ade80; font-size: 14px; font-weight: bold;"
                    )
                    card_layout.addWidget(done_label)

                layout.addWidget(card)

        layout.addStretch()

        # кнопки
        btn_row = QHBoxLayout()

        b_reset = QPushButton("🗑 Сбросить все")
        b_reset.clicked.connect(self._reset_all)
        btn_row.addWidget(b_reset)

        btn_row.addStretch()

        b_close = QPushButton("Закрыть")
        b_close.clicked.connect(self.accept)
        btn_row.addWidget(b_close)

        layout.addLayout(btn_row)

    def _reset_all(self):
        reply = QMessageBox.question(
            self, "Сброс",
            "Сбросить ВСЕ достижения?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            from modules import achievements as ach_mod
            from modules import settings as settings_mod
            ach_mod.reset_all(self.parent_app.settings)
            settings_mod.save(self.parent_app.settings)
            QMessageBox.information(self, "Готово", "Достижения сброшены.")
            self.accept()
            QTimer.singleShot(50, lambda: AchievementsDialog(self.parent_app).exec())


# ============================================================
#                    GLOW-КНОПКА
# ============================================================
class GlowButton(QPushButton):
    """Кнопка с glow-эффектом от курсора (как Focus Highlight в Win10)."""
    def __init__(self, text, parent=None, is_primary=False, **kwargs):
        super().__init__(text, parent)
        self.is_primary = is_primary
        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setOffset(0, 0)
        self._glow.setBlurRadius(0)
        self._glow.setColor(QColor(ACCENT))
        self._glow.setEnabled(False)
        self.setGraphicsEffect(self._glow)

        self._base_blur = 24 if is_primary else 16
        self._max_blur = 45 if is_primary else 30
        self._target_blur = 0
        self._anim = QPropertyAnimation(self._glow, b"blurRadius")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.clicked.connect(self._play_click_sound)
        
    def _play_click_sound(self):
        """Играет клик или хруст льда (для Frostmourne)."""
        try:
            from modules import settings as _s
            _settings = _s.load()
            theme = _settings.get("theme", "dark")
            forced = _settings.get("admin_forced_holiday")
            if theme == "frostmourne" or forced == "frostmourne":
                from modules.sounds import ice_crack
                ice_crack()
            else:
                from modules.sounds import click
                click()
        except Exception:
            pass


    def set_glow(self, value):
        """value: 0.0 — 1.0."""
        target = int(self._base_blur + (self._max_blur - self._base_blur) * value)
        if target == self._target_blur:
            return
        self._target_blur = target
        if target > 0:
            self._glow.setEnabled(True)
            self._glow.setColor(QColor(ACCENT))
        else:
            self._glow.setEnabled(False)
        self._anim.stop()
        self._anim.setStartValue(self._glow.blurRadius())
        self._anim.setEndValue(target)
        self._anim.start()
        
# ============================================================
#                    КАРТОЧКА С ТЕНЬЮ
# ============================================================
class Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 12, 14, 12)
        self._layout.setSpacing(8)
        # тень на карточке
        self._shadow = add_shadow(self, color="#000000", blur=20, offset=(0, 4), opacity=100)

        # Liquid Glass — дополнительная тень, если включён
        self._apply_liquid_shadow()

    def _apply_liquid_shadow(self):
        """Если Liquid Glass — добавить мягкое свечение."""
        try:
            from modules import settings as _s
            s = _s.load()
            if s.get("liquid_glass", False):
                blur_px = s.get("liquid_blur", 20)
                # тень от стекла
                shadow = QGraphicsDropShadowEffect(self)
                shadow.setBlurRadius(blur_px + 10)
                shadow.setColor(QColor(255, 255, 255, 30))
                shadow.setOffset(0, 0)
                self.setGraphicsEffect(shadow)
        except Exception:
            pass

    def add(self, w):
        self._layout.addWidget(w)
        return w

    def add_layout(self, l):
        self._layout.addLayout(l)
        return l
        self._layout.setContentsMargins(14, 12, 14, 12)
        self._layout.setSpacing(8)
        # тень на карточке
        self._shadow = add_shadow(self, color="#000000", blur=20, offset=(0, 4), opacity=100)


# ============================================================
#                    КНОПКА КАЧЕСТВА
# ============================================================
class QualityButton(QPushButton):
    def __init__(self, text, value, group):
        super().__init__(text)
        self.value = value
        self.group = group
        self.selected = False
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(32)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.clicked.connect(self._on_click)
        self._refresh_style()

    def _on_click(self):
        self.group.select(self.value)

    def _refresh_style(self):
        if self.selected:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ACCENT};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 6px 10px;
                    font-family: "Consolas", monospace;
                    font-size: 11px;
                    font-weight: bold;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {BG_CARD};
                    color: {FG};
                    border: 1px solid {BORDER};
                    border-radius: 8px;
                    padding: 6px 10px;
                    font-family: "Consolas", monospace;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    border: 1px solid {ACCENT};
                    background-color: {BG_INPUT};
                }}
            """)

    def set_selected(self, selected):
        self.selected = selected
        self.setChecked(selected)
        self._refresh_style()


class QualityGroup(QWidget):
    def __init__(self, on_change=None, columns=3, parent=None):
        super().__init__(parent)
        self.on_change = on_change
        self.columns = columns
        self.buttons = {}
        self.selected = None
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)

    def set_items(self, items):
        while self._layout.count():
            child = self._layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.buttons.clear()
        self.selected = None

        for idx, (label, value) in enumerate(items):
            row = idx // self.columns
            col = idx % self.columns
            btn = QualityButton(label, value, self)
            self._layout.addWidget(btn, row, col)
            self.buttons[value] = btn

        if items:
            self.select(items[0][1], silent=True)

    def select(self, value, silent=False):
        if value not in self.buttons:
            return
        for v, btn in self.buttons.items():
            btn.set_selected(v == value)
        self.selected = value
        if self.on_change and not silent:
            self.on_change(value)

    def clear(self):
        self.set_items([])
        
class ClickSoundFilter(QObject):
    """Глобальный фильтр — играет звук при клике на любую кнопку/радио."""

    def eventFilter(self, obj, event):
        if event.type() == event.Type.MouseButtonPress:
            # ловим кнопки, радио, чекбоксы
            from PyQt6.QtWidgets import QPushButton, QRadioButton, QCheckBox
            if isinstance(obj, (QPushButton, QRadioButton, QCheckBox)):
                try:
                    from modules import settings as _s
                    _settings = _s.load()
                    theme = _settings.get("theme", "dark")
                    forced = _settings.get("admin_forced_holiday")
                    if theme == "frostmourne" or forced == "frostmourne":
                        from modules.sounds import ice_crack
                        ice_crack()
                    else:
                        from modules.sounds import click
                        click()
                except Exception:
                    pass
        return super().eventFilter(obj, event)


# ============================================================
#                    ГЛАВНОЕ ОКНО
# ============================================================
class DownloaderApp(QMainWindow):
    sig_populate = pyqtSignal(str, str)
    sig_error = pyqtSignal(str)
    sig_progress = pyqtSignal(float)
    sig_info = pyqtSignal(float, object)
    sig_thumb = pyqtSignal(bytes)

    def __init__(self):
        super().__init__()
        self.settings = settings.load()
        self._admin_mode = self.settings.get("admin_mode", False)
        # в начале __init__ после settings.load()
        liquid = self.settings.get("liquid_glass", False)

        # WA_TranslucentBackground не нужен — Acrylic работает без него
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.sig_populate.connect(self._populate_formats)
        self.sig_error.connect(self._fetch_error)
        self.sig_progress.connect(self._set_progress)
        self.sig_info.connect(self._update_info)
        self.sig_thumb.connect(self._set_thumb)
        self._fetch_in_progress = False
        self._glow_buttons = []

        today = datetime.now()
        self._holiday_mode = False
        self._holiday_theme = None
        self._holiday_greeting = None
        self._real_theme = self.settings.get("theme", "dark")
        self._falling_fx = None
        self._holiday_lights = None
        self._frost_fx = None

        if today.month == 10 and today.day == 31:
            self._holiday_mode = True
            self._holiday_theme = "halloween"
            self._holiday_greeting = "🎃 С ХЭЛЛОУИНОМ!\nНе забудь про конфеты!"
        elif today.month == 12 and today.day == 21:
            self._holiday_mode = True
            self._holiday_theme = "doomsday"
            self._holiday_greeting = "💀 21 ДЕКАБРЯ — КОНЕЦ СВЕТА!\nКачай, пока интернет не отключили!"
        elif today.month == 12 and today.day == 31:
            self._holiday_mode = True
            self._holiday_theme = "newyear"
            self._holiday_greeting = "🎄 С НОВЫМ ГОДОМ!\nПусть качается всё, что хочется!"
        elif today.month == 3 and today.day == 8:
            self._holiday_mode = True
            self._holiday_theme = "march8"
            self._holiday_greeting = "🌸 С 8 МАРТА!\nСкачай что-нибудь для мамы!"
        elif today.month == 9 and today.day == 1:
            self._holiday_mode = True
            self._holiday_theme = "september1"
            self._holiday_greeting = "🎒 С ДНЁМ ЗНАНИЙ!\nУчись, но не забывай качать!"
        elif today.month == 2 and today.day == 14:
            self._holiday_mode = True
            self._holiday_theme = "feb14"
            self._holiday_greeting = "❤️ С ДНЁМ ВЛЮБЛЁННЫХ!\nСкачай что-нибудь для второй половинки!"
        elif today.month == 4 and today.day == 12:
            self._holiday_mode = True
            self._holiday_theme = "april12"
            self._holiday_greeting = "🚀 С ДНЁМ КОСМОНАВТИКИ!\nПоехали!"
        elif today.month == 5 and today.day == 1:
            self._holiday_mode = True
            self._holiday_theme = "may1"
            self._holiday_greeting = "🎉 С ПРАЗДНИКОМ ВЕСНЫ И ТРУДА!\nОтдыхай и качай!"

        # админ-форсированный праздник
        forced = self.settings.get("admin_forced_holiday")
        if forced:
            self._holiday_mode = True
            self._holiday_theme = forced
            self._holiday_greeting = f"🎄 Тест: {forced}"

        theme_to_apply = self._holiday_theme if self._holiday_mode else self._real_theme
        _apply_theme(theme_to_apply)
        
        # если тема Frostmourne — играем "К чёрту людей!"
        if self._real_theme == "frostmourne" or self._holiday_theme == "frostmourne":
            QTimer.singleShot(1500, self._play_frostmourne_greeting)

        # Liquid Glass — прозрачность только для карточек и кнопок
        if self.settings.get("liquid_glass", False):
            _apply_liquid_glass(
                True,
                self.settings.get("liquid_opacity", 70),
                self.settings.get("liquid_blur", 20),
            )

        # заголовок зависит от темы
        if self._holiday_theme == "frostmourne" or self._real_theme == "frostmourne":
            self.setWindowTitle("❄️ Frostmourne Hungers")
        else:
            self.setWindowTitle(APP_TITLE)
        if self.settings.get("liquid_glass", False):
            # для Acrylic нужен обычный frameless, но с прозрачным фоном
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        else:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        saved_geom = self.settings.get("window_geometry", "")
        w, h = self._pick_size(saved_geom)
        self.resize(w, h)
        self.setMinimumSize(700, 500)

        active_icon = get_active_icon_path()
        if os.path.exists(active_icon):
            self.setWindowIcon(QIcon(active_icon))
        self._active_icon_path = active_icon

        self.current_url = ""
        self.formats = []
        self.title_text = ""
        self.meta = {}
        self.selected_format = None
        self.downloading = False
        self._silent = False
        self._rename_flag = False
        self._last_downloaded_file = None
        self._drag_pos = None
        self._is_maximized = False
        self._thumb_pixmap = None
        self._tray_icon = None
        self._saved_geometry = None
        self._minimize_anim_running = False
        self._restore_anim_running = False

        self._build_ui()
        self._apply_qss()
        self._on_mode_change()
        self._create_tray()

        if self._holiday_mode and self._holiday_greeting:
            QTimer.singleShot(1500, self._show_holiday_toast)

        if self._holiday_mode and HAS_BACKGROUND:
            # праздник — запускаем фон с гирляндой и эмодзи
            QTimer.singleShot(300, self._apply_holiday_background)

        if self.settings.get("auto_update_ytdlp", True):
            threading.Thread(target=self._check_ytdlp_update, daemon=True).start()

        QTimer.singleShot(100, self._cascade_animate)
        # QTimer.singleShot(800, self._check_cookies_on_start)

        # таймер для обновления glow от курсора
        self.setMouseTracking(True)
        self.centralWidget().setMouseTracking(True)
        self._glow_timer = QTimer(self)
        self._glow_timer.setInterval(30)
        self._glow_timer.timeout.connect(self._update_glow)
        self._glow_timer.start()
        # глобальный фильтр кликов — для звука на всех кнопках
        self._click_filter = ClickSoundFilter(self)
        QApplication.instance().installEventFilter(self._click_filter)
        # глобальный фильтр кликов — для звука
        self._click_filter = ClickSoundFilter(self)
        QApplication.instance().installEventFilter(self._click_filter)

    def _check_cookies_on_start(self):
        # Куки отключены — модуль переименован
        pass
    def _open_admin_panel(self):
        """Открывает админ-панель."""
        # достижения: админка
        try:
            from modules import achievements as ach_mod
            unlocked = ach_mod.track_admin(self.settings)
            for ach_id in unlocked:
                ach = ach_mod.ACHIEVEMENTS.get(ach_id, {})
                name = ach.get("name", ach_id)
                QTimer.singleShot(500, lambda n=name: QtToast(
                    self, f"🏆 Достижение: {n}", duration=4000
                ))
        except Exception as e:
            print(f"⚠️ Достижения (админка): {e}")

        AdminPanelDialog(self).exec()
    
    def _open_achievements(self):
        """Открывает окно достижений."""
        AchievementsDialog(self).exec()
        
    def changeEvent(self, event):
        """Ловим разворачивание из панели задач для анимации."""
        if event.type() == event.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                # окно сворачивается — анимацию делает _animate_minimize
                pass
            else:
                # окно разворачивается — анимируем
                if not getattr(self, "_restore_anim_running", False):
                    self._animate_restore()
        # при восстановлении — перезапускаем падающие
        if getattr(self, "_holiday_mode", False) and getattr(self, "_falling_fx", None):
            if not self._falling_fx.isVisible():
                QTimer.singleShot(100, self._restart_falling_fx)
            else:
                try:
                    parent = self.centralWidget()
                    self._falling_fx.setGeometry(parent.rect())
                    self._falling_fx.raise_()
                except Exception:
                    pass
                    
        super().changeEvent(event)

    def _animate_restore(self):
        """Плавное разворачивание — только opacity."""
        if self._restore_anim_running:
            return
        self._restore_anim_running = True

        # ← восстанавливаем состояние maximized/normal
        if getattr(self, "_was_maximized", False):
            self.showMaximized()
            self._is_maximized = True
        else:
            # если НЕ был максимизирован — возвращаем сохранённую геометрию
            if self._saved_geometry is not None:
                self.setGeometry(self._saved_geometry)
            self._is_maximized = False

        # fade-in
        self.setWindowOpacity(0.0)
        self._restore_opacity = QPropertyAnimation(self, b"windowOpacity")
        self._restore_opacity.setDuration(150)
        self._restore_opacity.setStartValue(0.0)
        self._restore_opacity.setEndValue(1.0)
        self._restore_opacity.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _done():
            self.setWindowOpacity(1.0)
            self._restore_anim_running = False

        self._restore_opacity.finished.connect(_done)
        self._restore_opacity.start()
        self._restore_anim = self._restore_opacity

    # ---------- glow ----------
    def _update_glow(self):
        """Обновляет свечение кнопок в зависимости от позиции курсора."""
        if not self._glow_buttons:
            return
        if not self.isActiveWindow():
            for btn in self._glow_buttons:
                btn.set_glow(0.0)
            return

        pos = self.mapFromGlobal(QCursor.pos())

        for btn in self._glow_buttons:
            btn_pos = btn.mapTo(self, QPoint(0, 0))
            btn_rect = QRect(btn_pos, btn.size())

            dx = max(btn_rect.left() - pos.x(), 0, pos.x() - btn_rect.right())
            dy = max(btn_rect.top() - pos.y(), 0, pos.y() - btn_rect.bottom())
            dist = (dx*dx + dy*dy) ** 0.5

            influence_radius = 140
            if dist > influence_radius:
                intensity = 0.0
            else:
                intensity = 1.0 - (dist / influence_radius)
                intensity = intensity ** 2

            btn.set_glow(intensity)

    def _pick_size(self, saved_geom):
        default_w, default_h = 900, 640
        w, h = default_w, default_h
        if saved_geom:
            try:
                size_part = saved_geom.split("+")[0]
                sw_, sh_ = map(int, size_part.split("x"))
                if sw_ >= 400 and sh_ >= 400:
                    w, h = sw_, sh_
            except Exception:
                pass

        screen = QApplication.primaryScreen().availableGeometry()
        w = min(w, screen.width() - 20)
        h = min(h, screen.height() - 20)
        self.move(
            screen.x() + (screen.width() - w) // 2,
            screen.y() + (screen.height() - h) // 2,
        )
        return w, h

    def _apply_qss(self):
        self.setStyleSheet(build_qss())
        # сообщаем BackgroundWidget текущий цвет фона
        if HAS_BACKGROUND and hasattr(self, "_central_bg"):
            try:
                self._central_bg.set_bg_color(BG)
            except Exception:
                pass

    def _cascade_animate(self):
        for i, card in enumerate((
            getattr(self, "url_card", None),
            getattr(self, "dir_card", None),
            getattr(self, "opts_card", None),
            getattr(self, "mode_card", None),
            getattr(self, "info_card", None),
            getattr(self, "fmt_card", None),
        )):
            if card:
                QTimer.singleShot(i * 60, lambda c=card: animate_slide_in(c, duration=400))
                
    # --------------------------------------------------------
    #                    UI
    # --------------------------------------------------------
    def _build_ui(self):
        if HAS_BACKGROUND:
            central = BackgroundWidget(bg_color=BG)
        else:
            central = QWidget()
        self.setCentralWidget(central)
        self._central_bg = central
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ----- Titlebar -----
        self.titlebar = QWidget()
        self.titlebar.setFixedHeight(36)
        self.titlebar.setStyleSheet(f"background-color: {TITLEBAR_BG};")
        tb_layout = QHBoxLayout(self.titlebar)
        tb_layout.setContentsMargins(10, 0, 0, 0)
        tb_layout.setSpacing(4)

        icon_text = "🎬"
        if self._holiday_theme == "frostmourne" or self._real_theme == "frostmourne":
            icon_text = "❄️"
        tb_icon = QLabel(icon_text)
        tb_icon.setStyleSheet(f"color: {ACCENT}; font-size: 14px; background: transparent;")
        tb_layout.addWidget(tb_icon)

        # заголовок в шапке — зависит от темы
        title_text = "YouTube Downloader"
        if self._holiday_theme == "frostmourne" or self._real_theme == "frostmourne":
            title_text = "❄️ Frostmourne"
        tb_title = QLabel(title_text)
        tb_title.setStyleSheet(f"color: {FG}; font-size: 12px; font-weight: bold; background: transparent;")
        tb_layout.addWidget(tb_title)
        tb_layout.addStretch()

        def _menu_btn(text, slot, tooltip=""):
            b = QPushButton(text)
            b.setObjectName("titlebtn")
            b.setFixedHeight(28)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"""
                QPushButton {{
                    background-color: {TITLEBAR_BG};
                    color: {FG};
                    border: none;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {BG_CARD};
                    color: {ACCENT};
                }}
            """)
            if tooltip:
                b.setToolTip(tooltip)
            b.clicked.connect(slot)
            return b

        tb_layout.addWidget(_menu_btn("📜 История", self._open_history, "История скачанного"))
        tb_layout.addWidget(_menu_btn("🎨 Тема", self._change_theme, "Сменить тему"))
        tb_layout.addWidget(_menu_btn("🎯 Профили", self._open_profiles, "Профили настроек"))
        tb_layout.addWidget(_menu_btn("⚙️ Настройки", self._open_settings, "Настройки"))
        tb_layout.addWidget(_menu_btn("🎵 Плеер", self._open_player, "Встроенный плеер"))
        tb_layout.addWidget(_menu_btn("📋 Что нового", self._open_changelog, "Changelog"))
        tb_layout.addWidget(_menu_btn("🏆 Достижения", self._open_achievements, "Достижения"))
        if getattr(self, "_admin_mode", False):
            tb_layout.addWidget(_menu_btn("🔧 Админка", self._open_admin_panel, "Админ-панель"))

        spacer = QWidget()
        spacer.setFixedWidth(10)
        spacer.setStyleSheet("background: transparent;")
        tb_layout.addWidget(spacer)

        self.btn_min = QPushButton("─")
        self.btn_min.setObjectName("titlebtn")
        self.btn_min.setFixedSize(40, 36)
        self.btn_min.clicked.connect(self._minimize_to_tray)
        tb_layout.addWidget(self.btn_min)

        self.btn_max = QPushButton("◻")
        self.btn_max.setObjectName("titlebtn")
        self.btn_max.setFixedSize(40, 36)
        self.btn_max.clicked.connect(self._toggle_maximize)
        tb_layout.addWidget(self.btn_max)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("closebtn")
        self.btn_close.setFixedSize(40, 36)
        self.btn_close.clicked.connect(self._on_close)
        tb_layout.addWidget(self.btn_close)

        self.titlebar.mousePressEvent = self._titlebar_press
        self.titlebar.mouseMoveEvent = self._titlebar_move
        self.titlebar.mouseDoubleClickEvent = lambda e: self._toggle_maximize()

        root_layout.addWidget(self.titlebar)

        # ----- Градиентная чёлка -----
        self.cheek = QWidget()
        self.cheek.setFixedHeight(3)
        self.cheek.paintEvent = self._paint_cheek
        root_layout.addWidget(self.cheek)

        # ----- Скролл -----
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root_layout.addWidget(self._scroll, stretch=1)
        scroll = self._scroll

        self.content = QWidget()
        scroll.setWidget(self.content)
        content_layout = QHBoxLayout(self.content)
        content_layout.setContentsMargins(20, 15, 20, 15)
        content_layout.setSpacing(15)

        # ===== ЛЕВАЯ КОЛОНКА =====
        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        content_layout.addLayout(left_col, stretch=1)

        # URL
        self.url_card = Card()
        url_lbl = QLabel("Ссылка")
        url_lbl.setStyleSheet(f"color: {FG_DIM}; font-size: 11px;")
        self.url_card.add(url_lbl)

        url_row = QHBoxLayout()
        url_row.setSpacing(6)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://youtube.com/watch?v=...")
        self.url_input.textChanged.connect(self._on_url_change)
        url_row.addWidget(self.url_input, stretch=1)

        self.btn_paste = QPushButton("📋")
        self.btn_paste.setFixedWidth(42)
        self.btn_paste.setToolTip("Вставить из буфера")
        self.btn_paste.clicked.connect(self._paste_from_clipboard)
        url_row.addWidget(self.btn_paste)

        self.url_card.add_layout(url_row)
        left_col.addWidget(self.url_card)

        # Папка
        self.dir_card = Card()
        dir_row = QHBoxLayout()
        dir_row.setSpacing(6)

        dir_icon = QLabel("📁")
        dir_icon.setStyleSheet("font-size: 14px;")
        dir_row.addWidget(dir_icon)

        self.dir_label = QLabel(settings.get_output_dir(self.settings))
        self.dir_label.setStyleSheet(f"color: {FG_DIM}; font-size: 11px;")
        self.dir_label.setWordWrap(True)
        dir_row.addWidget(self.dir_label, stretch=1)

        self.btn_open_dir = QPushButton("📂")
        self.btn_open_dir.setFixedWidth(38)
        self.btn_open_dir.setToolTip("Открыть папку")
        self.btn_open_dir.clicked.connect(self._open_output_dir)
        dir_row.addWidget(self.btn_open_dir)

        self.btn_choose_dir = QPushButton("Выбрать")
        self.btn_choose_dir.clicked.connect(self._choose_dir)
        dir_row.addWidget(self.btn_choose_dir)

        self.dir_card.add_layout(dir_row)
        left_col.addWidget(self.dir_card)

        # Настройки
        self.opts_card = Card()
        opts_title = QLabel("Настройки")
        opts_title.setStyleSheet(f"color: {FG}; font-size: 12px; font-weight: bold;")
        self.opts_card.add(opts_title)

        self._add_radio_row(self.opts_card, "Контейнер:", "container",
                             [("mp4", "MP4"), ("mkv", "MKV"), ("webm", "WEBM")])
        self._add_radio_row(self.opts_card, "Звук:", "audio_mode",
                             [("best", "Лучший"), ("128", "128"), ("192", "192"),
                              ("256", "256"), ("320", "320"), ("none", "Без звука")])
        self._add_radio_row(self.opts_card, "Кодек:", "audio_codec",
                             [("aac", "AAC"), ("opus", "Opus"), ("mp3", "MP3")])

        self.mark_check = QCheckBox("Помечать настройки в имени файла")
        self.mark_check.setChecked(self.settings.get("mark_settings", True))
        self.opts_card.add(self.mark_check)

        left_col.addWidget(self.opts_card)

        # Режим
        self.mode_card = Card()
        mode_row = QHBoxLayout()
        mode_lbl = QLabel("Режим:")
        mode_lbl.setStyleSheet(f"color: {FG_DIM}; font-size: 11px;")
        mode_lbl.setFixedWidth(80)
        mode_row.addWidget(mode_lbl)

        self.rb_mode_video = QRadioButton("🎬 MP4")
        self.rb_mode_audio = QRadioButton("🎵 MP3")
        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.rb_mode_video, 0)
        self.mode_group.addButton(self.rb_mode_audio, 1)
        if self.settings.get("mode", "video") == "audio":
            self.rb_mode_audio.setChecked(True)
        else:
            self.rb_mode_video.setChecked(True)
        self.mode_group.buttonClicked.connect(self._on_mode_change)

        mode_row.addWidget(self.rb_mode_video)
        mode_row.addWidget(self.rb_mode_audio)
        mode_row.addStretch()
        self.mode_card.add_layout(mode_row)
        left_col.addWidget(self.mode_card)

        left_col.addStretch()

        # ===== ПРАВАЯ КОЛОНКА =====
        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        content_layout.addLayout(right_col, stretch=1)

        # Превью
        self.info_card = Card()
        self.thumb_label = QLabel()
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setMinimumHeight(120)
        self.thumb_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.thumb_label.mouseDoubleClickEvent = lambda e: self._open_in_browser()
        self.info_card.add(self.thumb_label)

        self.title_label = QLabel("")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(f"color: {FG}; font-size: 12px; font-weight: bold;")
        self.info_card.add(self.title_label)

        right_col.addWidget(self.info_card)

        # Качество
        self.fmt_card = Card()
        fmt_title = QLabel("Качество")
        fmt_title.setStyleSheet(f"color: {FG}; font-size: 12px; font-weight: bold;")
        self.fmt_card.add(fmt_title)

        self.quality_group = QualityGroup(on_change=self._on_quality_change, columns=3)
        self.fmt_card.add(self.quality_group)

        right_col.addWidget(self.fmt_card)
        right_col.addStretch()

        # ===== НИЖНЯЯ ПАНЕЛЬ =====
        self.bottom = QWidget()
        self.bottom.setStyleSheet(f"background-color: {BG}; border-top: 1px solid {BORDER};")
        bottom_layout = QVBoxLayout(self.bottom)
        bottom_layout.setContentsMargins(20, 10, 20, 10)
        bottom_layout.setSpacing(6)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_fetch = GlowButton("🔍  Получить форматы", self, is_primary=False)
        self.btn_fetch.setObjectName("glow_btn")
        self.btn_fetch.clicked.connect(self._on_fetch)
        btn_row.addWidget(self.btn_fetch)
        self._glow_buttons.append(self.btn_fetch)

        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setFixedWidth(46)
        self.btn_refresh.clicked.connect(self._on_fetch)
        btn_row.addWidget(self.btn_refresh)

        btn_row.addStretch()

        self.btn_download = GlowButton("⬇  Скачать", self, is_primary=True)
        self.btn_download.setObjectName("glow_btn_primary")
        self.btn_download.setMinimumWidth(180)
        self.btn_download.clicked.connect(self._on_download)
        btn_row.addWidget(self.btn_download)
        self._glow_buttons.append(self.btn_download)

        bottom_layout.addLayout(btn_row)

        prog_row = QHBoxLayout()
        prog_row.setSpacing(8)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        prog_row.addWidget(self.progress, stretch=1)

        self.progress_label = QLabel("0%")
        self.progress_label.setStyleSheet(f"color: {FG_DIM}; font-size: 11px; font-weight: bold;")
        self.progress_label.setFixedWidth(50)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        prog_row.addWidget(self.progress_label)

        bottom_layout.addLayout(prog_row)

        self.status_label = QLabel("Готов к работе")
        self.status_label.setStyleSheet(f"color: {FG_DIM}; font-size: 11px;")
        bottom_layout.addWidget(self.status_label)

        root_layout.addWidget(self.bottom)

        self._setup_shortcuts()

    # --------------------------------------------------------
    #                    ХЕЛПЕРЫ UI
    # --------------------------------------------------------
    def _add_radio_row(self, card, label_text, attr_name, options):
        row = QHBoxLayout()
        row.setSpacing(8)

        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {FG_DIM}; font-size: 11px;")
        lbl.setFixedWidth(80)
        row.addWidget(lbl)

        group = QButtonGroup(self)
        buttons = {}
        current = self.settings.get(attr_name, options[0][0])

        for i, (val, text) in enumerate(options):
            rb = QRadioButton(text)
            group.addButton(rb, i)
            if val == current:
                rb.setChecked(True)
            rb.toggled.connect(lambda checked, v=val, n=attr_name: self._on_radio_change(n, v, checked))
            buttons[val] = rb
            row.addWidget(rb)

        row.addStretch()
        card.add_layout(row)

        setattr(self, f"_rb_{attr_name}", buttons)

    def _on_radio_change(self, name, value, checked):
        if not checked:
            return
        if not self._silent:
            try:
                from modules.sounds import radio
                radio()
            except Exception:
                pass

    def _paint_cheek(self, event):
        painter = QPainter(self.cheek)
        w = self.cheek.width()
        h = self.cheek.height()
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0, QColor(ACCENT))
        grad.setColorAt(1, QColor(BG))
        painter.fillRect(0, 0, w, h, QBrush(grad))
        
    # --------------------------------------------------------
    #                    TITLEBAR
    # --------------------------------------------------------
    def _titlebar_press(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _titlebar_move(self, e):
        if self._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def _toggle_maximize(self):
        if self._is_maximized:
            self.showNormal()
            self._is_maximized = False
        else:
            self.showMaximized()
            self._is_maximized = True

    def _minimize_to_tray(self):
        """Плавное сворачивание — только opacity, без geometry."""
        self._animate_minimize()

    def _animate_minimize(self):
        """Просто fade-out, потом showMinimized()."""
        if self._minimize_anim_running:
            return
        self._minimize_anim_running = True

        # запоминаем состояние (нормальное/максимизированное)
        self._was_maximized = self._is_maximized

        # запоминаем геометрию (только если НЕ максимизированы)
        if not self._is_maximized:
            self._saved_geometry = self.geometry()

        self._minimize_opacity = QPropertyAnimation(self, b"windowOpacity")
        self._minimize_opacity.setDuration(150)
        self._minimize_opacity.setStartValue(1.0)
        self._minimize_opacity.setEndValue(0.0)
        self._minimize_opacity.setEasingCurve(QEasingCurve.Type.InCubic)
        self._minimize_opacity.finished.connect(self._after_minimize_anim)
        self._minimize_opacity.start()
        self._minimize_anim = self._minimize_opacity

    def _after_minimize_anim(self):
        """После fade-out — нативное сворачивание."""
        self.showMinimized()
        self.setWindowOpacity(1.0)
        self._minimize_anim_running = False

    # --------------------------------------------------------
    #                    ТРЕЙ
    # --------------------------------------------------------
    def _create_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        try:
            icon_path = get_active_icon_path()
            if not os.path.exists(icon_path):
                icon_path = ICON_PATH
            self._tray_icon = QSystemTrayIcon(QIcon(icon_path), self)
            self._tray_icon.setToolTip("YouTube Downloader")

            menu = QMenu()
            act_open = QAction("🎬 Открыть", self)
            act_open.triggered.connect(self._show_from_tray)
            menu.addAction(act_open)

            act_hide = QAction("📥 Свернуть", self)
            act_hide.triggered.connect(self.hide)
            menu.addAction(act_hide)

            menu.addSeparator()

            act_quit = QAction("❌ Выход", self)
            act_quit.triggered.connect(self._on_close)
            menu.addAction(act_quit)

            self._tray_icon.setContextMenu(menu)
            self._tray_icon.activated.connect(self._on_tray_click)
            self._tray_icon.show()
        except Exception as e:
            print(f"⚠️ Не удалось создать трей: {e}")

    def _on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_from_tray()

    def _show_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def update_tray_icon(self):
        if not self._tray_icon:
            return
        try:
            icon_path = get_active_icon_path()
            if os.path.exists(icon_path):
                self._tray_icon.setIcon(QIcon(icon_path))
        except Exception:
            pass

    # --------------------------------------------------------
    #                    URL / Папка
    # --------------------------------------------------------
    def _on_url_change(self):
        url = self.url_input.text().strip()
        if not url:
            if not self.downloading:
                self._set_status("Готов к работе")
            return
        if not self.downloading:
            plat = _detect_platform(url)
            self._set_status(f"🔗 {plat}")

    def _paste_from_clipboard(self):
        cb = QApplication.clipboard()
        text = cb.text()
        if text:
            self.url_input.setText(text.strip())

    def _choose_dir(self):
        current = settings.get_output_dir(self.settings)
        chosen = QFileDialog.getExistingDirectory(self, "Выбери папку", current)
        if chosen:
            self.settings["output_dir"] = chosen
            self.dir_label.setText(chosen)
        # достижения: скачивание
        try:
            from modules import achievements as ach_mod
            fmt = self.selected_format or {}
            mode = "audio" if self.rb_mode_audio.isChecked() else "video"
            unlocked = ach_mod.track_download(self.settings, fmt, mode)
            for ach_id in unlocked:
                ach = ach_mod.ACHIEVEMENTS.get(ach_id, {})
                name = ach.get("name", ach_id)
                QTimer.singleShot(500, lambda n=name: QtToast(
                    self, f"🏆 Достижение: {n}", duration=4000
                ))
        except Exception as e:
            print(f"⚠️ Достижения: {e}")
            settings.save(self.settings)
            self._set_status(f"Папка: {chosen}")
            try:
                from modules.sounds import folder_pick
                folder_pick()
            except Exception:
                pass

    def _open_output_dir(self):
        try:
            from modules.toast import open_folder
            open_folder(settings.get_output_dir(self.settings))
        except Exception as e:
            print(f"⚠️ Не удалось открыть папку: {e}")

    # --------------------------------------------------------
    #                    РЕЖИМ
    # --------------------------------------------------------
    def _on_mode_change(self):
        is_audio = self.rb_mode_audio.isChecked()
        for rb in self._rb_container.values():
            rb.setEnabled(not is_audio)
        self._rb_audio_mode["none"].setEnabled(not is_audio)

    # --------------------------------------------------------
    #                    FETCH
    # --------------------------------------------------------
    def _on_fetch(self):
        if self.downloading or self._fetch_in_progress:
            return
        self._fetch_in_progress = True
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "URL пустой", "Вставь ссылку.")
            self._fetch_in_progress = False
            return

        if "playlist" in url.lower() or "list=" in url.lower():
            self._ask_playlist(url)
            return

        self.btn_fetch.setEnabled(False)
        self.btn_refresh.setEnabled(False)
        self.btn_download.setEnabled(False)
        self.quality_group.clear()
        self.title_label.setText("")
        self.thumb_label.clear()
        self._set_status("Получаю форматы...")
        threading.Thread(target=self._fetch_worker, args=(url,), daemon=True).start()

    def _fetch_worker(self, url):
        try:
            title, videos, audios, thumb_url, meta = core.get_formats(url)
            self.title_text = title
            self.meta = meta
            self.current_url = url

            is_audio = self.rb_mode_audio.isChecked()
            if is_audio:
                self.formats = core.unique_sorted_audio(audios)
            else:
                self.formats = core.unique_sorted_video(videos)

            self.sig_populate.emit(title, thumb_url or "")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.sig_error.emit(str(e))

    def _populate_formats(self, title, thumb_url):
        try:
            self.title_label.setText(f"🎬 {title}")

            items = []
            for fmt in self.formats:
                label = self._fmt_label(fmt)
                items.append((label, fmt['id']))

            self.quality_group.set_items(items)

            self.btn_fetch.setEnabled(True)
            self.btn_refresh.setEnabled(True)
            self.btn_download.setEnabled(bool(self.formats))
            self._set_status(f"Найдено: {len(self.formats)}")
            self._fetch_in_progress = False

            if thumb_url and self.settings.get("preview_enabled", True):
                threading.Thread(target=self._load_thumb_worker, args=(thumb_url,), daemon=True).start()
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _load_thumb_worker(self, url):
        try:
            import urllib.request
            import ssl as _ssl
            ctx = _ssl._create_unverified_context()
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (YouTubeDownloader)"
            })
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = resp.read()

            from PyQt6.QtGui import QImage
            img = QImage()
            img.loadFromData(data)
            if img.isNull():
                return
            self.sig_thumb.emit(data)
        except Exception as e:
            print(f"⚠️ Не удалось загрузить превью: {e}")

    def _set_thumb(self, image_bytes):
        try:
            from PyQt6.QtGui import QImage, QPixmap
            img = QImage()
            img.loadFromData(image_bytes)
            if img.isNull():
                return

            pix = QPixmap.fromImage(img).scaled(
                220, 220,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._thumb_pixmap = pix
            self.thumb_label.setPixmap(pix)
            self.thumb_label.setFixedHeight(pix.height())
        except Exception as e:
            print(f"⚠️ Ошибка установки превью: {e}")

    def _fmt_label(self, fmt):
        size_bytes = fmt.get('filesize') or 0
        if not size_bytes:
            size_str = "?"
        elif size_bytes >= 1024 * 1024 * 1024:
            size_str = f"{size_bytes/(1024**3):.1f} GB"
        else:
            size_str = f"{size_bytes/(1024*1024):.0f} MB"

        if self.rb_mode_audio.isChecked():
            abr = fmt.get('abr') or 0
            return f"{abr:.0f} kbps · {size_str}"

        h = fmt.get('height') or 0
        fps = fmt.get('fps') or 0
        if fps and fps > 30:
            return f"{h}p{fps} · {size_str}"
        return f"{h}p · {size_str}"

    def _fetch_error(self, msg):
        self.btn_fetch.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self._set_status("Ошибка получения форматов")
        QMessageBox.critical(self, "Ошибка", msg)
        self._fetch_in_progress = False

    def _on_quality_change(self, value):
        for fmt in self.formats:
            if fmt.get('id') == value:
                self.selected_format = fmt
                self._set_status(f"Выбрано: {self._fmt_label(fmt)}")
                return
        self.selected_format = None

    # --------------------------------------------------------
    #                    DOWNLOAD
    # --------------------------------------------------------
    def _on_download(self):
        if self.downloading:
            return
        fmt = self.selected_format
        if not fmt:
            QMessageBox.warning(self, "Качество не выбрано", "Выбери качество.")
            return
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "URL пустой", "Вставь ссылку.")
            return

        suffix = self._build_suffix()
        output_dir = self._get_output_dir()
        action = self._check_duplicate(self.title_text, output_dir, suffix)
        if action == "skip":
            self._set_status("⏭ Пропущено (файл уже есть)")
            return
        self._rename_flag = (action == "rename")

        self.downloading = True
        self.btn_fetch.setEnabled(False)
        self.btn_refresh.setEnabled(False)
        self._set_download_btn_cancel_mode()
        self._set_status("Скачиваю...")
        self._set_progress(0)

        mode = "audio" if self.rb_mode_audio.isChecked() else "video"
        threading.Thread(target=self._download_worker, args=(url, fmt, mode), daemon=True).start()

    def _set_download_btn_cancel_mode(self):
        self.btn_download.setText("⏹  Отмена")
        self.btn_download.setObjectName("glow_btn_primary")
        try:
            self.btn_download.clicked.disconnect()
        except Exception:
            pass
        self.btn_download.clicked.connect(self._on_cancel)
        self.btn_download.setEnabled(True)

    def _set_download_btn_normal_mode(self):
        self.btn_download.setText("⬇  Скачать")
        try:
            self.btn_download.clicked.disconnect()
        except Exception:
            pass
        self.btn_download.clicked.connect(self._on_download)
        self.btn_download.setEnabled(bool(self.formats))

    def _on_cancel(self):
        if not self.downloading:
            return
        try:
            from modules import core
            core.cancel_download()
            self._set_status("⏹ Отмена...")
        except Exception as e:
            print(f"⚠️ Ошибка отмены: {e}")

    def _download_worker(self, url, fmt, mode):
        try:
            core.PROGRESS_CALLBACK = self._on_progress
            output_dir = self._get_output_dir()
            suffix = self._build_suffix()

            if mode == "audio":
                codec = self._get_checked("_rb_audio_codec", "aac")
                if codec not in ("mp3", "m4a"):
                    codec = "mp3"
                bitrate = None
                am = self._get_checked("_rb_audio_mode", "best")
                if am.isdigit():
                    bitrate = int(am)

                final_path = core.download_audio(
                    url, fmt['id'], output_dir,
                    codec=codec, bitrate=bitrate,
                    name_suffix=suffix,
                    rename_if_exists=self._rename_flag,
                )
                self._last_downloaded_file = final_path

                mp3_path = final_path or embed.find_latest_mp3(output_dir)
                if mp3_path and os.path.exists(mp3_path):
                    thumb = embed.find_thumbnail(mp3_path)
                    cover = thumb if thumb else (COVER_PATH if os.path.exists(COVER_PATH) else None)
                    if cover:
                        embed.embed_cover(mp3_path, cover)
                    if self.settings.get("embed_metadata", True) and self.meta:
                        embed.embed_metadata(mp3_path, self.meta)
                try:
                    embed.cleanup_temp_files(output_dir)
                except Exception:
                    pass
            else:
                container = self._get_checked("_rb_container", "mp4")
                am = self._get_checked("_rb_audio_mode", "best")
                audio_mode = 'best'
                audio_bitrate = None
                audio_codec = None
                if am == 'none':
                    audio_mode = 'none'
                elif am.isdigit():
                    audio_mode = 'bitrate'
                    audio_bitrate = int(am)

                final_path = core.download_video(
                    url, fmt['id'], output_dir,
                    container=container,
                    audio_mode=audio_mode,
                    audio_bitrate=audio_bitrate,
                    audio_codec=audio_codec,
                    name_suffix=suffix,
                    rename_if_exists=self._rename_flag,
                )
                self._last_downloaded_file = final_path

            core.PROGRESS_CALLBACK = None
            QTimer.singleShot(0, self._download_done)
        except yt_dlp.utils.DownloadCancelled:
            core.PROGRESS_CALLBACK = None
            QTimer.singleShot(0, self._download_cancelled)
        except Exception as e:
            core.PROGRESS_CALLBACK = None
            QTimer.singleShot(0, lambda: self._download_error(str(e)))

    def _download_cancelled(self):
        self.downloading = False
        self.btn_fetch.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self._set_download_btn_normal_mode()
        self._set_status("⏹ Отменено")

    def _download_done(self):
        self.downloading = False
        self.btn_fetch.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self._set_download_btn_normal_mode()

        output_dir = self._get_output_dir()

        saved_url = self.url_input.text().strip()
        settings.add_recent_url(self.settings, saved_url)
        self.url_input.setText("")

        self._set_status(f"✅ Готово! Файл в: {output_dir}")

        latest_file = self._last_downloaded_file
        if latest_file and os.path.exists(latest_file):
            settings.add_to_history(self.settings, latest_file,
                                    url=saved_url, title=self.title_text)
        self._last_downloaded_file = None
        self.selected_format = None

        if self.settings.get("clear_thumb_cache", True):
            try:
                from modules import cache
                cache.clear_thumbnail_cache(latest_file)
                cache.clear_vlc_cache()
            except Exception:
                pass

        settings.save(self.settings)

        try:
            if latest_file:
                QtToast(self, f"✅ Файл сохранён:\n{os.path.basename(latest_file)}")
            else:
                QtToast(self, f"✅ Файл сохранён:\n{output_dir}")
        except Exception as e:
            print(f"⚠️ Ошибка тоста: {e}")
        # достижения: скачивание
        try:
            from modules import achievements as ach_mod
            fmt = self.selected_format or {}
            mode = "audio" if self.rb_mode_audio.isChecked() else "video"
            unlocked = ach_mod.track_download(self.settings, fmt, mode)
            for ach_id in unlocked:
                ach = ach_mod.ACHIEVEMENTS.get(ach_id, {})
                name = ach.get("name", ach_id)
                QTimer.singleShot(500, lambda n=name: QtToast(
                    self, f"🏆 Достижение: {n}", duration=4000
                ))
        except Exception as e:
            print(f"⚠️ Достижения: {e}")

    def _download_error(self, msg):
        self.downloading = False
        self.btn_fetch.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self._set_download_btn_normal_mode()
        self._set_status("Ошибка скачивания")
        QMessageBox.critical(self, "Ошибка", msg)
        
    # --------------------------------------------------------
    #                    ВСПОМОГАТЕЛЬНЫЕ
    # --------------------------------------------------------
    def _get_checked(self, attr, default):
        buttons = getattr(self, attr, {})
        for val, rb in buttons.items():
            if rb.isChecked():
                return val
        return default

    def _get_output_dir(self):
        base = settings.get_output_dir(self.settings)
        if not self.settings.get("auto_sort", False):
            return base
        if self.rb_mode_audio.isChecked():
            sub = self.settings.get("sort_audio_dir", "Музыка")
        elif not self.mark_check.isChecked():
            sub = self.settings.get("sort_archive_dir", "Архив")
        else:
            sub = self.settings.get("sort_video_dir", "Видео")
        full = os.path.join(base, sub)
        try:
            os.makedirs(full, exist_ok=True)
        except Exception:
            return base
        return full

    def _build_suffix(self):
        if not self.mark_check.isChecked():
            return ""
        if self.rb_mode_audio.isChecked():
            codec = self._get_checked("_rb_audio_codec", "mp3")
            if codec not in ("mp3", "m4a"):
                codec = "mp3"
            am = self._get_checked("_rb_audio_mode", "best")
            br = f"-{am}" if am.isdigit() else ""
            return f"{codec}{br}"
        cont = self._get_checked("_rb_container", "mp4")
        am = self._get_checked("_rb_audio_mode", "best")
        parts = [cont]
        if am == "none":
            parts.append("nosound")
        elif am.isdigit():
            parts.append(f"a{am}")
        return "-".join(parts)

    def _check_duplicate(self, title, output_dir, suffix=""):
        safe = re.sub(r'[<>:"/\\|?*]', '_', title).strip()
        base = f"{safe} [{suffix}]" if suffix else safe
        found = []
        if os.path.isdir(output_dir):
            for f in os.listdir(output_dir):
                name_no_ext, ext = os.path.splitext(f)
                if ext.lower() in ('.mp3', '.mp4', '.mkv', '.webm', '.m4a'):
                    if name_no_ext == base or name_no_ext.startswith(base + "_"):
                        found.append(f)
        if not found:
            return None

        msg = QMessageBox(self)
        msg.setWindowTitle("Дубликат")
        msg.setText(f"⚠️ Файл уже существует\nНайдено: {len(found)}")
        msg.setInformativeText(found[0][:60])
        b_skip = msg.addButton("⏭ Пропустить", QMessageBox.ButtonRole.RejectRole)
        b_rename = msg.addButton("📝 Переименовать", QMessageBox.ButtonRole.ActionRole)
        b_over = msg.addButton("♻️ Перезаписать", QMessageBox.ButtonRole.AcceptRole)
        msg.exec()

        if msg.clickedButton() == b_skip:
            return "skip"
        if msg.clickedButton() == b_rename:
            return "rename"
        return "overwrite"

    def _set_status(self, text):
        # если тема Frostmourne — переводим на язык Артаса
        if self._holiday_theme == "frostmourne" or self._real_theme == "frostmourne":
            text = self._translate_to_arthas(text)
        self.status_label.setText(text)

    def _translate_to_arthas(self, text):
        """Переводит статус на язык Артаса."""
        replacements = {
            "Готов к работе": "❄️ Клинок ждёт...",
            "Получаю форматы...": "❄️ Читаю судьбу жертвы...",
            "Найдено:": "❄️ Душ найдено:",
            "Скачиваю...": "❄️ Фростморн пьёт душу...",
            "✅ Готово!": "💀 Душа поглощена!",
            "⏹ Отменено": "❄️ Жертва сбежала...",
            "Ошибка": "💀 Тьма отвернулась...",
            "Ошибка получения форматов": "💀 Не удалось прочесть судьбу",
            "Ошибка скачивания": "💀 Душа сопротивляется",
            "Папка:": "❄️ Логово:",
            "⏭ Пропущено": "❄️ Душа уже наша",
        }
        for old, new in replacements.items():
            if old in text:
                text = text.replace(old, new)
        return text

    def _set_progress(self, percent):
        self.progress.setValue(int(percent))
        self.progress_label.setText(f"{percent:.0f}%")

    def _on_progress(self, d):
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                percent = downloaded / total * 100
                self.sig_progress.emit(percent)
            speed = d.get('speed') or 0
            eta = d.get('eta')
            self.sig_info.emit(speed, eta)
        elif d.get('status') == 'finished':
            self.sig_progress.emit(100.0)

    def _update_info(self, speed_bps, eta_sec):
        def _speed(bps):
            if not bps:
                return "—"
            if bps >= 1024 * 1024:
                return f"{bps/(1024*1024):.1f} MB/s"
            if bps >= 1024:
                return f"{bps/1024:.0f} KB/s"
            return f"{bps:.0f} B/s"

        def _eta(sec):
            if sec is None or sec < 0:
                return "—"
            sec = int(sec)
            h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
            if h > 0:
                return f"{h}:{m:02d}:{s:02d}"
            return f"{m:02d}:{s:02d}"

        self._set_status(f"⬇ {self.progress.value()}% · {_speed(speed_bps)} · осталось {_eta(eta_sec)}")

    # --------------------------------------------------------
    #                    ПЛЕЙЛИСТ
    # --------------------------------------------------------
    def _ask_playlist(self, url):
        msg = QMessageBox(self)
        msg.setWindowTitle("Плейлист обнаружен")
        msg.setText("📚 Плейлист обнаружен")
        msg.setInformativeText("Скачать весь плейлист в подпапку?")
        b_all = msg.addButton("📚 Весь плейлист", QMessageBox.ButtonRole.AcceptRole)
        b_one = msg.addButton("🎬 Одно видео", QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        if msg.clickedButton() == b_all:
            self._download_playlist(url)
        else:
            self._on_fetch_single(url)

    def _on_fetch_single(self, url):
        self.btn_fetch.setEnabled(False)
        self._set_status("Получаю форматы...")
        threading.Thread(target=self._fetch_worker, args=(url,), daemon=True).start()

    def _download_playlist(self, url):
        if self.downloading:
            return
        self.downloading = True
        self.btn_fetch.setEnabled(False)
        self.btn_refresh.setEnabled(False)
        self.btn_download.setEnabled(False)
        self._set_status("📚 Получаю плейлист...")
        threading.Thread(target=self._playlist_worker, args=(url,), daemon=True).start()

    def _playlist_worker(self, url):
        try:
            output_dir = self._get_output_dir()
            mode = "audio" if self.rb_mode_audio.isChecked() else "video"
            suffix = self._build_suffix()
            core.PROGRESS_CALLBACK = self._on_progress
            if mode == "audio":
                codec = self._get_checked("_rb_audio_codec", "mp3")
                if codec not in ("mp3", "m4a"):
                    codec = "mp3"
                playlist_dir, title = core.download_playlist(
                    url, output_dir, mode='audio', codec=codec, name_suffix=suffix
                )
            else:
                container = self._get_checked("_rb_container", "mp4")
                playlist_dir, title = core.download_playlist(
                    url, output_dir, mode='video', container=container, name_suffix=suffix
                )
            core.PROGRESS_CALLBACK = None
            QTimer.singleShot(0, lambda d=playlist_dir, t=title: self._playlist_done(d, t))
        except Exception as e:
            core.PROGRESS_CALLBACK = None
            QTimer.singleShot(0, lambda: self._download_error(str(e)))

    def _playlist_done(self, playlist_dir, title):
        self.downloading = False
        self.btn_fetch.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self.btn_download.setEnabled(True)
        self._set_status(f"✅ Плейлист сохранён: {title}")

    # --------------------------------------------------------
    #                    ДИАЛОГИ
    # --------------------------------------------------------
    def _open_settings(self):
        SettingsDialog(self).exec()
        
    def _reset_launcher(self):
        """Сбрасывает preferred_gui и перезапускает лаунчер."""
        try:
            from config import set_preferred_gui
            set_preferred_gui(None)
        except Exception as e:
            print(f"⚠️ Не удалось сбросить preferred_gui: {e}")

        # Запускаем лаунчер
        import subprocess
        launcher_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "downloader_launcher.py"
        )
        try:
            subprocess.Popen([sys.executable, launcher_path])
        except Exception as e:
            print(f"⚠️ Не удалось запустить лаунчер: {e}")
            return

        # Закрываем текущее приложение
        QApplication.quit()

    def _open_profiles(self):
        ProfilesDialog(self).exec()

    def _open_history(self):
        HistoryDialog(self).exec()

    def _open_changelog(self):
        ChangelogDialog(self).exec()

    def _open_icon_manager(self):
        IconManagerDialog(self).exec()

    def _open_player(self):
        QMessageBox.information(self, "Плеер", "🎵 Плеер появится в следующем обновлении.")

    def _open_in_browser(self):
        if self.current_url:
            webbrowser.open(self.current_url)

    def _change_theme(self):
        ThemeDialog(self).exec()
        
    def _play_frostmourne_greeting(self):
        """Играет 'К чёрту людей!' при входе в тему Frostmourne."""
        try:
            from modules.sounds import play_admin_mp3
            play_admin_mp3("KChortuLudei!.mp3")
        except Exception as e:
            print(f"⚠️ Голос Фростморна: {e}")
            
    def _play_voice(self, filename):
        """Играет звук из admin_assets/sounds/."""
        try:
            from modules.sounds import play_admin_mp3
            if play_admin_mp3(filename):
                print(f"🔊 {filename}")
            else:
                QMessageBox.warning(
                    self, "Нет файла",
                    f"Файл не найден:\nadmin_assets/sounds/{filename}"
                )
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", str(e))

    def _take_frostmourne(self):
        """Пасхалка: Артас берёт Фростморн."""
        # играем "Я с радостью приму проклятие"
        try:
            from modules.sounds import play_admin_mp3
            play_admin_mp3("YaSRadost'uPrimu.mp3")
        except Exception as e:
            print(f"⚠️ Голос: {e}")

        # диалог через 4 сек
        QTimer.singleShot(4000, lambda: QMessageBox.information(
            self, "❄️ Фростморн",
            "«Я с радостью приму на себя проклятие»\n\n"
            "Ты взял Фростморн. Ты — Король-лич.\n"
            "Тема: Frostmourne. Черепа падают.\n\n"
            "Перезапусти приложение."
        ))

        # ставим тему и праздник
        self.parent_app.settings["theme"] = "frostmourne"
        self.parent_app.settings["admin_forced_holiday"] = "frostmourne"

        # достижения: тема Frostmourne
        try:
            from modules import achievements as ach_mod
            unlocked = ach_mod.track_theme(self.parent_app.settings, "frostmourne")
            for ach_id in unlocked:
                ach = ach_mod.ACHIEVEMENTS.get(ach_id, {})
                ach_name = ach.get("name", ach_id)
                QTimer.singleShot(5000, lambda n=ach_name: QtToast(
                    self.parent_app, f"🏆 Достижение: {n}", duration=4000
                ))
        except Exception as e:
            print(f"⚠️ Достижения (Frostmourne): {e}")

        settings.save(self.parent_app.settings)
        self.accept()

        # перезапуск через 4.5 сек
        QTimer.singleShot(4500, self.parent_app._restart_with_animation)
        
    def _apply_holiday_background(self):
        """Гирлянда поверх всего + падающие под scroll, но над фоном."""
        if not self._holiday_theme:
            return

        # 1. гирлянда — поверх всего
        if HAS_HOLIDAY_FX:
            try:
                self._holiday_lights = HolidayLights(
                    self.centralWidget(),
                    self._holiday_theme,
                    count=25,
                )
                # под шапкой
                self._holiday_lights.setGeometry(
                    0, 39,
                    self.centralWidget().width(), 30
                )
                self._holiday_lights.show()
                self._holiday_lights.raise_()
                print(f"🎄 Гирлянда поверх всего")
            except Exception as e:
                print(f"⚠️ Гирлянда: {e}")

        # 2. падающие — на viewport scroll, под content
        try:
            from modules.falling_fx_qt import FallingFXQt
            viewport = self._scroll.viewport()
            self._falling_fx = FallingFXQt(
                viewport,
                self._holiday_theme,
                count=12,
                speed=1.5,
            )
            self._falling_fx.setGeometry(viewport.rect())
            self._falling_fx.show()

            # ВРЕМЕННО без stackUnder — проверим, видны ли
            # self._falling_fx.stackUnder(self.content)
            print(f"🎄 Падающие на viewport, БЕЗ stackUnder")
        except Exception as e:
            print(f"⚠️ Падающие: {e}")
            
            
    def _restart_falling_fx(self):
        """Пересоздаёт падающие эмодзи."""
        try:
            if getattr(self, "_falling_fx", None):
                self._falling_fx.stop()
                self._falling_fx.deleteLater()
                self._falling_fx = None

            from modules.falling_fx_qt import FallingFXQt
            parent = self.centralWidget()
            self._falling_fx = FallingFXQt(
                parent,
                self._holiday_theme,
                count=12,
                speed=1.5,
            )
            self._falling_fx.setGeometry(parent.rect())
            self._falling_fx.show()
            self._falling_fx.raise_()
            print(f"🎄 Падающие пересозданы")
        except Exception as e:
            print(f"⚠️ Ошибка пересоздания: {e}")

    def _disable_native_acrylic(self):
        """Выключает Acrylic."""
        import sys
        if sys.platform != "win32":
            return
        try:
            hwnd = int(self.winId())
            disable_acrylic_win10(hwnd)
        except Exception:
            pass
        
    def _restart_with_animation(self):
        """Плавно перезапускает приложение с новой темой."""
        # --- оверлей ---
        overlay = QWidget(self)
        overlay.setGeometry(self.rect())
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 200);")

        lay = QVBoxLayout(overlay)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("🎨")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 64px; background: transparent;")
        lay.addWidget(icon)

        txt = QLabel("Применяю тему...")
        txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        txt.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold; background: transparent;")
        lay.addWidget(txt)

        overlay.show()
        overlay.raise_()
        overlay.setWindowOpacity(0.0)

        # fade-in оверлея
        fade_in = QPropertyAnimation(overlay, b"windowOpacity")
        fade_in.setDuration(250)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        fade_in.start()

        # fade-out главного окна → перезапуск
        fade_out = QPropertyAnimation(self, b"windowOpacity")
        fade_out.setDuration(250)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        fade_out.finished.connect(self._do_restart)
        fade_out.start()

        self._restart_overlay = overlay
        self._restart_fade_in = fade_in
        self._restart_fade_out = fade_out

    def _do_restart(self):
        """Перезапускает приложение. Работает и в скрипте, и в exe."""
        # сохраняем состояние настроек
        self.settings["mode"] = "audio" if self.rb_mode_audio.isChecked() else "video"
        self.settings["container"] = self._get_checked("_rb_container", "mp4")
        self.settings["audio_mode"] = self._get_checked("_rb_audio_mode", "best")
        self.settings["audio_codec"] = self._get_checked("_rb_audio_codec", "aac")
        self.settings["mark_settings"] = self.mark_check.isChecked()
        settings.save(self.settings)

        # останавливаем фоновые штуки
        if getattr(self, "_falling_fx", None):
            try:
                self._falling_fx.stop()
            except Exception:
                pass
        if getattr(self, "_holiday_lights", None):
            try:
                self._holiday_lights.stop()
            except Exception:
                pass
        if getattr(self, "_frost_fx", None):
            try:
                self._frost_fx.stop()
            except Exception:
                pass
        if getattr(self, "_glow_timer", None):
            self._glow_timer.stop()
        if self._tray_icon:
            try:
                self._tray_icon.hide()
            except Exception:
                pass

        # --- перезапуск ---
        import subprocess
        import threading
        import time

        if getattr(sys, "frozen", False):
            # exe — запускаем отсоединённо, с задержкой
            exe_path = sys.executable

            def _delayed_launch():
                time.sleep(2.0)  # ждём, пока родитель закроется
                subprocess.Popen([exe_path],
                                 creationflags=subprocess.DETACHED_PROCESS
                                 | subprocess.CREATE_NEW_PROCESS_GROUP)

            threading.Thread(target=_delayed_launch, daemon=True).start()
        else:
            # скрипт
            script = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "downloader_qt.py"
            )
            subprocess.Popen([sys.executable, script])

        QApplication.quit()
            
    def _show_holiday_toast(self):
        try:
            QtToast(self, self._holiday_greeting, duration=7000)
        except Exception as e:
            print(f"⚠️ Ошибка праздничного тоста: {e}")

    def _check_ytdlp_update(self):
        try:
            from modules import updater
            updated = updater.check_and_update(silent=True)
            if updated:
                QTimer.singleShot(0, lambda: QMessageBox.information(
                    self, "yt-dlp обновлён",
                    "📦 yt-dlp обновлён!\nПерезапусти приложение."
                ))
        except Exception as e:
            print(f"⚠️ Ошибка проверки обновлений: {e}")

    def _setup_shortcuts(self):
        from PyQt6.QtGui import QShortcut, QKeySequence
        QShortcut(QKeySequence("Ctrl+V"), self, self._paste_from_clipboard)
        QShortcut(QKeySequence("Return"), self, self._on_fetch)
        QShortcut(QKeySequence("F5"), self, self._on_fetch)
        QShortcut(QKeySequence("Escape"), self, self._on_close)
        QShortcut(QKeySequence("Ctrl+H"), self, self._open_history)
        QShortcut(QKeySequence("Ctrl+T"), self, self._change_theme)

    def _on_close(self):
        try:
            geom = f"{self.width()}x{self.height()}"
            self.settings["window_geometry"] = geom
        except Exception:
            pass

        self.settings["mode"] = "audio" if self.rb_mode_audio.isChecked() else "video"
        self.settings["container"] = self._get_checked("_rb_container", "mp4")
        self.settings["audio_mode"] = self._get_checked("_rb_audio_mode", "best")
        self.settings["audio_codec"] = self._get_checked("_rb_audio_codec", "aac")
        self.settings["mark_settings"] = self.mark_check.isChecked()
        # НЕ сохраняем настройки при закрытии (они уже сохранены при действиях)
        print("DEBUG: _on_close — сохранение отключено")

        if getattr(self, "_glow_timer", None):
            self._glow_timer.stop()

        if self._tray_icon:
            try:
                self._tray_icon.hide()
            except Exception:
                pass

        QApplication.quit()


# ============================================================
#                    ДИАЛОГИ
# ============================================================
class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setFixedSize(480, 560)
        self.parent_app = parent
        self.vars = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel("⚙️ Настройки")
        title.setStyleSheet(f"color: {FG}; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setSpacing(12)
        scroll.setWidget(inner)
        layout.addWidget(scroll, stretch=1)

        def add_check(key, label, hint=""):
            cb = QCheckBox(label)
            cb.setChecked(parent.settings.get(key, True))
            self.vars[key] = cb
            inner_layout.addWidget(cb)
            if hint:
                h = QLabel(hint)
                h.setStyleSheet(f"color: {FG_DIM}; font-size: 10px; font-style: italic;")
                h.setContentsMargins(22, 0, 0, 0)
                inner_layout.addWidget(h)

        add_check("sounds_enabled", "🔊 Звуки", "Клики, переключения, уведомления")
        add_check("toasts_enabled", "💬 Всплывающие уведомления")
        add_check("preview_enabled", "🖼 Показывать превью")
        add_check("animations_enabled", "✨ Анимации")
        add_check("clear_thumb_cache", "🧹 Чистить кэш обложек")
        add_check("embed_metadata", "📝 Метаданные в MP3")
        add_check("auto_update_ytdlp", "📦 Автообновление yt-dlp")
        add_check("auto_sort", "📂 Автосортировка по папкам")
        add_check("check_updates", "🔄 Проверять обновления")

        inner_layout.addStretch()
        
        # --- Liquid Glass ---
        separator = QLabel("")
        separator.setFixedHeight(10)
        inner_layout.addWidget(separator)

        liquid_title = QLabel("🧊 Liquid Glass")
        liquid_title.setStyleSheet(f"color: {FG}; font-size: 13px; font-weight: bold;")
        inner_layout.addWidget(liquid_title)

        liquid_cb = QCheckBox("Включить эффект стекла")
        liquid_cb.setChecked(parent.settings.get("liquid_glass", False))
        self.vars["liquid_glass"] = liquid_cb
        inner_layout.addWidget(liquid_cb)

        hint = QLabel("Делает любую тему полупрозрачной, как в iOS 26")
        hint.setStyleSheet(f"color: {FG_DIM}; font-size: 10px; font-style: italic;")
        hint.setContentsMargins(22, 0, 0, 0)
        inner_layout.addWidget(hint)

        # слайдер прозрачности
        op_row = QHBoxLayout()
        op_lbl = QLabel("Прозрачность:")
        op_lbl.setStyleSheet(f"color: {FG_DIM}; font-size: 11px;")
        op_lbl.setFixedWidth(100)
        op_row.addWidget(op_lbl)
        op_slider = QSlider(Qt.Orientation.Horizontal)
        op_slider.setRange(30, 90)
        op_slider.setValue(parent.settings.get("liquid_opacity", 70))
        self.vars["liquid_opacity"] = op_slider
        op_row.addWidget(op_slider, stretch=1)
        op_val = QLabel(f"{op_slider.value()}%")
        op_val.setStyleSheet(f"color: {FG}; font-size: 11px;")
        op_val.setFixedWidth(40)
        op_slider.valueChanged.connect(lambda v: op_val.setText(f"{v}%"))
        op_row.addWidget(op_val)
        inner_layout.addLayout(op_row)

        # слайдер размытия
        bl_row = QHBoxLayout()
        bl_lbl = QLabel("Размытие:")
        bl_lbl.setStyleSheet(f"color: {FG_DIM}; font-size: 11px;")
        bl_lbl.setFixedWidth(100)
        bl_row.addWidget(bl_lbl)
        bl_slider = QSlider(Qt.Orientation.Horizontal)
        bl_slider.setRange(5, 40)
        bl_slider.setValue(parent.settings.get("liquid_blur", 20))
        self.vars["liquid_blur"] = bl_slider
        bl_row.addWidget(bl_slider, stretch=1)
        bl_val = QLabel(f"{bl_slider.value()}px")
        bl_val.setStyleSheet(f"color: {FG}; font-size: 11px;")
        bl_val.setFixedWidth(40)
        bl_slider.valueChanged.connect(lambda v: bl_val.setText(f"{v}px"))
        bl_row.addWidget(bl_val)
        inner_layout.addLayout(bl_row)

        # Кнопки
        btn_row = QHBoxLayout()

        btn_switch = QPushButton("🔄 Сменить версию")
        btn_switch.clicked.connect(self._switch_version)
        btn_row.addWidget(btn_switch)

        btn_reset = QPushButton("Сбросить")
        btn_reset.clicked.connect(self._reset)
        btn_row.addWidget(btn_reset)

        btn_row.addStretch()

        btn_save = QPushButton("Сохранить")
        btn_save.setObjectName("primary")
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)

        layout.addLayout(btn_row)

    def _reset(self):
        """Сбросить настройки на дефолтные."""
        try:
            from modules.settings import DEFAULTS
        except ImportError:
            DEFAULTS = {}
        for key, cb in self.vars.items():
            cb.setChecked(DEFAULTS.get(key, True))

    def _save(self):
        for key, widget in self.vars.items():
            if isinstance(widget, QCheckBox):
                self.parent_app.settings[key] = widget.isChecked()
            elif isinstance(widget, QSlider):
                self.parent_app.settings[key] = widget.value()

        settings.save(self.parent_app.settings)

        # если Liquid Glass поменялся — предложить перезапуск
        old = self.parent_app.settings.get("liquid_glass", False)
        self.accept()

        # перезапуск с анимацией — чтобы стекло применилось
        QTimer.singleShot(50, self.parent_app._restart_with_animation)
        
    def _switch_version(self):
        """Спрашивает подтверждение и перезапускает лаунчер."""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Сменить версию",
            "Приложение закроется и откроется лаунчер выбора версии.\n"
            "Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.accept()
            self.parent_app._reset_launcher()


class ProfilesDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Профили")
        self.setFixedSize(500, 500)
        self.parent_app = parent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title = QLabel("🎯 Профили")
        title.setStyleSheet(f"color: {FG}; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self.list = QListWidget()
        layout.addWidget(self.list, stretch=1)
        self._refresh()

        btn_row = QHBoxLayout()
        b1 = QPushButton("✓ Применить")
        b1.setObjectName("primary")
        b1.clicked.connect(self._apply)
        btn_row.addWidget(b1)

        b2 = QPushButton("💾 Сохранить текущий")
        b2.clicked.connect(self._save_current)
        btn_row.addWidget(b2)

        btn_row.addStretch()

        b3 = QPushButton("🗑 Удалить")
        b3.clicked.connect(self._delete)
        btn_row.addWidget(b3)

        layout.addLayout(btn_row)

        presets = QLabel("Быстрые пресеты:")
        presets.setStyleSheet(f"color: {FG_DIM}; font-size: 11px;")
        layout.addWidget(presets)

        presets_row = QHBoxLayout()
        PRESETS = {
            "🎵 Музыка 320": {"mode": "audio", "audio_codec": "mp3", "audio_mode": "320"},
            "🎬 Видео 1080": {"mode": "video", "container": "mp4", "audio_codec": "aac", "audio_mode": "320"},
            "📦 Архив": {"mode": "video", "container": "mp4", "audio_codec": "aac", "audio_mode": "best"},
        }
        for name, data in PRESETS.items():
            b = QPushButton(name)
            b.clicked.connect(lambda _, d=data: self._apply_data(d))
            presets_row.addWidget(b)
        presets_row.addStretch()
        layout.addLayout(presets_row)

    def _refresh(self):
        self.list.clear()
        profiles = self.parent_app.settings.get("profiles", {})
        for name in profiles:
            self.list.addItem(f"  {name}")

    def _apply(self):
        item = self.list.currentItem()
        if not item:
            return
        name = item.text().strip()
        profiles = self.parent_app.settings.get("profiles", {})
        if name in profiles:
            self._apply_data(profiles[name])

    def _apply_data(self, data):
        p = self.parent_app
        p._silent = True
        if data.get("mode") == "audio":
            p.rb_mode_audio.setChecked(True)
        else:
            p.rb_mode_video.setChecked(True)
        if "container" in data:
            btn = p._rb_container.get(data["container"])
            if btn:
                btn.setChecked(True)
        if "audio_mode" in data:
            btn = p._rb_audio_mode.get(data["audio_mode"])
            if btn:
                btn.setChecked(True)
        if "audio_codec" in data:
            btn = p._rb_audio_codec.get(data["audio_codec"])
            if btn:
                btn.setChecked(True)
        p._silent = False
        p._on_mode_change()
        self.accept()

    def _save_current(self):
        name, ok = QInputDialog.getText(self, "Имя профиля", "Название:")
        if not ok or not name:
            return
        p = self.parent_app
        data = {
            "mode": "audio" if p.rb_mode_audio.isChecked() else "video",
            "container": p._get_checked("_rb_container", "mp4"),
            "audio_mode": p._get_checked("_rb_audio_mode", "best"),
            "audio_codec": p._get_checked("_rb_audio_codec", "aac"),
        }
        profiles = p.settings.get("profiles", {})
        profiles[name] = data
        p.settings["profiles"] = profiles
        settings.save(p.settings)
        self._refresh()

    def _delete(self):
        item = self.list.currentItem()
        if not item:
            return
        name = item.text().strip()
        p = self.parent_app
        profiles = p.settings.get("profiles", {})
        if name in profiles:
            del profiles[name]
            p.settings["profiles"] = profiles
            settings.save(p.settings)
            self._refresh()


class HistoryDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("История")
        self.setFixedSize(700, 500)
        self.parent_app = parent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("📜 История скачанного")
        title.setStyleSheet(f"color: {FG}; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self.list = QListWidget()
        history = parent.settings.get("history", [])
        for i, entry in enumerate(history, 1):
            date = entry.get("date", "?")
            title_ = entry.get("title", "?")
            self.list.addItem(f"{i:2}. [{date}] {title_}")

        layout.addWidget(self.list, stretch=1)

        btn_row = QHBoxLayout()
        b_open = QPushButton("▶ Открыть файл")
        b_open.clicked.connect(self._open_file)
        btn_row.addWidget(b_open)

        b_folder = QPushButton("📂 Папка")
        b_folder.clicked.connect(self._open_folder)
        btn_row.addWidget(b_folder)

        btn_row.addStretch()

        b_clear = QPushButton("🗑 Очистить")
        b_clear.clicked.connect(self._clear)
        btn_row.addWidget(b_clear)

        layout.addLayout(btn_row)

    def _open_file(self):
        item = self.list.currentRow()
        history = self.parent_app.settings.get("history", [])
        if 0 <= item < len(history):
            f = history[item].get("file", "")
            if f and os.path.exists(f):
                try:
                    from modules.toast import open_file
                    open_file(f)
                except Exception:
                    pass

    def _open_folder(self):
        item = self.list.currentRow()
        history = self.parent_app.settings.get("history", [])
        if 0 <= item < len(history):
            f = history[item].get("file", "")
            if f:
                try:
                    from modules.toast import open_folder
                    open_folder(os.path.dirname(f))
                except Exception:
                    pass

    def _clear(self):
        self.parent_app.settings["history"] = []
        settings.save(self.parent_app.settings)
        self.list.clear()


class ChangelogDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Что нового")
        self.setFixedSize(640, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("📋 Что нового")
        title.setStyleSheet(f"color: {FG}; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        txt = QTextEdit()
        txt.setReadOnly(True)
        content = "Changelog не найден."
        if os.path.exists(CHANGELOG_PATH):
            try:
                with open(CHANGELOG_PATH, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                content = f"Ошибка: {e}"
        txt.setPlainText(content)
        layout.addWidget(txt, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        b = QPushButton("Закрыть")
        b.clicked.connect(self.accept)
        btn_row.addWidget(b)
        layout.addLayout(btn_row)


class IconManagerDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Менеджер иконок")
        self.setFixedSize(700, 500)
        self.parent_app = parent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("🎨 Менеджер иконок")
        title.setStyleSheet(f"color: {FG}; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        body = QHBoxLayout()
        body.setSpacing(15)

        left = QVBoxLayout()
        self.list = QListWidget()
        left.addWidget(self.list)
        body.addLayout(left, stretch=1)

        right = QVBoxLayout()
        self.preview = QLabel()
        self.preview.setFixedSize(180, 180)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet(f"background-color: {BG_CARD}; border-radius: 12px;")
        right.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignHCenter)

        b_apply = QPushButton("✓ Применить")
        b_apply.setObjectName("primary")
        b_apply.clicked.connect(self._apply)
        right.addWidget(b_apply)

        b_create = QPushButton("➕ Создать")
        b_create.clicked.connect(self._create)
        right.addWidget(b_create)

        b_delete = QPushButton("🗑 Удалить")
        b_delete.clicked.connect(self._delete)
        right.addWidget(b_delete)

        right.addStretch()
        body.addLayout(right)

        layout.addLayout(body, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        b_close = QPushButton("Закрыть")
        b_close.clicked.connect(self.accept)
        btn_row.addWidget(b_close)
        layout.addLayout(btn_row)

        self.list.currentRowChanged.connect(self._show_preview)
        self._refresh()

    def _refresh(self):
        self.list.clear()
        self._icons = icon_manager.list_icons()
        active = icon_manager.get_active_icon_name()
        for name, path in self._icons:
            display = name + ("  ✓" if name == active else "")
            self.list.addItem(display)

    def _show_preview(self, row):
        if row < 0 or row >= len(self._icons):
            return
        name, path = self._icons[row]
        if os.path.exists(path):
            pix = QPixmap(path).scaled(170, 170, Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation)
            self.preview.setPixmap(pix)

    def _apply(self):
        row = self.list.currentRow()
        if row < 0 or row >= len(self._icons):
            return
        name = self._icons[row][0]
        if icon_manager.apply_icon(name):
            self.parent_app.settings["active_icon"] = name
            settings.save(self.parent_app.settings)
            new_icon = get_active_icon_path()
            if os.path.exists(new_icon):
                self.parent_app.setWindowIcon(QIcon(new_icon))
                self.parent_app._active_icon_path = new_icon
            self.parent_app.update_tray_icon()
            self._refresh()

    def _create(self):
        QMessageBox.information(self, "Генератор", "🎨 Генератор иконок — в следующем обновлении.")

    def _delete(self):
        row = self.list.currentRow()
        if row < 0 or row >= len(self._icons):
            return
        name = self._icons[row][0]
        if name in ("classic", "dark"):
            QMessageBox.warning(self, "Нельзя удалить", "Стандартная иконка.")
            return
        if icon_manager.delete_icon(name):
            self._refresh()

class ThemeDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Выбор темы")
        self.setFixedSize(500, 700)
        self.parent_app = parent
        self.selected_theme_id = self.parent_app.settings.get("theme", "dark")

        self._build_ui()

    def _build_ui(self):
        # очищаем
        if self.layout() is not None:
            old = self.layout()
            while old.count():
                item = old.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel("🎨 Выбери тему")
        title.setStyleSheet(f"color: {FG}; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # ==== Вкладки ====
        from modules.themes import THEMES, CATEGORIES, themes_by_category
        from modules import theme_manager

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {BORDER};
                border-radius: 8px;
                background: {BG_CARD};
            }}
            QTabBar::tab {{
                background: {BG_INPUT};
                color: {FG_DIM};
                padding: 8px 14px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 12px;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background: {ACCENT};
                color: white;
            }}
            QTabBar::tab:hover {{
                background: {BORDER};
                color: {FG};
            }}
        """)
        layout.addWidget(self.tabs, stretch=1)

        self._theme_buttons = []
        current = self.parent_app.settings.get("theme", "dark")

        # для каждой категории — своя вкладка
        for cat_key, cat_name in CATEGORIES.items():
            if cat_key == "custom":
                # свои темы — отдельно
                custom_list = theme_manager.list_custom_themes()
                if not custom_list:
                    continue
                themes_in_cat = [(t["id"], {"name": t["name"], "category": "custom"})
                                 for t in custom_list]
            elif cat_key == "all":
                # "Все" — объединяем всё
                themes_in_cat = []
                for k, t in THEMES.items():
                    if k.startswith("custom_"):
                        continue
                    themes_in_cat.append((k, t))
                for t in theme_manager.list_custom_themes():
                    themes_in_cat.append((t["id"], {"name": t["name"], "category": "custom"}))
            else:
                themes_in_cat = themes_by_category(cat_key)

            if not themes_in_cat:
                continue

            tab = self._make_tab(themes_in_cat, current, is_custom=(cat_key == "custom"))
            self.tabs.addTab(tab, cat_name)

        # ---- Кнопки внизу ----
        btn_row = QHBoxLayout()

        b_create = QPushButton("➕ Создать")
        b_create.setCursor(Qt.CursorShape.PointingHandCursor)
        b_create.clicked.connect(self._create_theme)
        btn_row.addWidget(b_create)

        b_delete = QPushButton("🗑 Удалить")
        b_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        b_delete.clicked.connect(self._delete_theme)
        btn_row.addWidget(b_delete)

        btn_row.addStretch()

        b_close = QPushButton("Закрыть")
        b_close.clicked.connect(self.accept)
        btn_row.addWidget(b_close)

        layout.addLayout(btn_row)

    def _make_tab(self, themes_list, current, is_custom=False):
        """Создаёт содержимое вкладки со списком тем."""
        from modules.themes import THEMES
        from modules import theme_manager

        # скролл
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        vbox = QVBoxLayout(inner)
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(6)

        for key, t in themes_list:
            display = t["name"] + ("  ✓" if key == current else "")

            b = QPushButton(display)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(38)
            b.setMouseTracking(True)

            # цвета темы
            try:
                card = t["BG_CARD"]
                accent = t["ACCENT"]
                fg = t["FG"]
                border = t["BORDER"]
                bg_in = t["BG_INPUT"]
            except KeyError:
                t_data = theme_manager.get_custom_theme(key)
                colors = theme_manager.build_full_theme(t_data["colors"]) if t_data else {}
                card = colors.get("BG_CARD", BG_CARD)
                accent = colors.get("ACCENT", ACCENT)
                fg = colors.get("FG", FG)
                border = colors.get("BORDER", BORDER)
                bg_in = colors.get("BG_INPUT", BG_INPUT)

            normal_style = f"""
                QPushButton {{
                    background-color: {card};
                    color: {fg};
                    border: 1px solid {border};
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 14px;
                    font-size: 12px;
                    font-weight: bold;
                }}
            """
            hover_style = f"""
                QPushButton {{
                    background-color: {bg_in};
                    color: {fg};
                    border: 2px solid {accent};
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 13px;
                    font-size: 12px;
                    font-weight: bold;
                }}
            """

            b.setStyleSheet(normal_style)
            b._normal_style = normal_style
            b._hover_style = hover_style
            b._is_hovered = False

            def _make_handlers(btn, accent_color):
                def on_enter(e):
                    if btn._is_hovered:
                        return
                    btn._is_hovered = True
                    shadow = QGraphicsDropShadowEffect(btn)
                    shadow.setBlurRadius(16)
                    shadow.setColor(QColor(accent_color))
                    shadow.setOffset(0, 4)
                    try:
                        shadow.setOpacity(0.5)
                    except Exception:
                        pass
                    btn.setGraphicsEffect(shadow)
                    btn.setStyleSheet(btn._hover_style)

                def on_leave(e):
                    if not btn._is_hovered:
                        return
                    btn._is_hovered = False
                    btn.setGraphicsEffect(None)
                    btn.setStyleSheet(btn._normal_style)

                btn.enterEvent = on_enter
                btn.leaveEvent = on_leave

            _make_handlers(b, accent)

            b.clicked.connect(lambda _, k=key: self._set_theme(k))
            vbox.addWidget(b)

        vbox.addStretch()
        scroll.setWidget(inner)
        return scroll

    def _create_theme(self):
        try:
            from modules.theme_configurator import ThemeConfiguratorDialog
        except ImportError as e:
            QMessageBox.warning(self, "Ошибка", f"Конфигуратор недоступен:\n{e}")
            return

        dlg = ThemeConfiguratorDialog(self.parent_app)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.saved_id:
            from modules import settings as _settings_mod
            fresh = _settings_mod.load()
            self.parent_app.settings["custom_themes"] = fresh.get("custom_themes", {})
        # достижения: тема
        try:
            from modules import achievements as ach_mod
            unlocked = ach_mod.track_theme(self.parent_app.settings, name)
            for ach_id in unlocked:
                ach = ach_mod.ACHIEVEMENTS.get(ach_id, {})
                ach_name = ach.get("name", ach_id)
                QTimer.singleShot(1000, lambda n=ach_name: QtToast(
                    self.parent_app, f"🏆 Достижение: {n}", duration=4000
                ))
        except Exception as e:
            print(f"⚠️ Достижения (тема): {e}")
            self.accept()
            QTimer.singleShot(50, lambda: ThemeDialog(self.parent_app).exec())

    def _delete_theme(self):
        from modules import theme_manager

        current = self.parent_app.settings.get("theme", "dark")
        custom = theme_manager.get_custom_theme(current)

        if not custom:
            QMessageBox.information(
                self, "Удалить",
                "Сейчас выбрана стандартная тема.\n"
                "Чтобы удалить свою — сначала выбери её (клик).\n"
                "Потом жми 🗑 Удалить."
            )
            return

        reply = QMessageBox.question(
            self, "Удалить тему",
            f"Удалить тему «{custom['name']}»?"
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if theme_manager.delete_custom_theme(current):
            from modules import settings as settings_module
            fresh = settings_module.load()
            self.parent_app.settings["custom_themes"] = fresh.get("custom_themes", {})
            self.parent_app.settings["theme"] = "dark"
            settings.save(self.parent_app.settings)
            QMessageBox.information(
                self, "Тема удалена",
                "Тема удалена. Применена тёмная тема.\n"
                "Перезапусти приложение."
            )
            self.accept()
            QTimer.singleShot(50, lambda: ThemeDialog(self.parent_app).exec())

    def _set_theme(self, name):
        """Применяет тему с анимацией и перезапуском."""
        from modules import settings as _settings_mod

        fresh = _settings_mod.load()
        fresh["theme"] = name
        _settings_mod.save(fresh)
        self.parent_app.settings["theme"] = name
        self.parent_app.settings["custom_themes"] = fresh.get("custom_themes", {})

        # достижения: тема
        try:
            from modules import achievements as ach_mod
            unlocked = ach_mod.track_theme(self.parent_app.settings, name)
            for ach_id in unlocked:
                ach = ach_mod.ACHIEVEMENTS.get(ach_id, {})
                ach_name = ach.get("name", ach_id)
                QTimer.singleShot(1000, lambda n=ach_name: QtToast(
                    self.parent_app, f"🏆 Достижение: {n}", duration=4000
                ))
            # сохраняем прогресс
            _settings_mod.save(self.parent_app.settings)
        except Exception as e:
            print(f"⚠️ Достижения (тема): {e}")

        if name == "frostmourne":
            try:
                from modules.sounds import ice_crack
                ice_crack()
            except Exception:
                pass
        self.accept()
        QTimer.singleShot(50, self.parent_app._restart_with_animation)

class QtToast(QWidget):
    """Всплывающее уведомление для PyQt6."""
    def __init__(self, parent, text, duration=3000, bg=None, fg=None):
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.ToolTip |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        bg = bg or BG_CARD
        fg = fg or FG

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {ACCENT};
                border-radius: 10px;
            }}
        """)
        outer.addWidget(card)

        inner = QVBoxLayout(card)
        inner.setContentsMargins(16, 12, 16, 12)

        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {fg}; font-size: 12px; background: transparent;")
        lbl.setWordWrap(True)
        inner.addWidget(lbl)

        self.adjustSize()

        screen = QApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()
        x = screen.right() - w - 30
        y = screen.bottom() - h - 30
        self.move(x, y)

        self.setWindowOpacity(0.0)
        self.show()
        self._fade_in(duration)

    def _fade_in(self, duration):
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(300)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()
        QTimer.singleShot(duration, self._fade_out)

    def _fade_out(self):
        self._anim_out = QPropertyAnimation(self, b"windowOpacity")
        self._anim_out.setDuration(300)
        self._anim_out.setStartValue(1.0)
        self._anim_out.setEndValue(0.0)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim_out.finished.connect(self.close)
        self._anim_out.start()


class CookieSetupDialog(QDialog):
    """Диалог настройки куки."""
    def __init__(self, parent, first_run=False):
        super().__init__(parent)
        self.setWindowTitle("Настройка куки")
        self.setFixedSize(500, 380)
        self.parent_app = parent
        self.first_run = first_run

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        icon_lbl = QLabel("🍪")
        icon_lbl.setStyleSheet("font-size: 48px;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        title = QLabel("Для скачивания с YouTube нужны куки")
        title.setStyleSheet(f"color: {FG}; font-size: 14px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        layout.addWidget(title)

        desc = QLabel(
            "YouTube требует авторизацию, чтобы подтвердить, что ты не бот.\n\n"
            "Выбери браузер, в котором ты залогинен в YouTube. "
            "Откроется окно браузера — залогинься (если нужно) и закрой его."
        )
        desc.setStyleSheet(f"color: {FG_DIM}; font-size: 11px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(10)

        browser_row = QHBoxLayout()
        browser_lbl = QLabel("Браузер:")
        browser_lbl.setStyleSheet(f"color: {FG}; font-size: 12px;")
        browser_row.addWidget(browser_lbl)

        self.browser_combo = QComboBox()
        try:
            from modules import cookie_export
            installed = cookie_export.get_installed_browsers()
            if not installed:
                installed = ["firefox", "chrome", "edge", "brave"]
        except Exception:
            installed = ["firefox", "chrome", "edge", "brave"]
        self.browser_combo.addItems([b.capitalize() for b in installed])
        browser_row.addWidget(self.browser_combo, stretch=1)
        layout.addLayout(browser_row)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        if not first_run:
            btn_cancel = QPushButton("Отмена")
            btn_cancel.clicked.connect(self.reject)
            btn_row.addWidget(btn_cancel)

        btn_ok = QPushButton("🍪 Получить куки")
        btn_ok.setObjectName("primary")
        btn_ok.clicked.connect(self._do_export)
        btn_row.addWidget(btn_ok)

        layout.addLayout(btn_row)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(f"color: {FG_DIM}; font-size: 11px;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_lbl)

    def _do_export(self):
        try:
            from modules import cookie_export
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Модуль экспорта не найден:\n{e}")
            return
        browser = self.browser_combo.currentText().lower()
        self.status_lbl.setText(f"🌐 Открываю {browser}...")
        QApplication.processEvents()

        path = cookie_export.export_cookies(
            browser,
            progress_callback=lambda msg: self.status_lbl.setText(msg)
        )

        if path:
            QtToast(self.parent_app, "✅ Куки сохранены! Можно качать.")
            self.accept()
        else:
            QMessageBox.warning(
                self, "Ошибка",
                "⚠️ Не удалось получить куки.\n"
                "Попробуй другой браузер или закрой браузер и повтори."
            )
            self.status_lbl.setText("")

class AdminPanelDialog(QDialog):
    """Админ-панель — всё для быстрого теста."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("🔧 Админ-панель")
        self.setFixedSize(560, 720)
        self.parent_app = parent

        # скролл на всю панель
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        outer.addWidget(scroll)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        scroll.setWidget(inner)

        title = QLabel("🔧 Админ-панель")
        title.setStyleSheet(f"color: {FG}; font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # ============================================
        # 1. СТАТИСТИКА
        # ============================================
        stats_title = QLabel("📊 Статистика")
        stats_title.setStyleSheet(f"color: {FG}; font-size: 14px; font-weight: bold;")
        layout.addWidget(stats_title)

        history = parent.settings.get("history", [])
        total = len(history)
        audio = sum(1 for h in history if h.get("file", "").lower().endswith(".mp3"))
        video = total - audio

        stats_box = QLabel(
            f"📥 Всего: {total}   🎵 Аудио: {audio}   🎬 Видео: {video}\n"
            f"🎨 Тема: {parent.settings.get('theme', 'dark')}\n"
            f"🧊 Liquid Glass: {'вкл' if parent.settings.get('liquid_glass') else 'выкл'}\n"
            f"🎄 Праздник: {parent.settings.get('admin_forced_holiday') or 'нет'}"
        )
        stats_box.setStyleSheet(
            f"color: {FG}; font-size: 12px; "
            f"background: {BG_CARD}; border: 1px solid {BORDER}; "
            f"border-radius: 8px; padding: 12px;"
        )
        layout.addWidget(stats_box)

        # ============================================
        # 2. ПРАЗДНИКИ (тест)
        # ============================================
        hol_title = QLabel("🎄 Праздники (форсировать)")
        hol_title.setStyleSheet(f"color: {FG}; font-size: 14px; font-weight: bold;")
        layout.addWidget(hol_title)

        hol_row = QHBoxLayout()

        self.holiday_combo = QComboBox()
        holidays = [
            ("— нет —", None),
            ("🎃 Хэллоуин", "halloween"),
            ("💀 Doomsday", "doomsday"),
            ("🎄 Новый год", "newyear"),
            ("🌸 8 марта", "march8"),
            ("🎒 1 сентября", "september1"),
            ("❤️ 14 февраля", "feb14"),
            ("🚀 12 апреля", "april12"),
            ("🎉 1 мая", "may1"),
            ("❄️ Frostmourne", "frostmourne"),
        ]
        for name, key in holidays:
            self.holiday_combo.addItem(name, key)

        current_holiday = parent.settings.get("admin_forced_holiday")
        for i in range(self.holiday_combo.count()):
            if self.holiday_combo.itemData(i) == current_holiday:
                self.holiday_combo.setCurrentIndex(i)
                break

        hol_row.addWidget(self.holiday_combo, stretch=1)

        b_apply_hol = QPushButton("Применить")
        b_apply_hol.clicked.connect(self._apply_holiday)
        hol_row.addWidget(b_apply_hol)

        layout.addLayout(hol_row)

        # ============================================
        # 3. LIQUID GLASS
        # ============================================
        lg_title = QLabel("🧊 Liquid Glass")
        lg_title.setStyleSheet(f"color: {FG}; font-size: 14px; font-weight: bold;")
        layout.addWidget(lg_title)

        self.lg_check = QCheckBox("Включить")
        self.lg_check.setChecked(parent.settings.get("liquid_glass", False))
        layout.addWidget(self.lg_check)

        lg_row = QHBoxLayout()
        lg_lbl = QLabel("Прозрачность:")
        lg_lbl.setStyleSheet(f"color: {FG_DIM}; font-size: 11px;")
        lg_lbl.setFixedWidth(100)
        lg_row.addWidget(lg_lbl)

        self.lg_slider = QSlider(Qt.Orientation.Horizontal)
        self.lg_slider.setRange(30, 90)
        self.lg_slider.setValue(parent.settings.get("liquid_opacity", 70))
        lg_row.addWidget(self.lg_slider, stretch=1)

        self.lg_val = QLabel(f"{self.lg_slider.value()}%")
        self.lg_val.setStyleSheet(f"color: {FG}; font-size: 11px;")
        self.lg_val.setFixedWidth(40)
        self.lg_slider.valueChanged.connect(lambda v: self.lg_val.setText(f"{v}%"))
        lg_row.addWidget(self.lg_val)

        layout.addLayout(lg_row)

        # ============================================
        # 4. ТЕМА (быстро)
        # ============================================
        theme_title = QLabel("🎨 Тема (быстро)")
        theme_title.setStyleSheet(f"color: {FG}; font-size: 14px; font-weight: bold;")
        layout.addWidget(theme_title)

        theme_row = QHBoxLayout()

        self.theme_combo = QComboBox()
        from modules.themes import THEMES
        for key, t in THEMES.items():
            if key.startswith("custom_"):
                continue
            self.theme_combo.addItem(t["name"], key)

        current_theme = parent.settings.get("theme", "dark")
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == current_theme:
                self.theme_combo.setCurrentIndex(i)
                break

        theme_row.addWidget(self.theme_combo, stretch=1)

        b_apply_theme = QPushButton("Применить")
        b_apply_theme.clicked.connect(self._apply_theme)
        theme_row.addWidget(b_apply_theme)

        layout.addLayout(theme_row)

        # ============================================
        # 5. БЫСТРЫЕ ДЕЙСТВИЯ
        # ============================================
        quick_title = QLabel("⚡ Быстрые действия")
        quick_title.setStyleSheet(f"color: {FG}; font-size: 14px; font-weight: bold;")
        layout.addWidget(quick_title)

        quick_row1 = QHBoxLayout()

        b_random = QPushButton("🎲 Случайная тема")
        b_random.clicked.connect(self._random_theme)
        quick_row1.addWidget(b_random)

        b_rainbow = QPushButton("🌈 Радуга")
        b_rainbow.clicked.connect(self._rainbow_themes)
        quick_row1.addWidget(b_rainbow)

        layout.addLayout(quick_row1)

        quick_row2 = QHBoxLayout()
        
        # ❄️ Фростморн
        b_frost = QPushButton("❄️ Взять Фростморн")
        b_frost.setStyleSheet(
            "background: #1a3a5a; color: #88ccff; "
            "font-weight: bold; padding: 10px;"
        )
        b_frost.clicked.connect(self._take_frostmourne)
        layout.addWidget(b_frost)
        # голосовые кнопки
        voice_row = QHBoxLayout()

        b_voice1 = QPushButton("🎤 «К чёрту людей!»")
        b_voice1.clicked.connect(lambda: self._play_voice("KChortuLudei!.mp3"))
        voice_row.addWidget(b_voice1)

        b_voice2 = QPushButton("🎤 «Я с радостью приму»")
        b_voice2.clicked.connect(lambda: self._play_voice("YaSRadost'uPrimu.mp3"))
        voice_row.addWidget(b_voice2)

        layout.addLayout(voice_row)

        b_reload = QPushButton("🔄 Перезапуск")
        b_reload.clicked.connect(self._reload)
        quick_row2.addWidget(b_reload)

        b_test_link = QPushButton("🎬 Тест-ссылка")
        b_test_link.clicked.connect(self._test_link)
        quick_row2.addWidget(b_test_link)

        layout.addLayout(quick_row2)

        # ============================================
        # 6. DEBUG
        # ============================================
        debug_title = QLabel("🐛 Debug")
        debug_title.setStyleSheet(f"color: {FG}; font-size: 14px; font-weight: bold;")
        layout.addWidget(debug_title)

        self.debug_logs = QCheckBox("Логи в консоль")
        self.debug_logs.setChecked(parent.settings.get("debug_logs", False))
        layout.addWidget(self.debug_logs)

        self.debug_ids = QCheckBox("Показывать ID форматов")
        self.debug_ids.setChecked(parent.settings.get("debug_ids", False))
        layout.addWidget(self.debug_ids)

        self.debug_paths = QCheckBox("Показывать пути файлов")
        self.debug_paths.setChecked(parent.settings.get("debug_paths", False))
        layout.addWidget(self.debug_paths)

        # ============================================
        # 7. СБРОС
        # ============================================
        reset_title = QLabel("🗑 Сброс")
        reset_title.setStyleSheet(f"color: {FG}; font-size: 14px; font-weight: bold;")
        layout.addWidget(reset_title)

        reset_row = QHBoxLayout()

        b_reset_hist = QPushButton("Историю")
        b_reset_hist.clicked.connect(self._reset_history)
        reset_row.addWidget(b_reset_hist)

        b_reset_all = QPushButton("ВСЁ")
        b_reset_all.setStyleSheet(f"background: {ACCENT}; color: white;")
        b_reset_all.clicked.connect(self._reset_all)
        reset_row.addWidget(b_reset_all)

        layout.addLayout(reset_row)

        layout.addStretch()

        # ============================================
        # 8. КНОПКИ ВНИЗУ
        # ============================================
        btn_row = QHBoxLayout()

        b_disable_admin = QPushButton("🚪 Выйти из админа")
        b_disable_admin.clicked.connect(self._disable_admin)
        btn_row.addWidget(b_disable_admin)

        btn_row.addStretch()

        b_save = QPushButton("Сохранить")
        b_save.setObjectName("primary")
        b_save.clicked.connect(self._save)
        btn_row.addWidget(b_save)

        b_close = QPushButton("Закрыть")
        b_close.clicked.connect(self.accept)
        btn_row.addWidget(b_close)

        layout.addLayout(btn_row)

    # ============================================
    # МЕТОДЫ
    # ============================================

    def _apply_holiday(self):
        """Форсирует праздник."""
        holiday_key = self.holiday_combo.currentData()
        self.parent_app.settings["admin_forced_holiday"] = holiday_key
        settings.save(self.parent_app.settings)
        QMessageBox.information(
            self, "Праздник",
            f"Праздник: {self.holiday_combo.currentText()}\n"
            f"Перезапусти приложение."
        )

    def _apply_theme(self):
        """Применяет выбранную тему + сбрасывает форсированный праздник."""
        theme_key = self.theme_combo.currentData()
        self.parent_app.settings["theme"] = theme_key
        # сбрасываем форсированный праздник, чтобы не оставался
        self.parent_app.settings["admin_forced_holiday"] = None

        # достижения: тема
        try:
            from modules import achievements as ach_mod
            unlocked = ach_mod.track_theme(self.parent_app.settings, theme_key)
            for ach_id in unlocked:
                ach = ach_mod.ACHIEVEMENTS.get(ach_id, {})
                ach_name = ach.get("name", ach_id)
                QTimer.singleShot(1000, lambda n=ach_name: QtToast(
                    self.parent_app, f"🏆 Достижение: {n}", duration=4000
                ))
        except Exception as e:
            print(f"⚠️ Достижения (тема): {e}")

        settings.save(self.parent_app.settings)

        # хруст льда, если тема Frostmourne
        if theme_key == "frostmourne":
            try:
                from modules.sounds import ice_crack
                ice_crack()
            except Exception:
                pass

        self.accept()
        QTimer.singleShot(50, self.parent_app._restart_with_animation)
     
    def _play_voice(self, filename):
        """Играет звук из admin_assets/sounds/."""
        try:
            from modules.sounds import play_admin_mp3
            if play_admin_mp3(filename):
                print(f"🔊 {filename}")
            else:
                QMessageBox.warning(
                    self, "Нет файла",
                    f"Файл не найден:\nadmin_assets/sounds/{filename}"
                )
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", str(e))

    def _take_frostmourne(self):
        """Пасхалка: Артас берёт Фростморн."""
        # играем "Я с радостью приму проклятие"
        try:
            from modules.sounds import play_admin_mp3
            play_admin_mp3("YaSRadost'uPrimu.mp3")
        except Exception as e:
            print(f"⚠️ Голос: {e}")

        # диалог через 4 сек
        QTimer.singleShot(4000, lambda: QMessageBox.information(
            self, "❄️ Фростморн",
            "«Я с радостью приму на себя проклятие»\n\n"
            "Ты взял Фростморн. Ты — Король-лич.\n"
            "Тема: Frostmourne. Черепа падают.\n\n"
            "Перезапусти приложение."
        ))

        # ставим тему и праздник
        self.parent_app.settings["theme"] = "frostmourne"
        self.parent_app.settings["admin_forced_holiday"] = "frostmourne"
        # достижения: Фростморн
        try:
            from modules import achievements as ach_mod
            unlocked = ach_mod.track_frostmourne_taken(self.parent_app.settings)
            for ach_id in unlocked:
                ach = ach_mod.ACHIEVEMENTS.get(ach_id, {})
                ach_name = ach.get("name", ach_id)
                QTimer.singleShot(5000, lambda n=ach_name: QtToast(
                    self.parent_app, f"🏆 Достижение: {n}", duration=4000
                ))
        except Exception as e:
            print(f"⚠️ Достижения (Фростморн): {e}")
            print(f"⚠️ Достижения (Фростморн): {e}")
        settings.save(self.parent_app.settings)
        self.accept()

        # перезапуск через 4.5 сек
        QTimer.singleShot(4500, self.parent_app._restart_with_animation)

    def _random_theme(self):
        """Случайная тема + сброс праздника."""
        import random
        from modules.themes import THEMES
        keys = [k for k in THEMES.keys() if not k.startswith("custom_")]
        theme_key = random.choice(keys)
        self.parent_app.settings["theme"] = theme_key
        self.parent_app.settings["admin_forced_holiday"] = None

        # достижения: тема
        try:
            from modules import achievements as ach_mod
            unlocked = ach_mod.track_theme(self.parent_app.settings, theme_key)
            for ach_id in unlocked:
                ach = ach_mod.ACHIEVEMENTS.get(ach_id, {})
                ach_name = ach.get("name", ach_id)
                QTimer.singleShot(1000, lambda n=ach_name: QtToast(
                    self.parent_app, f"🏆 Достижение: {n}", duration=4000
                ))
        except Exception as e:
            print(f"⚠️ Достижения (тема): {e}")

        settings.save(self.parent_app.settings)
        self.accept()
        QTimer.singleShot(50, self.parent_app._restart_with_animation)

    def _rainbow_themes(self):
        """Радуга — быстрая смена тем."""
        from modules.themes import THEMES
        keys = [k for k in THEMES.keys() if not k.startswith("custom_")]

        # проходим по 10 темам с задержкой 200мс
        self.parent_app.settings["admin_forced_holiday"] = None

        def _step(idx):
            if idx >= 10:
                return
            theme_key = keys[idx % len(keys)]
            self.parent_app.settings["theme"] = theme_key
            settings.save(self.parent_app.settings)
            QTimer.singleShot(200, lambda: _step(idx + 1))

        _step(0)
        QMessageBox.information(
            self, "Радуга",
            "Темы меняются. После — перезапусти приложение."
        )

    def _reload(self):
        """Перезапускает приложение."""
        self.accept()
        QTimer.singleShot(50, self.parent_app._restart_with_animation)

    def _test_link(self):
        """Вставляет тестовую ссылку."""
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.parent_app.url_input.setText(test_url)
        QMessageBox.information(
            self, "Тест",
            f"Ссылка вставлена:\n{test_url}"
        )

    def _reset_history(self):
        reply = QMessageBox.question(
            self, "Сброс",
            "Очистить историю скачиваний?"
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.parent_app.settings["history"] = []
            settings.save(self.parent_app.settings)
            QMessageBox.information(self, "Готово", "История очищена.")

    def _reset_all(self):
        reply = QMessageBox.question(
            self, "Сброс ВСЕГО",
            "Сбросить ВСЕ настройки?\n"
            "Это удалит историю, профили, темы."
        )
        if reply == QMessageBox.StandardButton.Yes:
            from modules.settings import DEFAULTS
            new_settings = dict(DEFAULTS)
            new_settings["admin_mode"] = True  # оставляем админку
            settings.save(new_settings)
            QMessageBox.information(
                self, "Готово",
                "Все настройки сброшены.\nПерезапусти приложение."
            )

    def _disable_admin(self):
        reply = QMessageBox.question(
            self, "Выйти из админа",
            "Выключить админ-режим?\n"
            "Кнопка 🔧 исчезнет после перезапуска."
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.parent_app.settings["admin_mode"] = False
            settings.save(self.parent_app.settings)
            self.accept()
            QTimer.singleShot(50, self.parent_app._restart_with_animation)

    def _save(self):
        """Сохраняет настройки."""
        self.parent_app.settings["liquid_glass"] = self.lg_check.isChecked()
        self.parent_app.settings["liquid_opacity"] = self.lg_slider.value()
        self.parent_app.settings["debug_logs"] = self.debug_logs.isChecked()
        self.parent_app.settings["debug_ids"] = self.debug_ids.isChecked()
        self.parent_app.settings["debug_paths"] = self.debug_paths.isChecked()
        settings.save(self.parent_app.settings)
        QMessageBox.information(self, "Готово", "Настройки сохранены.")


# ============================================================
#                    ЗАПУСК
# ============================================================
def run():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")

    try:
        from modules.sounds import startup
        startup()
    except Exception:
        pass

    window = DownloaderApp()
    window.show()

    app.exec()


if __name__ == "__main__":
    run()