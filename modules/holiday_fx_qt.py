"""
Праздничные украшения по краям окна — PyQt6 edition.
Рисует гирлянду, тыквы, сердечки и т.д. по периметру.
"""

import math
import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont


# Настройки для каждого праздника
HOLIDAY_STYLES = {
    "newyear": {
        "lights": ["#ff0000", "#00ff00", "#0066ff", "#ffff00", "#ff00ff"],
        "corners": ["🎄", "🎁"],
        "glow": True,
    },
    "halloween": {
        "lights": ["#ff8800", "#ff6600", "#ffaa00", "#cc5500"],
        "corners": ["🎃", "👻"],
        "glow": True,
    },
    "feb14": {
        "lights": ["#ff2d6f", "#ff6699", "#ff0044"],
        "corners": ["❤️", "💕"],
        "glow": True,
    },
    "march8": {
        "lights": ["#ff66b3", "#ff99cc", "#ff3388"],
        "corners": ["🌸", "🌷"],
        "glow": True,
    },
    "april12": {
        "lights": ["#4d8cff", "#77aaff", "#2a66cc"],
        "corners": ["🚀", "⭐"],
        "glow": True,
    },
    "doomsday": {
        "lights": ["#ff0000", "#aa0000", "#ff4444"],
        "corners": ["💀", "☠️"],
        "glow": True,
        "special": "fire",
    },
    "september1": {
        "lights": ["#ff8c00", "#ffaa33", "#cc5500"],
        "corners": ["🎒", "📚"],
        "glow": True,
    },
    "may1": {
        "lights": ["#4dd94d", "#77ff77", "#2aaa2a"],
        "corners": ["🎈", "🌷"],
        "glow": True,
    },
}


class HolidayLights(QWidget):
    """Гирлянда с рандомными вспышками лампочек."""

    def __init__(self, parent, holiday_name, count=25):
        super().__init__(parent)
        self.holiday_name = holiday_name
        self.style = HOLIDAY_STYLES.get(holiday_name, HOLIDAY_STYLES["newyear"])
        self.count = count

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # яркость каждой лампочки (0.0 — 1.0)
        self.brightness = [random.uniform(0.6, 0.9) for _ in range(count)]

        # таймер мерцания (20 FPS)
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        # таймер случайных вспышек
        self._flash_timer = QTimer(self)
        self._flash_timer.setInterval(300)  # каждые 300мс
        self._flash_timer.timeout.connect(self._random_flash)
        self._flash_timer.start()

        self.setFixedHeight(30)

    def _random_flash(self):
        """Случайная лампочка вспыхивает на полную."""
        if not self.brightness:
            return
        idx = random.randint(0, len(self.brightness) - 1)
        self.brightness[idx] = 1.0

    def _tick(self):
        """Плавное затухание + лёгкое мерцание."""
        for i in range(len(self.brightness)):
            # затухание к базовому уровню
            base = 0.55
            if self.brightness[i] > base:
                self.brightness[i] -= 0.04
                if self.brightness[i] < base:
                    self.brightness[i] = base
            else:
                # лёгкое дыхание
                self.brightness[i] = base + random.uniform(-0.05, 0.05)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # прозрачность при Liquid Glass
        try:
            from modules import settings as _s
            _settings = _s.load()
            if _settings.get("liquid_glass", False):
                opacity = 0.5 + 0.3 * (_settings.get("liquid_opacity", 70) / 100)
            else:
                opacity = 1.0
        except Exception:
            opacity = 1.0

        painter.setOpacity(opacity)

        w = self.width()
        h = self.height()
        
        # спец-режим (для Doomsday — огонь)
        special = self.style.get("special")

        # ==== ПРОВОД (только для гирлянды) ====
        if special != "fire":
            painter.setPen(QPen(QColor(80, 80, 80), 2))
            painter.drawLine(0, int(h - 10), w, int(h - 10))

        # ==== ГИРЛЯНДА (или огонь для Doomsday) ====
        special = self.style.get("special")

        if special == "fire":
            # огненные вспышки вместо лампочек
            for i in range(self.count):
                x = (w / (self.count + 1)) * (i + 1)
                brightness = self.brightness[i]

                # красный + оранжевый огонь
                r = int(255 * (0.5 + 0.5 * brightness))
                g = int(80 * brightness)
                b = 0

                radius = 4 + 4 * brightness

                # яркое свечение
                glow = QColor(r, g, b, int(120 * brightness))
                painter.setBrush(QBrush(glow))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(x, h - 15), radius + 8, radius + 8)

                # ядро огня
                painter.setBrush(QBrush(QColor(r, g, b)))
                painter.drawEllipse(QPointF(x, h - 15), radius, radius)
        else:
            # обычная гирлянда
            lights = self.style["lights"]
            spacing = w / (self.count + 1)

            for i in range(self.count):
                x = spacing * (i + 1)
                brightness = self.brightness[i]
                color_hex = lights[i % len(lights)]
                color = QColor(color_hex)

                r = int(color.red() * (0.4 + 0.6 * brightness))
                g = int(color.green() * (0.4 + 0.6 * brightness))
                b = int(color.blue() * (0.4 + 0.6 * brightness))

                radius = 4 + 3 * brightness

                if self.style.get("glow"):
                    glow_color = QColor(r, g, b, int(100 * brightness))
                    painter.setBrush(QBrush(glow_color))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(QPointF(x, h - 10), radius + 5, radius + 5)

                painter.setBrush(QBrush(QColor(r, g, b)))
                painter.setPen(QPen(QColor(r, g, b), 1))
                painter.drawEllipse(QPointF(x, h - 10), radius, radius)

        # ==== УГЛОВЫЕ ЭМОДЗИ ====
        corners = self.style.get("corners", [])
        if corners:
            font = QFont("Segoe UI Emoji", 22)
            painter.setFont(font)

            if len(corners) > 0:
                painter.drawText(
                    QRectF(0, h - 30, 40, 40),
                    Qt.AlignmentFlag.AlignCenter,
                    corners[0],
                )
            if len(corners) > 1:
                painter.drawText(
                    QRectF(w - 40, h - 30, 40, 40),
                    Qt.AlignmentFlag.AlignCenter,
                    corners[1],
                )

        painter.setOpacity(1.0)
        painter.end()

    def stop(self):
        """Останавливает анимацию."""
        if self._timer:
            self._timer.stop()
        if self._flash_timer:
            self._flash_timer.stop()