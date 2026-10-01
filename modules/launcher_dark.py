"""
Лаунчер на Tkinter — выбор версии (Classic / Modern).
С fade-out анимацией при переключении на Qt-лаунчер.
"""

import sys
import os
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import set_preferred_gui, get_active_icon_path, APP_VERSION


# Цвета (Classic — как в Tkinter-версии приложения)
BG = "#1e1e1e"
BG_CARD = "#2a2a2a"
FG = "#e0e0e0"
FG_DIM = "#888888"
ACCENT = "#e62117"
ACCENT_HOVER = "#ff3b30"
BORDER = "#3a3a3a"


class ChoiceCard(tk.Frame):
    """Карточка выбора версии (Tkinter)."""

    def __init__(self, parent, title, subtitle, description,
                 is_recommended=False, launcher=None):
        # Внешняя рамка для бордера
        super().__init__(parent, bg=BORDER, bd=0, highlightthickness=0)
        self.launcher = launcher
        self.is_selected = False
        self.is_recommended = is_recommended

        # Внутренний фрейм
        self.inner = tk.Frame(self, bg=BG_CARD)
        self.inner.pack(fill="both", expand=True, padx=2, pady=2)

        # Заголовок + бейдж
        title_row = tk.Frame(self.inner, bg=BG_CARD)
        title_row.pack(fill="x", padx=16, pady=(12, 4))

        tk.Label(
            title_row, text=title, bg=BG_CARD, fg=FG,
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left")

        if is_recommended:
            badge = tk.Label(
                title_row, text="Рекомендуется", bg=ACCENT, fg="white",
                font=("Segoe UI", 8, "bold"), padx=6, pady=2,
            )
            badge.pack(side="left", padx=(8, 0))

        # Подзаголовок
        tk.Label(
            self.inner, text=subtitle, bg=BG_CARD, fg=ACCENT,
            font=("Segoe UI", 10, "bold"), anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 4))

        # Описание
        tk.Label(
            self.inner, text=description, bg=BG_CARD, fg=FG_DIM,
            font=("Segoe UI", 9), justify="left", anchor="w",
            wraplength=440,
        ).pack(fill="x", padx=16, pady=(0, 12))

        # Привязка кликов ко всем элементам
        for w in (self, self.inner, title_row):
            w.bind("<Button-1>", self._on_click)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

        for child in self.inner.winfo_children():
            child.bind("<Button-1>", self._on_click)
            child.bind("<Enter>", self._on_enter)
            child.bind("<Leave>", self._on_leave)
            for sub in child.winfo_children():
                sub.bind("<Button-1>", self._on_click)
                sub.bind("<Enter>", self._on_enter)
                sub.bind("<Leave>", self._on_leave)

    def _on_click(self, event=None):
        if self.launcher:
            self.launcher._on_card_clicked(self)

    def _on_enter(self, event=None):
        if not self.is_selected:
            self.config(bg=ACCENT)

    def _on_leave(self, event=None):
        if not self.is_selected:
            self.config(bg=BORDER)

    def set_selected(self, selected):
        self.is_selected = selected
        if selected:
            self.config(bg=ACCENT)
        else:
            self.config(bg=BORDER)


class LauncherWindow:
    def __init__(self, root, chosen=None):
        self.root = root
        self.selected = chosen or "tkinter"
        self._closing = False

        self.root.title("YouTube Downloader — Выбор версии")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        # Размер и центрирование
        w, h = 560, 520
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        # Иконка
        try:
            icon_path = get_active_icon_path()
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        self._build_ui()

        # Fade-in при старте
        self.root.attributes("-alpha", 0.0)
        self._fade_in()

    def _build_ui(self):
        # Заголовок
        tk.Label(
            self.root, text="YouTube Downloader", bg=BG, fg=FG,
            font=("Segoe UI", 20, "bold"),
        ).pack(pady=(30, 4))

        tk.Label(
            self.root, text=f"v{APP_VERSION} — выбери версию",
            bg=BG, fg=FG_DIM, font=("Segoe UI", 10),
        ).pack(pady=(0, 16))

        # Карточки
        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=30, pady=(0, 16))

        self.card_qt = ChoiceCard(
            container,
            title="🎨 Modern",
            subtitle="PyQt6 — активно развивается",
            description=("Современный интерфейс, плавные анимации, тени, "
                         "праздничные темы с падающими объектами. "
                         "Все новые функции — здесь."),
            is_recommended=True,
            launcher=self,
        )
        self.card_qt.pack(fill="x", pady=(0, 10))

        self.card_tk = ChoiceCard(
            container,
            title="🌙 Classic",
            subtitle="Tkinter — архивная версия",
            description=("Проверенный временем интерфейс. Всё, что нужно для скачивания. "
                         "Больше не обновляется — только стабильность. "
                         "Финальная версия v0.4.2."),
            is_recommended=False,
            launcher=self,
        )
        self.card_tk.pack(fill="x")

        # Чекбокс "Запомнить"
        self.remember_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            self.root, text="Запомнить выбор (не спрашивать в следующий раз)",
            variable=self.remember_var,
            bg=BG, fg=FG, selectcolor=BG_CARD,
            activebackground=BG, activeforeground=ACCENT,
            font=("Segoe UI", 10), bd=0, highlightthickness=0,
        ).pack(anchor="w", padx=30, pady=(0, 16))

        # Кнопка "Вперёд"
        btn_row = tk.Frame(self.root, bg=BG)
        btn_row.pack(fill="x", padx=30, pady=(0, 30))

        self.btn_forward = tk.Label(
            btn_row, text="Вперёд →", bg=ACCENT, fg="white",
            font=("Segoe UI", 12, "bold"), padx=30, pady=12,
            cursor="hand2",
        )
        self.btn_forward.pack(side="right")

        self.btn_forward.bind("<Enter>", lambda e: self.btn_forward.config(bg=ACCENT_HOVER))
        self.btn_forward.bind("<Leave>", lambda e: self.btn_forward.config(bg=ACCENT))
        self.btn_forward.bind("<Button-1>", lambda e: self._on_forward())

        # Изначально выбран Classic
        self._select(self.card_tk)

    def _on_card_clicked(self, card):
        """Клик по карточке."""
        if card is self.card_tk:
            # Classic — просто выделяем
            self._select(self.card_tk)
        else:
            # Modern — выделяем, fade-out, запуск Qt-лаунчера
            self._select(self.card_qt)
            self.root.after(200, self._switch_to_qt)

    def _select(self, card):
        self.card_qt.set_selected(card is self.card_qt)
        self.card_tk.set_selected(card is self.card_tk)
        self.selected = "tkinter" if card is self.card_tk else "qt"

    def _fade_in(self, step=0.0):
        step += 0.1
        if step >= 1.0:
            self.root.attributes("-alpha", 1.0)
            return
        try:
            self.root.attributes("-alpha", step)
        except Exception:
            pass
        self.root.after(20, lambda: self._fade_in(step))

    def _fade_out(self, on_done=None, step=1.0):
        step -= 0.1
        if step <= 0.0:
            try:
                self.root.attributes("-alpha", 0.0)
            except Exception:
                pass
            if on_done:
                on_done()
            return
        try:
            self.root.attributes("-alpha", step)
        except Exception:
            pass
        self.root.after(20, lambda: self._fade_out(on_done, step))

    def _switch_to_qt(self):
        if self._closing:
            return
        self._closing = True

        def _launch():
            self.root.destroy()
            from modules import launcher_qt
            launcher_qt.run()

        self._fade_out(_launch)

    def _on_forward(self):
        if self.remember_var.get():
            set_preferred_gui(self.selected)

        selected = self.selected

        def _launch():
            self.root.destroy()
            if selected == "tkinter":
                from modules import gui_dark
                gui_dark.run()
            else:
                from modules import gui_qt
                gui_qt.run()

        self._fade_out(_launch)


def run(chosen=None):
    root = tk.Tk()
    LauncherWindow(root, chosen=chosen)
    root.mainloop()


if __name__ == "__main__":
    # парсим --chosen из аргументов
    chosen = None
    for arg in sys.argv:
        if arg.startswith("--chosen="):
            chosen = arg.split("=", 1)[1]
    run(chosen)