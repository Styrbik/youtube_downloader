"""
Иней по краям окна — для темы Frostmourne.
"""

import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont


class FrostFX(QWidget):
    """Иней — мелкие снежинки по краям окна."""

    def __init__(self, parent, count=40):
        super().__init__(parent)
        self.count = count

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.snowflakes = []
        self._spawn()

        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _spawn(self):
        """Создаёт снежинки по краям."""
        w = max(self.width(), 400)
        h = max(self.height(), 600)

        for _ in range(self.count):
            # 70% по краям, 30% по всему полю
            if random.random() < 0.7:
                # край: сверху, снизу, слева или справа
                side = random.choice(["top", "bottom", "left", "right"])
                if side == "top":
                    x = random.randint(0, w)
                    y = random.randint(0, 60)
                elif side == "bottom":
                    x = random.randint(0, w)
                    y = random.randint(h - 60, h)
                elif side == "left":
                    x = random.randint(0, 60)
                    y = random.randint(0, h)
                else:
                    x = random.randint(w - 60, w)
                    y = random.randint(0, h)
            else:
                x = random.randint(0, w)
                y = random.randint(0, h)

            size = random.randint(10, 18)
            alpha = random.randint(80, 180)
            drift = random.uniform(-0.3, 0.3)

            self.snowflakes.append({
                "x": x,
                "y": y,
                "size": size,
                "alpha": alpha,
                "drift": drift,
                "phase": random.uniform(0, 6.28),
            })

    def _tick(self):
        """Двигает снежинки + пульсирует прозрачность."""
        for s in self.snowflakes:
            s["phase"] += 0.05
            s["x"] += s["drift"]

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # прозрачность при Liquid Glass
        try:
            from modules import settings as _s
            _settings = _s.load()
            if _settings.get("liquid_glass", False):
                opacity = 0.4 + 0.3 * (_settings.get("liquid_opacity", 70) / 100)
            else:
                opacity = 0.8
        except Exception:
            opacity = 0.8

        w = self.width()
        h = self.height()

        for s in self.snowflakes:
            import math
            pulse = 0.5 + 0.5 * math.sin(s["phase"])
            alpha = int(s["alpha"] * pulse * opacity)

            font = QFont("Segoe UI Emoji", s["size"])
            painter.setFont(font)
            painter.setPen(QColor(180, 230, 255, alpha))

            # рисуем эмодзи-снежинку
            rect = QRectF(s["x"] - s["size"], s["y"] - s["size"],
                          s["size"] * 2, s["size"] * 2)
            painter.drawText(
                rect,
                Qt.AlignmentFlag.AlignCenter,
                "❄️",
            )

        # ==== МЕЧ В УГЛУ ====
        font = QFont("Segoe UI Emoji", 36)
        painter.setFont(font)
        painter.setPen(QColor(120, 200, 255, int(180 * opacity)))
        painter.drawText(
            QRectF(w - 80, h - 80, 70, 70),
            Qt.AlignmentFlag.AlignCenter,
            "⚔️",
        )

        painter.end()

    def stop(self):
        if self._timer:
            self._timer.stop()