"""
Диалог конфигуратора тем.
Гибрид: 3 базовых цвета + расширенный режим.

Цвета берутся из gui_qt (текущая тема приложения).
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QWidget, QColorDialog, QMessageBox, QScrollArea,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from modules import theme_manager


def _get_current_colors(parent=None):
    """Берёт цвета текущей темы (учитывая праздник и parent)."""
    if parent is not None and hasattr(parent, "settings"):
        try:
            from modules.themes import get_theme
            if getattr(parent, "_holiday_mode", False):
                theme_name = parent._holiday_theme
            else:
                theme_name = parent.settings.get("theme", "dark")
            t = get_theme(theme_name)
            return {
                "BG": t["BG"],
                "BG_CARD": t["BG_CARD"],
                "BG_INPUT": t["BG_INPUT"],
                "FG": t["FG"],
                "FG_DIM": t["FG_DIM"],
                "ACCENT": t["ACCENT"],
                "BORDER": t["BORDER"],
            }
        except Exception as e:
            print(f"DEBUG _get_current_colors(parent) error: {e}")

    try:
        from modules import gui_qt as g
        return {
            "BG": g.BG,
            "BG_CARD": g.BG_CARD,
            "BG_INPUT": g.BG_INPUT,
            "FG": g.FG,
            "FG_DIM": g.FG_DIM,
            "ACCENT": g.ACCENT,
            "BORDER": g.BORDER,
        }
    except Exception:
        return {
            "BG": "#1e1e1e",
            "BG_CARD": "#2a2a2a",
            "BG_INPUT": "#333333",
            "FG": "#e0e0e0",
            "FG_DIM": "#888888",
            "ACCENT": "#e62117",
            "BORDER": "#3a3a3a",
        }


def _is_dark(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return (r + g + b) < 128 * 3


class ColorPicker(QWidget):
    """Строка: название + кнопка с текущим цветом."""

    def __init__(self, label_text, color_hex, on_change=None, parent=None,
                 theme_bg_card="#2a2a2a", theme_fg="#e0e0e0", theme_accent="#e62117",
                 theme_border="#3a3a3a", theme_fg_dim="#888888"):
        super().__init__(parent)
        self.label_text = label_text
        self.color_hex = color_hex
        self.on_change = on_change
        self.theme_bg_card = theme_bg_card
        self.theme_fg = theme_fg
        self.theme_accent = theme_accent
        self.theme_border = theme_border
        self.theme_fg_dim = theme_fg_dim

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        lbl = QLabel(label_text)
        lbl.setMinimumWidth(180)
        lbl.setStyleSheet(f"color: {theme_fg_dim}; font-size: 12px; background: transparent;")
        layout.addWidget(lbl)

        self.color_btn = QPushButton(color_hex)
        self.color_btn.setFixedHeight(30)
        self.color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_btn_style()
        self.color_btn.clicked.connect(self._pick)
        layout.addWidget(self.color_btn, stretch=1)

    def _apply_btn_style(self):
        text_color = "white" if _is_dark(self.color_hex) else "black"
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color_hex};
                color: {text_color};
                border: 1px solid {self.theme_border};
                border-radius: 7px;
                font-family: Consolas, monospace;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border: 2px solid {self.theme_accent};
            }}
        """)

    def _pick(self):
        color = QColorDialog.getColor(
            QColor(self.color_hex), self,
            f"Выбери цвет: {self.label_text}",
        )
        if color.isValid():
            self.set_color(color.name())

    def set_color(self, hex_color):
        self.color_hex = hex_color
        self.color_btn.setText(hex_color)
        self._apply_btn_style()
        if self.on_change:
            self.on_change(self.color_hex)

    def get_color(self):
        return self.color_hex


class ThemeConfiguratorDialog(QDialog):
    def __init__(self, parent, theme_id=None):
        super().__init__(parent)
        self.setWindowTitle("Конфигуратор темы")
        self.setFixedSize(600, 720)
        self.parent_app = parent
        self.theme_id = theme_id
        self.saved_id = None
        self.expanded = False

        # цвета текущей темы — С PARENT!
        self.c = _get_current_colors(parent)
        print(f"DEBUG theme_configurator: BG={self.c['BG']}, ACCENT={self.c['ACCENT']}, FG={self.c['FG']}")

        # базовые цвета — из текущей темы
        self.base_colors = {
            "BG": self.c["BG"],
            "ACCENT": self.c["ACCENT"],
            "FG": self.c["FG"],
        }
        self.extra_colors = {}

        self._build_ui()

        if self.theme_id:
            self._load_existing()

        self._update_preview()

        # фон диалога — от текущей темы
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.c["BG"]};
            }}
            QLabel {{
                color: {self.c["FG"]};
                background: transparent;
            }}
            QLineEdit {{
                background-color: {self.c["BG_INPUT"]};
                color: {self.c["FG"]};
                border: 1px solid {self.c["BORDER"]};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.c["ACCENT"]};
            }}
            QPushButton {{
                background-color: {self.c["BG_CARD"]};
                color: {self.c["FG"]};
                border: 1px solid {self.c["BORDER"]};
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                border: 1px solid {self.c["ACCENT"]};
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {self.c["BG"]};
                width: 8px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.c["BORDER"]};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {self.c["ACCENT"]};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                background: none; height: 0;
            }}
        """)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Заголовок
        title = QLabel("🎨 Конфигуратор темы")
        title.setStyleSheet(f"color: {self.c['FG']}; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Название
        name_row = QHBoxLayout()
        name_lbl = QLabel("Название:")
        name_lbl.setStyleSheet(f"color: {self.c['FG_DIM']}; font-size: 12px;")
        name_lbl.setMinimumWidth(80)
        name_row.addWidget(name_lbl)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Например: 💙 Моя синяя")
        name_row.addWidget(self.name_input, stretch=1)
        layout.addLayout(name_row)

        # Скролл с цветами
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_inner = QWidget()
        scroll_inner.setStyleSheet("background: transparent;")
        self.colors_layout = QVBoxLayout(scroll_inner)
        self.colors_layout.setSpacing(6)
        self.colors_layout.setContentsMargins(0, 6, 0, 6)

        # ---- Базовые цвета ----
        base_lbl = QLabel("Базовые цвета")
        base_lbl.setStyleSheet(f"color: {self.c['FG']}; font-size: 13px; font-weight: bold; padding-top: 4px;")
        self.colors_layout.addWidget(base_lbl)

        self.pickers = {}
        for key, label in [
            ("BG", "Фон (BG)"),
            ("ACCENT", "Акцент (ACCENT)"),
            ("FG", "Текст (FG)"),
        ]:
            p = ColorPicker(
                label, self.base_colors[key],
                on_change=lambda c, k=key: self._on_color_change(k, c),
                theme_fg_dim=self.c["FG_DIM"],
                theme_border=self.c["BORDER"],
                theme_accent=self.c["ACCENT"],
            )
            self.pickers[key] = p
            self.colors_layout.addWidget(p)

        # ---- Расширенный блок (скрыт) ----
        self.extra_widget = QWidget()
        self.extra_widget.setStyleSheet("background: transparent;")
        extra_layout = QVBoxLayout(self.extra_widget)
        extra_layout.setContentsMargins(0, 6, 0, 0)
        extra_layout.setSpacing(6)

        extra_lbl = QLabel("Дополнительные цвета")
        extra_lbl.setStyleSheet(f"color: {self.c['FG']}; font-size: 13px; font-weight: bold;")
        extra_layout.addWidget(extra_lbl)

        full = theme_manager.build_full_theme(self.base_colors)
        for key, label in [
            ("BG_CARD", "Карточка (BG_CARD)"),
            ("BG_INPUT", "Поле ввода (BG_INPUT)"),
            ("FG_DIM", "Тусклый текст (FG_DIM)"),
            ("ACCENT_HOVER", "Акцент hover"),
            ("ACCENT_PRESS", "Акцент press"),
            ("BORDER", "Граница (BORDER)"),
        ]:
            p = ColorPicker(
                label, full.get(key, "#000000"),
                on_change=lambda c, k=key: self._on_extra_change(k, c),
                theme_fg_dim=self.c["FG_DIM"],
                theme_border=self.c["BORDER"],
                theme_accent=self.c["ACCENT"],
            )
            self.pickers[key] = p
            extra_layout.addWidget(p)

        self.extra_widget.setVisible(False)
        self.colors_layout.addWidget(self.extra_widget)
        self.colors_layout.addStretch()
        scroll.setWidget(scroll_inner)

        layout.addWidget(scroll, stretch=1)

        # ---- Превью (всегда внизу, фикс. высота) ----
        preview_lbl = QLabel("Превью")
        preview_lbl.setStyleSheet(f"color: {self.c['FG_DIM']}; font-size: 11px;")
        layout.addWidget(preview_lbl)

        self.preview = QWidget()
        self.preview.setFixedHeight(70)
        layout.addWidget(self.preview)

        # ---- Кнопки ----
        btn_row = QHBoxLayout()

        self.btn_expand = QPushButton("⚙️ Расширенный режим")
        self.btn_expand.clicked.connect(self._toggle_expanded)
        btn_row.addWidget(self.btn_expand)

        btn_row.addStretch()

        b_cancel = QPushButton("Отмена")
        b_cancel.clicked.connect(self.reject)
        btn_row.addWidget(b_cancel)

        b_save = QPushButton("💾 Сохранить")
        b_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.c['ACCENT']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 18px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.c['ACCENT']};
            }}
        """)
        b_save.clicked.connect(self._save)
        btn_row.addWidget(b_save)

        layout.addLayout(btn_row)

    def _load_existing(self):
        theme = theme_manager.get_custom_theme(self.theme_id)
        if not theme:
            return
        self.name_input.setText(theme["name"])
        colors = theme["colors"]
        for key in ("BG", "ACCENT", "FG"):
            if key in colors:
                self.base_colors[key] = colors[key]
                self.pickers[key].set_color(colors[key])
        for key in ("BG_CARD", "BG_INPUT", "FG_DIM", "ACCENT_HOVER", "ACCENT_PRESS", "BORDER"):
            if key in colors:
                self.extra_colors[key] = colors[key]
                self.pickers[key].set_color(colors[key])

    def _on_color_change(self, key, color):
        self.base_colors[key] = color
        full = theme_manager.build_full_theme(self.base_colors)
        for k in ("BG_CARD", "BG_INPUT", "FG_DIM", "ACCENT_HOVER", "ACCENT_PRESS", "BORDER"):
            if k not in self.extra_colors:
                self.pickers[k].set_color(full.get(k, "#000000"))
        self._update_preview()

    def _on_extra_change(self, key, color):
        self.extra_colors[key] = color
        self._update_preview()

    def _toggle_expanded(self):
        self.expanded = not self.expanded
        self.extra_widget.setVisible(self.expanded)
        self.btn_expand.setText(
            "⚙️ Скрыть" if self.expanded else "⚙️ Расширенный режим"
        )

    def _update_preview(self):
        full = theme_manager.build_full_theme(self.base_colors)
        for k, v in self.extra_colors.items():
            full[k] = v

        bg = full["BG"]
        card = full["BG_CARD"]
        accent = full["ACCENT"]
        fg = full["FG"]
        border = full["BORDER"]
        bg_input = full["BG_INPUT"]
        fg_dim = full["FG_DIM"]

        self.preview.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 10px;
            }}
        """)

        # очищаем
        for child in self.preview.findChildren(QWidget):
            child.deleteLater()

        # пересоздаём layout
        old_layout = self.preview.layout()
        if old_layout:
            QWidget().setLayout(old_layout)

        inner = QHBoxLayout(self.preview)
        inner.setContentsMargins(10, 8, 10, 8)
        inner.setSpacing(8)

        btn = QPushButton("⬇ Скачать")
        btn.setEnabled(False)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        inner.addWidget(btn)

        line = QLabel("https://youtube.com/...")
        line.setStyleSheet(f"""
            background-color: {bg_input};
            color: {fg_dim};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 10px;
        """)
        inner.addWidget(line, stretch=1)

    def _save(self):
        name = self.name_input.text().strip()
        print(f"[SAVE] name='{name}'")
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введи название темы.")
            return

        from modules.themes import THEMES
        if not self.theme_id:
            for k, t in THEMES.items():
                if t.get("name", "").lower() == name.lower():
                    QMessageBox.warning(self, "Ошибка", "Тема с таким именем уже есть.")
                    return

        colors = dict(self.base_colors)
        colors.update(self.extra_colors)
        print(f"[SAVE] colors={colors}")

        theme_id = theme_manager.save_custom_theme(name, colors, theme_id=self.theme_id)
        print(f"[SAVE] theme_id={theme_id}")

        if not theme_id:
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить тему.")
            return

        self.saved_id = theme_id
        self.accept()