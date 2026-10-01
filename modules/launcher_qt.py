"""
Лаунчер на PyQt6 — выбор версии (Classic / Modern).
С fade-out анимацией при переключении на Tkinter-лаунчер.
"""

import sys
import os
import subprocess

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QCheckBox,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QIcon

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import set_preferred_gui, get_active_icon_path, APP_VERSION


# Цвета (Modern)
BG = "#1e1e1e"
BG_CARD = "#2a2a2a"
FG = "#e0e0e0"
FG_DIM = "#888888"
ACCENT = "#e62117"
ACCENT_HOVER = "#ff3b30"
BORDER = "#3a3a3a"


class ChoiceCard(QFrame):
    """Карточка выбора версии."""
    def __init__(self, title, subtitle, description, is_recommended=False, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.is_selected = False
        self.is_recommended = is_recommended
        self._parent_launcher = parent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # Заголовок + бейдж
        title_row = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {FG}; font-size: 18px; font-weight: bold; background: transparent;")
        title_row.addWidget(title_lbl)

        if is_recommended:
            badge = QLabel("Рекомендуется")
            badge.setStyleSheet(f"""
                background-color: {ACCENT};
                color: white;
                font-size: 10px;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 8px;
            """)
            title_row.addWidget(badge)

        title_row.addStretch()
        layout.addLayout(title_row)

        # Подзаголовок
        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet(f"color: {ACCENT}; font-size: 12px; font-weight: bold; background: transparent;")
        layout.addWidget(sub_lbl)

        # Описание
        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet(f"color: {FG_DIM}; font-size: 11px; background: transparent;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        self.setMinimumHeight(140)
        self._refresh_style()

    def set_selected(self, selected):
        self.is_selected = selected
        self._refresh_style()

    def _refresh_style(self):
        if self.is_selected:
            border = f"2px solid {ACCENT}"
        else:
            border = f"1px solid {BORDER}"

        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: {BG_CARD};
                border: {border};
                border-radius: 12px;
            }}
            QFrame#card:hover {{
                border: 1px solid {ACCENT};
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._parent_launcher:
                self._parent_launcher._on_card_clicked(self)
        super().mousePressEvent(event)


class LauncherWindow(QWidget):
    def __init__(self, chosen=None):
        super().__init__()
        self.selected = chosen or "qt"
        self._closing = False

        self.setWindowTitle("YouTube Downloader — Выбор версии")
        self.setStyleSheet(f"background-color: {BG};")
        self.resize(560, 500)

        icon_path = get_active_icon_path()
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        # Заголовок
        title = QLabel("YouTube Downloader")
        title.setStyleSheet(f"color: {FG}; font-size: 24px; font-weight: bold; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(f"v{APP_VERSION} — выбери версию")
        subtitle.setStyleSheet(f"color: {FG_DIM}; font-size: 12px; background: transparent;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        # Modern (Qt)
        self.card_qt = ChoiceCard(
            "🎨 Modern",
            "PyQt6 — активно развивается",
            "Современный интерфейс, плавные анимации, тени, "
            "праздничные темы с падающими объектами. "
            "Все новые функции — здесь.",
            is_recommended=True,
            parent=self,
        )
        layout.addWidget(self.card_qt)

        # Classic (Tkinter)
        self.card_tk = ChoiceCard(
            "🌙 Classic",
            "Tkinter — архивная версия",
            "Проверенный временем интерфейс. Всё, что нужно для скачивания. "
            "Больше не обновляется — только стабильность. "
            "Финальная версия v0.4.2.",
            is_recommended=False,
            parent=self,
        )
        layout.addWidget(self.card_tk)

        layout.addStretch()

        # Чекбокс "Запомнить"
        self.remember_cb = QCheckBox("Запомнить выбор (не спрашивать в следующий раз)")
        self.remember_cb.setStyleSheet(f"""
            QCheckBox {{
                color: {FG};
                font-size: 12px;
                spacing: 8px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 16px; height: 16px;
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {ACCENT};
                border: 1px solid {ACCENT};
            }}
        """)
        self.remember_cb.setChecked(True)
        layout.addWidget(self.remember_cb)

        # Кнопка "Вперёд"
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_forward = QPushButton("Вперёд →")
        self.btn_forward.setFixedHeight(44)
        self.btn_forward.setMinimumWidth(160)
        self.btn_forward.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_forward.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 24px;
            }}
            QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}
            QPushButton:pressed {{ background-color: #b71c1c; }}
        """)
        self.btn_forward.clicked.connect(self._on_forward)
        btn_row.addWidget(self.btn_forward)

        layout.addLayout(btn_row)

        # Изначально выбран Modern
        self._select(self.card_qt)

    def _on_card_clicked(self, card):
        """Клик по карточке — переключаем выбор. Если Classic — fade-out и запуск Tkinter."""
        if card is self.card_qt:
            self._select(self.card_qt)
        else:
            self._select(self.card_tk)
            QTimer.singleShot(200, self._switch_to_tkinter)

    def _select(self, card):
        self.card_qt.set_selected(card is self.card_qt)
        self.card_tk.set_selected(card is self.card_tk)
        self.selected = "qt" if card is self.card_qt else "tkinter"

    def _center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.x() + (screen.width() - self.width()) // 2
        y = screen.y() + (screen.height() - self.height()) // 2
        self.move(x, y)

    def _fade_in(self):
        self.setWindowOpacity(0.0)
        self._anim_in = QPropertyAnimation(self, b"windowOpacity")
        self._anim_in.setDuration(250)
        self._anim_in.setStartValue(0.0)
        self._anim_in.setEndValue(1.0)
        self._anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_in.start()

    def _fade_out(self, on_done=None):
        self._anim_out = QPropertyAnimation(self, b"windowOpacity")
        self._anim_out.setDuration(250)
        self._anim_out.setStartValue(1.0)
        self._anim_out.setEndValue(0.0)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InCubic)
        if on_done:
            self._anim_out.finished.connect(on_done)
        self._anim_out.start()

    def _switch_to_tkinter(self):
        if self._closing:
            return
        self._closing = True

        def _launch():
            QApplication.quit()
            from modules import launcher_dark
            launcher_dark.run()

        self._fade_out(_launch)

    def _on_forward(self):
        """Кнопка Вперёд — запускаем выбранную версию."""
        if self.remember_cb.isChecked():
            set_preferred_gui(self.selected)

        selected = self.selected

        def _launch():
            QApplication.quit()
            if selected == "qt":
                from modules import gui_qt
                gui_qt.run()
            else:
                from modules import gui_dark
                gui_dark.run()

        self._fade_out(_launch)


def run(chosen=None):
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = LauncherWindow(chosen=chosen)

    # 1) Показываем (layout рассчитается)
    window.show()

    # 2) Центрируем ПОСЛЕ показа
    screen = QApplication.primaryScreen().availableGeometry()
    x = screen.x() + (screen.width() - window.width()) // 2
    y = screen.y() + (screen.height() - window.height()) // 2
    window.move(x, y)

    # 3) Fade-in через 50 мс — чтобы layout точно был готов
    QTimer.singleShot(50, window._fade_in)

    sys.exit(app.exec())


if __name__ == "__main__":
    # парсим --chosen из аргументов
    chosen = None
    for arg in sys.argv:
        if arg.startswith("--chosen="):
            chosen = arg.split("=", 1)[1]
    run(chosen)
    run(chosen)