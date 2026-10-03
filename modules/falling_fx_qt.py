"""
Падающие объекты для праздничных тем — PyQt6 edition.
Аналог modules/falling_fx.py, но на QPainter + QTimer.

Использование:
    fx = FallingFXQt(parent_widget, "halloween", count=12, speed=1.5)
    fx.setGeometry(parent_widget.rect())
    fx.show()
    # потом при закрытии:
    fx.stop()
"""

import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QFont


# Эмодзи для каждого праздника — те же, что в Tkinter-версии
HOLIDAY_EMOJI = {
    "halloween": ["🎃", "👻", "🦇", "💀", "🕷"],
    "doomsday":  ["💀", "☄️", "🔥", "⚡"],
    "newyear":   ["❄️", "🎄", "⭐", "🎁", "🔔"],
    "march8":    ["🌸", "🌷", "💐", "❤️", "💖"],
    "september1": ["🎒", "📚", "✏️", "🔔", "🍎"],
    "feb14":      ["❤️", "💕", "💖", "🌹", "💘"],
    "april12":    ["🚀", "🛸", "👨‍🚀", "⭐", "🌍"],
    "may1":       ["🌸", "🎈", "🌷", "🌹", "🎉"],
    "frostmourne": ["❄️", "💀", "⚔️", "🔷"],
    }


class FallingObject:
    """Один падающий объект."""
    def __init__(self, x, y, emoji, size, vy):
        self.x = x
        self.y = y
        self.emoji = emoji
        self.size = size
        self.vy = vy  # скорость по вертикали (пикселей за тик)


class FallingFXQt(QWidget):
    """
    Прозрачный виджет поверх родителя. Рисует падающие эмодзи.
    Не перехватывает клики — можно спокойно работать с UI под ним.
    """
    def __init__(self, parent, theme_name, count=12, speed=1.5):
        super().__init__(parent)
        self.theme_name = theme_name
        self.count = count
        self.speed = speed

        # Прозрачный фон, не перехватывает клики
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        self.emoji_list = HOLIDAY_EMOJI.get(theme_name, ["✨"])
        self.objects = []
        self.running = True

        # Заполняем объекты (первый раз — раскидываем по всей высоте)
        self._spawn_all()

        # Таймер ~20 FPS (как 50 мс в Tkinter)
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _spawn_all(self):
        """Создаёт все объекты. Первый раз — по всей высоте."""
        w = max(self.width(), 400)
        h = max(self.height(), 600)

        for _ in range(self.count):
            emoji = random.choice(self.emoji_list)
            x = random.randint(10, max(20, w - 10))
            y = random.randint(0, h)  # сразу по всей высоте
            size = random.randint(14, 22)
            vy = random.uniform(0.5, 2.0) * self.speed
            self.objects.append(FallingObject(x, y, emoji, size, vy))

    def _tick(self):
        if not self.running:
            return

        h = self.height() or 600
        w = self.width() or 400

        for obj in self.objects:
            obj.y += obj.vy
            # если упал ниже — перерождаем сверху
            if obj.y > h + 30:
                obj.x = random.randint(10, max(20, w - 10))
                obj.y = random.randint(-80, -10)

        self.update()  # вызвать paintEvent

    def paintEvent(self, event):
        if not self.objects:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # прозрачность эмодзи (если Liquid Glass включён)
        try:
            from modules import settings as _s
            _settings = _s.load()
            if _settings.get("liquid_glass", False):
                opacity = 0.4 + 0.3 * (_settings.get("liquid_opacity", 70) / 100)
            else:
                opacity = 1.0
        except Exception:
            opacity = 1.0

        painter.setOpacity(opacity)

        for obj in self.objects:
            font = QFont("Segoe UI Emoji", obj.size)
            painter.setFont(font)

            rect = QRectF(obj.x - obj.size, obj.y - obj.size,
                          obj.size * 2, obj.size * 2)
            painter.drawText(
                rect,
                Qt.AlignmentFlag.AlignCenter,
                obj.emoji,
            )

        painter.setOpacity(1.0)
        painter.end()

    def resizeEvent(self, event):
        """При ресайзе — раскидываем объекты по новой ширине."""
        w = self.width()
        for obj in self.objects:
            if obj.x > w:
                obj.x = random.randint(10, max(20, w - 10))
        super().resizeEvent(event)

    def stop(self):
        """Останавливает анимацию."""
        self.running = False
        if self._timer:
            self._timer.stop()