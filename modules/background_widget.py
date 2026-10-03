"""
BackgroundWidget — фон с гирляндой и падающими эмодзи.
Рисует всё в paintEvent — карточки автоматически сверху.
"""

import random
import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QFont, QBrush, QPen


# Эмодзи для каждого праздника
HOLIDAY_EMOJI = {
    "halloween": ["🎃", "👻", "🦇", "💀", "🕷"],
    "doomsday":  ["💀", "☄️", "🔥", "⚡"],
    "newyear":   ["❄️", "🎄", "⭐", "🎁", "🔔"],
    "march8":    ["🌸", "🌷", "💐", "❤️", "💖"],
    "september1": ["🎒", "📚", "✏️", "🔔", "🍎"],
    "feb14":      ["❤️", "💕", "💖", "🌹", "💘"],
    "april12":    ["🚀", "🛸", "👨‍🚀", "⭐", "🌍"],
    "may1":       ["🌸", "🎈", "🌷", "🌹", "🎉"],
}

# Гирлянда для каждого праздника
HOLIDAY_LIGHTS = {
    "newyear":   ["#ff0000", "#00ff00", "#0066ff", "#ffff00", "#ff00ff"],
    "halloween": ["#ff8800", "#ff6600", "#ffaa00", "#cc5500"],
    "feb14":     ["#ff2d6f", "#ff6699", "#ff0044"],
    "march8":    ["#ff66b3", "#ff99cc", "#ff3388"],
    "april12":   ["#4d8cff", "#77aaff", "#2a66cc"],
    "doomsday":  ["#ff0000", "#aa0000", "#ff4444"],
    "september1": ["#ff8c00", "#ffaa33", "#cc5500"],
    "may1":      ["#4dd94d", "#77ff77", "#2aaa2a"],
}

# Угловые эмодзи
HOLIDAY_CORNERS = {
    "newyear":   ["🎄", "🎁"],
    "halloween": ["🎃", "👻"],
    "feb14":     ["❤️", "💕"],
    "march8":    ["🌸", "🌷"],
    "april12":   ["🚀", "⭐"],
    "doomsday":  ["💀", "☠️"],
    "september1": ["🎒", "📚"],
    "may1":      ["🎈", "🌷"],
}


class FallingObject:
    """Один падающий эмодзи."""
    def __init__(self, x, y, emoji, size, vy):
        self.x = x
        self.y = y
        self.emoji = emoji
        self.size = size
        self.vy = vy


class BackgroundWidget(QWidget):
    """Фон с гирляндой и падающими эмодзи."""

    def __init__(self, parent=None, bg_color="#1e1e1e"):
        super().__init__(parent)
        self.bg_color = bg_color
        self.holiday_theme = None
        self.falling_objects = []
        self._falling_count = 12
        self._falling_speed = 1.5

        # гирлянда
        self._light_count = 25
        self._lights_brightness = []
        self._flash_timer = None

        # таймер
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        # вспышки гирлянды
        self._flash_timer = QTimer(self)
        self._flash_timer.setInterval(300)
        self._flash_timer.timeout.connect(self._random_flash)
        self._flash_timer.start()

    def set_bg_color(self, color):
        """Устанавливает цвет фона."""
        self.bg_color = color
        self.update()

    def set_holiday(self, theme_name):
        """Устанавливает праздник — запускает гирлянду и падающие."""
        self.holiday_theme = theme_name
        self.falling_objects = []
        self._lights_brightness = []

        if not theme_name:
            self.update()
            return

        # создаём падающие объекты
        emoji_list = HOLIDAY_EMOJI.get(theme_name, ["✨"])
        w = max(self.width(), 400)
        h = max(self.height(), 600)
        for _ in range(self._falling_count):
            emoji = random.choice(emoji_list)
            x = random.randint(10, max(20, w - 10))
            y = random.randint(0, h)
            size = random.randint(14, 22)
            vy = random.uniform(0.5, 2.0) * self._falling_speed
            self.falling_objects.append(FallingObject(x, y, emoji, size, vy))

        # гирлянда
        self._lights_brightness = [random.uniform(0.6, 0.9) for _ in range(self._light_count)]

        self.update()

    def _random_flash(self):
        """Случайная лампочка вспыхивает."""
        if not self._lights_brightness:
            return
        idx = random.randint(0, len(self._lights_brightness) - 1)
        self._lights_brightness[idx] = 1.0

    def _tick(self):
        """Обновляет падающие и гирлянду."""
        h = self.height() or 600
        w = self.width() or 400

        # падающие
        for obj in self.falling_objects:
            obj.y += obj.vy
            if obj.y > h + 30:
                obj.x = random.randint(10, max(20, w - 10))
                obj.y = random.randint(-80, -10)

        # гирлянда — затухание
        for i in range(len(self._lights_brightness)):
            base = 0.55
            if self._lights_brightness[i] > base:
                self._lights_brightness[i] -= 0.04
                if self._lights_brightness[i] < base:
                    self._lights_brightness[i] = base
            else:
                self._lights_brightness[i] = base + random.uniform(-0.05, 0.05)

        self.update()

    def paintEvent(self, event):
        """Рисует только фон."""
        painter = QPainter(self)
        painter.fillRect(0, 0, self.width(), self.height(), QColor(self.bg_color))
        painter.end()