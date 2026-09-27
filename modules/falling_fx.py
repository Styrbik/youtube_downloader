"""
Падающие объекты для праздничных тем.
Рисует на Canvas и анимирует.
"""

import random
import tkinter as tk


# Эмодзи для каждого праздника
HOLIDAY_EMOJI = {
    "halloween": ["🎃", "👻", "🦇", "💀", "🕷"],
    "doomsday":  ["💀", "☄️", "🔥", "⚡"],
    "newyear":   ["❄️", "🎄", "⭐", "🎁", "🔔"],
    "march8":    ["🌸", "🌷", "💐", "❤️", "💖"],
}


class FallingFX:
    """Падающие объекты на Canvas."""
    def __init__(self, canvas, theme_name, count=12, speed=1.5):
        self.canvas = canvas
        self.theme_name = theme_name
        self.count = count
        self.speed = speed
        self.items = []  # [(id, x, y, vy, emoji)]
        self.running = True
        self._anim_id = None

        self.emoji_list = HOLIDAY_EMOJI.get(theme_name, ["✨"])
        self._spawn_all()
        self._start()

    def _spawn_all(self):
        """Создаёт все объекты."""
        self.canvas.update_idletasks()
        w = self.canvas.winfo_width() or 400
        h = self.canvas.winfo_height() or 600

        for _ in range(self.count):
            self._spawn_one(w, h, initial=True)

    def _spawn_one(self, w, h, initial=False):
        """Создаёт один объект."""
        emoji = random.choice(self.emoji_list)
        x = random.randint(10, max(20, w - 10))
        y = random.randint(-h, 0) if not initial else random.randint(0, h)
        size = random.randint(14, 22)
        vy = random.uniform(0.5, 2.0) * self.speed

        try:
            item_id = self.canvas.create_text(
                x, y, text=emoji, font=("Segoe UI Emoji", size),
                fill="#ffffff",
            )
        except Exception:
            item_id = self.canvas.create_text(
                x, y, text="*", font=("Segoe UI", size),
                fill="#ffffff",
            )

        self.items.append([item_id, x, y, vy, emoji])

    def _start(self):
        self._tick()

    def _tick(self):
        if not self.running:
            return
        try:
            h = self.canvas.winfo_height() or 600
            w = self.canvas.winfo_width() or 400

            for item in self.items:
                item_id, x, y, vy, emoji = item
                y += vy
                if y > h + 30:
                    # перерождаем сверху
                    x = random.randint(10, max(20, w - 10))
                    y = random.randint(-80, -10)
                    item[1] = x
                    item[2] = y
                else:
                    item[2] = y
                try:
                    self.canvas.coords(item_id, item[1], item[2])
                except Exception:
                    pass

            self._anim_id = self.canvas.after(50, self._tick)
        except Exception:
            pass

    def stop(self):
        """Останавливает анимацию."""
        self.running = False
        if self._anim_id:
            try:
                self.canvas.after_cancel(self._anim_id)
            except Exception:
                pass
            self._anim_id = None