import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys
import re
import yt_dlp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import core, settings, visual, embed, icon_manager
from modules.icons import icon_photo, load_thumbnail
from modules.sounds import (
    click, radio, fetch, download_start, done, error,
    warning, folder_pick, file_saved, startup, shutdown, list_click
)
from modules.toast import show_toast, open_file, open_folder
from modules.themes import THEMES, get_theme
from modules.splash import show_splash
from config import (DOWNLOADS_DIR, ICON_PATH, CHANGELOG_PATH,
                    COVER_PATH, get_centered_geometry,
                    APP_VERSION, APP_BUILD_NAME)

APP_TITLE = f"YouTube Downloader v{APP_VERSION}"
ANIMATIONS_ENABLED = True

# Глобальные цвета
BG = "#1e1e1e"
BG_CARD = "#2a2a2a"
BG_INPUT = "#333333"
FG = "#e0e0e0"
FG_DIM = "#888888"
ACCENT = "#e62117"
ACCENT_HOVER = "#ff3b30"
ACCENT_PRESS = "#b71c1c"
BORDER = "#3a3a3a"
BORDER_HOVER = "#e62117"
DISABLED = "#3a3a3a"
DISABLED_FG = "#666"
TITLEBAR_BG = "#151515"
TITLEBAR_HOVER = "#2a2a2a"
TITLEBAR_CLOSE = "#c0392b"


def _apply_theme_vars(theme_name):
    global BG, BG_CARD, BG_INPUT, FG, FG_DIM, ACCENT, ACCENT_HOVER
    global ACCENT_PRESS, BORDER, BORDER_HOVER, DISABLED, DISABLED_FG
    global TITLEBAR_BG, TITLEBAR_HOVER, TITLEBAR_CLOSE
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
    BORDER_HOVER = t["BORDER_HOVER"]
    DISABLED = t["DISABLED"]
    DISABLED_FG = t["DISABLED_FG"]

    def _darker(hex_color, factor=0.7):
        h = hex_color.lstrip("#")
        r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
        return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"

    TITLEBAR_BG = _darker(BG, 0.7)
    TITLEBAR_HOVER = _darker(BG_CARD, 1.0)


def ease_out_cubic(t):
    return 1 - pow(1 - t, 3)


def _hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


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
    
def _fmt_speed(bps):
    """Форматирует скорость: 1234567 -> '1.2 MB/s'"""
    if not bps:
        return "—"
    if bps >= 1024 * 1024:
        return f"{bps/(1024*1024):.1f} MB/s"
    if bps >= 1024:
        return f"{bps/1024:.0f} KB/s"
    return f"{bps:.0f} B/s"


def _fmt_eta(seconds):
    """Форматирует ETA: 3725 -> '1:02:05'"""
    if seconds is None or seconds < 0:
        return "—"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _sanitize_geom(geom, default="780x920+100+100"):
    try:
        size = geom.split("+")[0]
        w, h = map(int, size.split("x"))
        if w < 400 or h < 400:
            return default
        return geom
    except Exception:
        return default


class HoverButton(tk.Label):

    def __init__(self, parent, text, command, bg=None, fg="white",
                 hover_bg=None, font=("Segoe UI", 10, "bold"),
                 padx=20, pady=8, icon=None, **kwargs):
        bg = bg or ACCENT
        hover_bg = hover_bg or ACCENT_HOVER
        super().__init__(parent, text=text, bg=bg, fg=fg, font=font,
                         padx=padx, pady=pady, cursor="hand2",
                         compound="left", **kwargs)
        self.default_bg = bg
        self.hover_bg = hover_bg
        self.command = command
        self.enabled = True
        self._icon_photo = None
        if icon:
            try:
                self._icon_photo = icon_photo(icon, 16, "#ffffff")
                self.config(image=self._icon_photo)
            except Exception:
                pass
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, e):
        if self.enabled:
            self.config(bg=self.hover_bg)

    def _on_leave(self, e):
        if self.enabled:
            self.config(bg=self.default_bg)

    def _on_press(self, e):
        if self.enabled:
            self.config(bg=ACCENT_PRESS)

    def _on_release(self, e):
        if not self.enabled:
            return
        self.config(bg=self.hover_bg)
        try:
            click()
        except Exception:
            pass
        if self.command:
            self.command()

    def set_enabled(self, enabled):
        self.enabled = enabled
        if enabled:
            self.config(bg=self.default_bg, fg="white", cursor="hand2")
        else:
            self.config(bg=DISABLED, fg=DISABLED_FG, cursor="arrow")
           
class QualityButton(tk.Label):
    """Кнопка качества с плавной анимацией цвета."""
    def __init__(self, parent, text, value, group, **kwargs):
        super().__init__(parent, text=text, bg=BG_CARD, fg=FG,
                         font=("Consolas", 8, "bold"),
                         padx=6, pady=3, cursor="hand2", **kwargs)
        self.value = value
        self.group = group
        self.selected = False
        self._anim_id = None
        self._current_color = BG_CARD
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_click(self, e):
        self.group.select(self.value)
        try:
            list_click()
        except Exception:
            pass

    def _on_enter(self, e):
        if not self.selected:
            self.config(bg=BORDER)

    def _on_leave(self, e):
        if not self.selected:
            self.config(bg=BG_CARD)

    def set_selected(self, selected):
        self.selected = selected
        target = ACCENT if selected else BG_CARD
        fg_target = "white" if selected else FG
        self._animate_to(target, fg_target)

    def _animate_to(self, target_bg, target_fg, steps=8):
        if self._anim_id:
            self.after_cancel(self._anim_id)

        def parse(c):
            h = c.lstrip("#")
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        start_bg = parse(self._current_color)
        end_bg = parse(target_bg)
        step = [0]

        def tick():
            step[0] += 1
            t = step[0] / steps
            if t > 1:
                t = 1
            r = int(start_bg[0] + (end_bg[0] - start_bg[0]) * t)
            g = int(start_bg[1] + (end_bg[1] - start_bg[1]) * t)
            b = int(start_bg[2] + (end_bg[2] - start_bg[2]) * t)
            color = f"#{r:02x}{g:02x}{b:02x}"
            self.config(bg=color, fg=target_fg)
            self._current_color = color
            if t < 1:
                self._anim_id = self.after(16, tick)
            else:
                self._anim_id = None

        tick()


class QualityGroup:
    """Группа кнопок качества. Одна активная. Многострочная раскладка."""
    def __init__(self, parent_frame, on_change=None, columns=6):
        self.parent = parent_frame
        self.on_change = on_change
        self.columns = columns
        self.buttons = {}
        self.selected = None
        self._order = []
        self.row_frame = None

    def set_items(self, items):
        for btn in self.buttons.values():
            btn.destroy()
        self.buttons.clear()
        self._order.clear()
        self.selected = None

        for label, value in items:
            idx = len(self._order)
            row = idx // self.columns
            col = idx % self.columns
            btn = QualityButton(self.parent, label, value, self)
            btn.grid(row=row, column=col, padx=(0, 4), pady=2, sticky="w")
            self.buttons[value] = btn
            self._order.append(value)

        if items:
            self.select(items[0][1], silent=True)

    def select(self, value, silent=False):
        if value not in self.buttons:
            return
        for v, btn in self.buttons.items():
            btn.set_selected(False)
        self.buttons[value].set_selected(True)
        self.selected = value
        if self.on_change and not silent:
            self.on_change(value)

    def get_selected(self):
        return self.selected

    def clear(self):
        self.set_items([])


class HoverCard(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BORDER, **kwargs)
        self.inner = tk.Frame(self, bg=BG_CARD)
        self.inner.pack(fill="x", padx=1, pady=1)
        self._bind_hover(self)
        self._bind_hover(self.inner)

    def _bind_hover(self, widget):
        widget.bind("<Enter>", lambda e: self.config(bg=BORDER_HOVER))
        widget.bind("<Leave>", lambda e: self.config(bg=BORDER))

    def content(self):
        return self.inner


class AnimatedIndicator:
    def __init__(self, canvas, var, options, fps=60):
        self.canvas = canvas
        self.var = var
        self.options = options
        self.delay = max(1, int(1000 / fps))

        self.indicator = canvas.create_rectangle(0, 0, 0, 4, fill=ACCENT, outline="")
        self.pos = float(options.index(var.get())) if var.get() in options else 0.0
        self.start_pos = self.pos
        self.target = self.pos
        self.progress = 1.0
        self.anim_id = None
        self.ranges = {}
        self.widgets = []

        self.var.trace_add("write", self._on_var_change)
        self.canvas.after(100, self._calc_ranges)
        self.canvas.after(600, self._calc_ranges)
        self.canvas.after(1200, self._calc_ranges)
        self.canvas.bind("<Configure>", lambda e: self._calc_ranges())

    def register(self, widget, value):
        self.widgets.append((widget, value))

    def _calc_ranges(self):
        self.canvas.update_idletasks()
        try:
            base_x = self.canvas.winfo_rootx()
            for w, val in self.widgets:
                w.update_idletasks()
                x1 = w.winfo_rootx() - base_x
                x2 = x1 + w.winfo_width()
                self.ranges[val] = (x1, x2)
        except Exception:
            pass
        self._draw()

    def force_recalc(self):
        self.ranges = {}
        self._calc_ranges()

    def _on_var_change(self, *args):
        val = self.var.get()
        if val in self.options:
            self._animate_to(self.options.index(val))

    def _animate_to(self, target_idx):
        self.target = float(target_idx)
        self.start_pos = self.pos
        self.progress = 0.0
        if self.anim_id:
            self.canvas.after_cancel(self.anim_id)
        self._tick()

    def _tick(self):
        global ANIMATIONS_ENABLED
        if not ANIMATIONS_ENABLED:
            self.pos = self.target
            self._draw()
            self.anim_id = None
            return
        self.progress += 0.12
        if self.progress >= 1.0:
            self.progress = 1.0
            self.pos = self.target
            self._draw()
            self.anim_id = None
            return
        eased = ease_out_cubic(self.progress)
        self.pos = self.start_pos + (self.target - self.start_pos) * eased
        self._draw()
        self.anim_id = self.canvas.after(self.delay, self._tick)

    def _draw(self):
        if not self.ranges:
            return
        idx = int(self.pos)
        frac = self.pos - idx
        keys = self.options
        if idx >= len(keys) - 1:
            a = self.ranges.get(keys[-1], (0, 0))
            b = a
        else:
            a = self.ranges.get(keys[idx], (0, 0))
            b = self.ranges.get(keys[idx + 1], a)
        x1 = a[0] + (b[0] - a[0]) * frac
        x2 = a[1] + (b[1] - a[1]) * frac
        self.canvas.coords(self.indicator, x1, 0, x2, 4)


class GradientBar(tk.Canvas):
    def __init__(self, parent, height=3, **kwargs):
        super().__init__(parent, height=height, highlightthickness=0, bd=0, **kwargs)
        self.bar_height = height
        self.bind("<Configure>", self._redraw)

    def _redraw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        if w < 10:
            return
        c1 = _hex_to_rgb(ACCENT)
        c2 = _hex_to_rgb(BG)
        steps = 100
        for i in range(steps):
            x1 = int(w * i / steps)
            x2 = int(w * (i + 1) / steps)
            t = i / (steps - 1)
            r, g, b = _lerp_color(c1, c2, t)
            self.create_rectangle(x1, 0, x2, self.bar_height,
                                  fill=f"#{r:02x}{g:02x}{b:02x}", outline="")


class TitleBarButton(tk.Label):
    def __init__(self, parent, text, command, hover_bg=TITLEBAR_HOVER,
                 hover_fg=None, **kwargs):
        super().__init__(parent, text=text, bg=TITLEBAR_BG, fg=FG,
                         font=("Segoe UI", 11), padx=14, pady=6,
                         cursor="hand2", **kwargs)
        self.default_bg = TITLEBAR_BG
        self.hover_bg = hover_bg
        self.hover_fg = hover_fg
        self.command = command
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._on_click)

    def _on_enter(self, e):
        self.config(bg=self.hover_bg)
        if self.hover_fg:
            self.config(fg=self.hover_fg)

    def _on_leave(self, e):
        self.config(bg=self.default_bg, fg=FG)

    def _on_click(self, e):
        try:
            click()
        except Exception:
            pass
        self.command()


class DownloaderApp:    
    def _start_falling_fx(self):
        """Запускает падающие объекты на правой колонке."""
        try:
            from modules.falling_fx import FallingFX
            self._falling_fx = FallingFX(
                self._right_canvas,
                self._holiday_theme,
                count=10,
                speed=1.2,
            )
        except Exception as e:
            print(f"⚠️ Не удалось запустить эффекты: {e}")

    def _show_holiday_toast(self):
        """Приветствие в праздничный день."""
        if not self._holiday_mode or not self._holiday_greeting:
            return
        try:
            show_toast(
                self.root,
                self._holiday_greeting,
                duration=7000,
            )
        except Exception:
            pass
    def on_show_player(self):
        """Встроенный плеер."""
        try:
            import pygame
            pygame.mixer.init()
        except Exception as e:
            messagebox.showerror("Плеер", f"Не удалось запустить плеер:\n{e}")
            return

        win = tk.Toplevel(self.root)
        win.title("Плеер")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self.root)

        self.root.update_idletasks()
        w, h = 640, 380
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(win, text="🎵 Плеер", bg=BG, fg=FG,
                 font=("Segoe UI", 14, "bold")).pack(pady=(15, 8))

        list_frame = tk.Frame(win, bg=BG)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                              font=("Consolas", 9), height=8,
                              bg=BG_CARD, fg=FG,
                              selectbackground=ACCENT, selectforeground="white",
                              bd=0, highlightthickness=0, activestyle="none")
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        history = self.settings.get("history", [])
        tracks = []
        for entry in history:
            fp = entry.get("file", "")
            if fp and os.path.exists(fp) and fp.lower().endswith(".mp3"):
                tracks.append(fp)

        for fp in tracks:
            listbox.insert("end", f"  {os.path.basename(fp)}")

        status_var = tk.StringVar(value="Выбери трек")
        tk.Label(win, textvariable=status_var, bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 9)).pack(pady=(0, 5))

        prog_frame = tk.Frame(win, bg=BG)
        prog_frame.pack(fill="x", padx=20, pady=(0, 5))
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Player.Horizontal.TProgressbar",
                        background=ACCENT, troughcolor=BG_CARD,
                        bordercolor=BG_CARD, lightcolor=ACCENT, darkcolor=ACCENT)
        progress = ttk.Progressbar(prog_frame, orient="horizontal",
                                    mode="determinate", maximum=100,
                                    style="Player.Horizontal.TProgressbar")
        progress.pack(fill="x")

        btn_row = tk.Frame(win, bg=BG)
        btn_row.pack(fill="x", padx=20, pady=(5, 15))

        state = {"current": None, "paused": False, "update_id": None}

        def _update_progress():
            if not state["current"]:
                return
            try:
                pos = pygame.mixer.music.get_pos()
                if pos < 0:
                    state["update_id"] = win.after(500, _update_progress)
                    return
                try:
                    from mutagen.mp3 import MP3
                    length_ms = int(MP3(state["current"]).info.length * 1000)
                except Exception:
                    length_ms = 1
                if length_ms > 0:
                    pct = min(100, pos / length_ms * 100)
                    progress["value"] = pct
                state["update_id"] = win.after(500, _update_progress)
            except Exception:
                pass

        def play_selected():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            if idx >= len(tracks):
                return
            fp = tracks[idx]
            try:
                pygame.mixer.music.load(fp)
                pygame.mixer.music.play()
                state["current"] = fp
                state["paused"] = False
                status_var.set(f"▶ {os.path.basename(fp)}")
                if state["update_id"]:
                    win.after_cancel(state["update_id"])
                _update_progress()
            except Exception as e:
                status_var.set(f"⚠️ Ошибка: {e}")

        def toggle_pause():
            if not state["current"]:
                return
            if state["paused"]:
                pygame.mixer.music.unpause()
                state["paused"] = False
                status_var.set(f"▶ {os.path.basename(state['current'])}")
            else:
                pygame.mixer.music.pause()
                state["paused"] = True
                status_var.set(f"⏸ {os.path.basename(state['current'])}")

        def stop_play():
            pygame.mixer.music.stop()
            state["current"] = None
            state["paused"] = False
            status_var.set("⏹ Остановлено")
            progress["value"] = 0
            if state["update_id"]:
                win.after_cancel(state["update_id"])
                state["update_id"] = None

        HoverButton(btn_row, "▶ Играть", play_selected,
                    bg=ACCENT, hover_bg=ACCENT_HOVER, fg="white",
                    font=("Segoe UI", 10, "bold"), padx=14, pady=8).pack(side="left", padx=(0, 6))
        HoverButton(btn_row, "⏸ Пауза", toggle_pause,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 10), padx=14, pady=8).pack(side="left", padx=(0, 6))
        HoverButton(btn_row, "⏹ Стоп", stop_play,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 10), padx=14, pady=8).pack(side="left")

        def close_win():
            try:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
            except Exception:
                pass
            if state["update_id"]:
                win.after_cancel(state["update_id"])
            win.destroy()

        HoverButton(btn_row, "Закрыть", close_win,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 10), padx=14, pady=8).pack(side="right")

        win.protocol("WM_DELETE_WINDOW", close_win)
        listbox.bind("<Double-Button-1>", lambda e: play_selected())

    def on_show_history(self):
        win = tk.Toplevel(self.root)
        win.title("История скачанного")
        win.configure(bg=BG)
        
    
    def _get_output_dir(self):
        """
        Возвращает папку для сохранения с учётом автосортировки.
        """
        base = settings.get_output_dir(self.settings)

        if not self.settings.get("auto_sort", False):
            return base

        mode = self.mode_var.get()
        mark = self.mark_var.get()

        if mode == "audio":
            sub = self.settings.get("sort_audio_dir", "Музыка")
        elif not mark:
            # архивный режим — без суффикса
            sub = self.settings.get("sort_archive_dir", "Архив")
        else:
            sub = self.settings.get("sort_video_dir", "Видео")

        full = os.path.join(base, sub)
        try:
            os.makedirs(full, exist_ok=True)
        except Exception as e:
            print(f"⚠️ Не удалось создать папку {full}: {e}")
            return base
        return full
    
    def on_show_profiles(self):
        """Окно управления профилями."""
        win = tk.Toplevel(self.root)
        win.title("Профили")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        self.root.update_idletasks()
        w, h = 500, 460
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(win, text="🎯 Профили", bg=BG, fg=FG,
                 font=("Segoe UI", 14, "bold")).pack(pady=(15, 8))

        tk.Label(win, text="Один клик — все настройки применяются",
                 bg=BG, fg=FG_DIM, font=("Segoe UI", 9, "italic")).pack()

        # --- список профилей ---
        frame = tk.Frame(win, bg=BG)
        frame.pack(fill="both", expand=True, padx=20, pady=(10, 5))

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set,
                              font=("Consolas", 10), height=10,
                              bg=BG_CARD, fg=FG,
                              selectbackground=ACCENT, selectforeground="white",
                              bd=0, highlightthickness=0, activestyle="none")
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        def refresh():
            listbox.delete(0, "end")
            profiles = self.settings.get("profiles", {})
            for name in profiles:
                listbox.insert("end", f"  {name}")

        refresh()

        # --- кнопки ---
        btn_row = tk.Frame(win, bg=BG)
        btn_row.pack(fill="x", padx=20, pady=(5, 5))

        def apply_selected():
            sel = listbox.curselection()
            if not sel:
                return
            profiles = self.settings.get("profiles", {})
            names = list(profiles.keys())
            idx = sel[0]
            if idx >= len(names):
                return
            name = names[idx]
            self._apply_profile(profiles[name])
            self.settings["last_profile"] = name
            settings.save(self.settings)
            show_toast(self.root, f"✅ Профиль «{name}» применён")
            win.destroy()

        def save_current():
            from tkinter import simpledialog
            name = simpledialog.askstring("Имя профиля",
                                           "Название (например, «Музыка 320»):",
                                           parent=win)
            if not name:
                return
            profile_data = {
                "mode": self.mode_var.get(),
                "container": self.container_var.get(),
                "audio_mode": self.audio_mode_var.get(),
                "audio_codec": self.audio_codec_var.get(),
                "mark_settings": self.mark_var.get(),
            }
            settings.save_profile(self.settings, name, profile_data)
            settings.save(self.settings)
            refresh()
            show_toast(self.root, f"✅ Профиль «{name}» сохранён")

        def delete_selected():
            sel = listbox.curselection()
            if not sel:
                return
            profiles = self.settings.get("profiles", {})
            names = list(profiles.keys())
            idx = sel[0]
            if idx >= len(names):
                return
            name = names[idx]
            if not messagebox.askyesno("Удалить профиль",
                                        f"Удалить «{name}»?"):
                return
            settings.delete_profile(self.settings, name)
            settings.save(self.settings)
            refresh()

        HoverButton(btn_row, "✓ Применить", apply_selected,
                    bg=ACCENT, hover_bg=ACCENT_HOVER, fg="white",
                    font=("Segoe UI", 10, "bold"), padx=14, pady=8).pack(side="left", padx=(0, 6))
        HoverButton(btn_row, "💾 Сохранить текущий", save_current,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 10), padx=14, pady=8).pack(side="left", padx=(0, 6))
        HoverButton(btn_row, "🗑 Удалить", delete_selected,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 10), padx=14, pady=8).pack(side="right")

        # --- готовые пресеты ---
        preset_row = tk.Frame(win, bg=BG)
        preset_row.pack(fill="x", padx=20, pady=(10, 15))

        tk.Label(preset_row, text="Быстрые пресеты:",
                 bg=BG, fg=FG_DIM, font=("Segoe UI", 9)).pack(anchor="w")

        presets_inner = tk.Frame(preset_row, bg=BG)
        presets_inner.pack(fill="x", pady=(4, 0))

        PRESETS = {
            "🎵 Музыка 320": {
                "mode": "audio", "audio_codec": "mp3",
                "audio_mode": "320", "mark_settings": True,
            },
            "🎬 Видео 1080": {
                "mode": "video", "container": "mp4",
                "audio_codec": "aac", "audio_mode": "320", "mark_settings": True,
            },
            "📦 Архив": {
                "mode": "video", "container": "mp4",
                "audio_codec": "aac", "audio_mode": "best", "mark_settings": False,
            },
        }

        def make_preset_btn(name, data):
            def cmd():
                self._apply_profile(data)
                show_toast(self.root, f"✅ Пресет «{name}» применён")
                win.destroy()
            return HoverButton(presets_inner, name, cmd,
                               bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                               font=("Segoe UI", 9), padx=10, pady=6)

        for name, data in PRESETS.items():
            make_preset_btn(name, data).pack(side="left", padx=(0, 6))

    def _apply_profile(self, profile_data):
        """Применяет профиль ко всем переменным."""
        self._silent = True

        if "mode" in profile_data:
            self.mode_var.set(profile_data["mode"])
        if "container" in profile_data:
            self.container_var.set(profile_data["container"])
        if "audio_mode" in profile_data:
            self.audio_mode_var.set(profile_data["audio_mode"])
        if "audio_codec" in profile_data:
            self.audio_codec_var.set(profile_data["audio_codec"])
        if "mark_settings" in profile_data:
            self.mark_var.set(profile_data["mark_settings"])

        self._silent = False
        self._on_mode_change()
        self._on_container_change()

    def _get_output_dir(self):
        """Возвращает папку для сохранения с учётом автосортировки."""
        base = settings.get_output_dir(self.settings)

        if not self.settings.get("auto_sort", False):
            return base

        mode = self.mode_var.get()
        mark = self.mark_var.get()

        if mode == "audio":
            sub = self.settings.get("sort_audio_dir", "Музыка")
        elif not mark:
            sub = self.settings.get("sort_archive_dir", "Архив")
        else:
            sub = self.settings.get("sort_video_dir", "Видео")

        full = os.path.join(base, sub)
        try:
            os.makedirs(full, exist_ok=True)
        except Exception as e:
            print(f"⚠️ Не удалось создать папку {full}: {e}")
            return base
        return full

    def on_open_output_dir(self):
        """Открывает папку загрузок в проводнике."""
        try:
            from modules.toast import open_folder
            output_dir = settings.get_output_dir(self.settings)
            open_folder(output_dir)
            try:
                folder_pick()
            except Exception:
                pass
        except Exception as e:
            print(f"⚠️ Не удалось открыть папку: {e}")

    def on_show_icon_manager(self):
        """Окно менеджера иконок."""
        win = tk.Toplevel(self.root)
        win.title("Менеджер иконок")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        self.root.update_idletasks()
        w, h = 700, 480
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(win, text="🎨 Менеджер иконок", bg=BG, fg=FG,
                 font=("Segoe UI", 14, "bold")).pack(pady=(15, 8))

        # ==== Две колонки ====
        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # --- Левая: галерея ---
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(left, text="Доступные иконки", bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

        listbox = tk.Listbox(left, font=("Consolas", 10), height=14,
                              bg=BG_CARD, fg=FG,
                              selectbackground=ACCENT, selectforeground="white",
                              bd=0, highlightthickness=0, activestyle="none")
        listbox.pack(fill="both", expand=True, pady=(4, 0))

        # --- Правая: превью + кнопки ---
        right = tk.Frame(body, bg=BG)
        right.pack(side="right", fill="both", padx=(10, 0))

        tk.Label(right, text="Превью", bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

        preview_label = tk.Label(right, bg=BG_CARD, width=200, height=200)
        preview_label.pack(pady=(4, 10))

        # локальная переменная для photo
        state = {"photo": None, "icons": []}

        def refresh_list():
            listbox.delete(0, "end")
            state["icons"] = icon_manager.list_icons()
            active = icon_manager.get_active_icon_name()
            for name, path in state["icons"]:
                display = name + ("  ✓" if name == active else "")
                listbox.insert("end", display)

        def show_preview(event=None):
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            if idx >= len(state["icons"]):
                return
            name, path = state["icons"][idx]
            try:
                from PIL import Image, ImageTk
                img = Image.open(path).convert("RGBA").resize((180, 180), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                state["photo"] = photo
                preview_label.config(image=photo, text="", width=180, height=180)
            except Exception as e:
                print(f"⚠️ Не удалось показать превью: {e}")

        listbox.bind("<<ListboxSelect>>", show_preview)

        def apply_selected():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            name = state["icons"][idx][0]
            if icon_manager.apply_icon(name):
                self.settings["active_icon"] = name
                settings.save(self.settings)
                show_toast(self.root, f"🎨 Иконка «{name}» применена\nПерезапусти для обновления")
                refresh_list()

        def delete_selected():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            name = state["icons"][idx][0]
            if name == "classic" or name == "dark":
                messagebox.showwarning("Нельзя удалить", "Эта иконка — стандартная.")
                return
            if icon_manager.delete_icon(name):
                refresh_list()

        def create_new():
            """Открывает генератор иконок."""
            from icon_maker_gui import IconMakerApp
            gen_win = tk.Toplevel(win)
            gen_win.title("Создание иконки")
            gen_win.configure(bg=BG)
            gen_win.geometry("720x560")

            # встраиваем генератор
            app = IconMakerApp(gen_win)

            # переопределяем сохранение ICO — сохраняем в icons/ с именем
            def save_to_icons():
                icon = app._make_current_icon()
                # спрашиваем имя
                from tkinter import simpledialog
                name = simpledialog.askstring("Имя иконки", "Название (без .ico):",
                                              parent=gen_win)
                if not name:
                    return
                if icon_manager.save_generated_icon(icon, name):
                    gen_win.destroy()
                    refresh_list()
                    show_toast(self.root, f"✅ Иконка «{name}» добавлена")

            # заменяем кнопку сохранения ICO
            for child in app.root.winfo_children():
                for sub in child.winfo_children():
                    if isinstance(sub, tk.Button) and "ICO" in sub.cget("text"):
                        sub.config(text="💾 В галерею", command=save_to_icons)

        # --- Кнопки ---
        btn_frame = tk.Frame(right, bg=BG)
        btn_frame.pack(fill="x", pady=(0, 5))

        HoverButton(btn_frame, "✓ Применить", apply_selected,
                    bg=ACCENT, hover_bg=ACCENT_HOVER, fg="white",
                    font=("Segoe UI", 9, "bold"), padx=12, pady=6).pack(fill="x", pady=2)
        HoverButton(btn_frame, "➕ Создать", create_new,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 9), padx=12, pady=6).pack(fill="x", pady=2)
        HoverButton(btn_frame, "🗑 Удалить", delete_selected,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 9), padx=12, pady=6).pack(fill="x", pady=2)

        # ==== Нижняя кнопка ====
        bottom = tk.Frame(win, bg=BG)
        bottom.pack(fill="x", padx=20, pady=(0, 12))
        HoverButton(bottom, "Закрыть", win.destroy,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 10), padx=20, pady=8).pack(side="right")

        refresh_list()
    
    def _open_in_browser(self, event=None):
        """Двойной клик по превью — открыть видео в браузере."""
        import webbrowser
        if self.current_url:
            webbrowser.open(self.current_url)
            try:
                click()
            except Exception:
                pass
    
    def _download_cancelled(self):
        self.downloading = False
        self.fetch_btn.set_enabled(True)
        self.refresh_btn.set_enabled(True)
        self._set_download_btn_normal_mode()
        self.set_status("⏹ Отменено")
        try:
            warning()
        except Exception:
            pass
        show_toast(self.root, "⏹ Загрузка отменена", bg="#3a2a10", fg="#ffcc88")
        
    def _set_download_btn_cancel_mode(self):
        """Превращает кнопку «Скачать» в «Отмена»."""
        self.download_btn.set_enabled(True)
        self.download_btn.default_bg = ACCENT_PRESS
        self.download_btn.hover_bg = "#8a1010"
        self.download_btn.config(
            text="⏹ Отмена",
            bg=ACCENT_PRESS,
        )
        self.download_btn.command = self._on_cancel

    def _set_download_btn_normal_mode(self):
        """Возвращает кнопку «Скачать» в обычный вид."""
        self.download_btn.default_bg = ACCENT
        self.download_btn.hover_bg = ACCENT_HOVER
        self.download_btn.config(
            text="Скачать",
            bg=ACCENT,
        )
        self.download_btn.command = self.on_download
    def _on_cancel(self):
        """Отмена текущей загрузки."""
        if not self.downloading:
            return
        try:
            from modules import core
            core.cancel_download()
            self.set_status("⏹ Отмена...")
        except Exception as e:
            print(f"⚠️ Ошибка отмены: {e}")
            
    def __init__(self, root):
        self.root = root
        self.settings = settings.load()

        # 🎃 Праздничные темы (не сохраняются, только визуально)
        from datetime import datetime
        today = datetime.now()
        self._holiday_mode = False
        self._holiday_theme = None
        self._holiday_greeting = None
        self._real_theme = self.settings.get("theme", "dark")

        # определяем праздник
        if today.month == 10 and today.day == 31:
            self._holiday_mode = True
            self._holiday_theme = "halloween"
            self._holiday_greeting = "🎃 С ХЭЛЛОУИНОМ!\nНе забудь про конфеты!"
            print("🎃 Сегодня Хэллоуин!")
        elif today.month == 12 and today.day == 21:
            self._holiday_mode = True
            self._holiday_theme = "doomsday"
            self._holiday_greeting = "💀 21 ДЕКАБРЯ — КОНЕЦ СВЕТА!\nКачай, пока интернет не отключили!"
            print("💀 Сегодня Doomsday!")
        elif today.month == 12 and today.day == 31:
            self._holiday_mode = True
            self._holiday_theme = "newyear"
            self._holiday_greeting = "🎄 С НОВЫМ ГОДОМ!\nПусть качается всё, что хочется!"
            print("🎄 Сегодня Новый год!")
        elif today.month == 3 and today.day == 8:
            self._holiday_mode = True
            self._holiday_theme = "march8"
            self._holiday_greeting = "🌸 С 8 МАРТА!\nСкачай что-нибудь для мамы!"
            print("🌸 Сегодня 8 марта!")

        theme_to_apply = self._holiday_theme if self._holiday_mode else self._real_theme
        _apply_theme_vars(theme_to_apply)

        self.root.title(APP_TITLE)

        saved_geom = self.settings.get("window_geometry", "")
        geom = self._pick_geometry(saved_geom)
        self.root.geometry(geom)
        self.root.minsize(700, 500)
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        if os.path.exists(ICON_PATH):
            try:
                self.root.iconbitmap(ICON_PATH)
            except Exception:
                pass

        if not os.path.exists(COVER_PATH):
            try:
                visual.make_cover()
            except Exception:
                pass

        self.url_var = tk.StringVar()
        self.current_url = ""
        self.mode_var = tk.StringVar(value=self.settings.get("mode", "video"))
        self.status_var = tk.StringVar(value="Готов к работе")
        self.container_var = tk.StringVar(value=self.settings.get("container", "mp4"))
        self.audio_mode_var = tk.StringVar(value=self.settings.get("audio_mode", "best"))
        self.audio_codec_var = tk.StringVar(value=self.settings.get("audio_codec", "aac"))

        self.formats = []
        self.title_text = ""
        self.meta = {}
        self.thumb_photo = None
        self.downloading = False
        self.progress_current = 0.0
        self.progress_target = 0.0
        self.progress_anim_id = None
        self._silent = False
        self._rename_flag = False
        self._last_downloaded_file = None

        self._drag_data = {"x": 0, "y": 0}
        self._is_maximized = False
        self._restore_geom = geom

        self.mode_var.trace_add("write", self._play_radio)
        self.container_var.trace_add("write", self._play_radio)
        self.audio_mode_var.trace_add("write", self._play_radio)
        self.audio_codec_var.trace_add("write", self._play_radio)

        self._setup_window_frame()
        self._build_ui()
        self._on_mode_change()
        self._apply_settings_live()
        # 🎃 падающие объекты для праздничной темы
        if getattr(self, "_holiday_mode", False):
            self._start_falling_fx()
        # проверка обновлений yt-dlp в фоне
        if self.settings.get("auto_update_ytdlp", True):
            threading.Thread(target=self._check_ytdlp_update, daemon=True).start()

        self.root.bind_all("<Control-v>", lambda e: self._paste_from_clipboard())
        self.root.bind_all("<Control-V>", lambda e: self._paste_from_clipboard())
        self.root.bind_all("<Return>", lambda e: self.on_fetch() if not self.downloading else None)
        self.root.bind_all("<Escape>", lambda e: self._on_close())
        self.root.bind_all("<Control-h>", lambda e: self.on_show_history())
        self.root.bind_all("<Control-H>", lambda e: self.on_show_history())
        self.root.bind_all("<Control-t>", lambda e: self.on_change_theme())
        self.root.bind_all("<Control-T>", lambda e: self.on_change_theme())
        self.root.bind_all("<F5>", lambda e: self.on_fetch() if not self.downloading else None)

        self.root.after(500, self._recalc_indicators)
        self.root.after(100, self._force_show)
        self.root.after(300, self._register_in_taskbar)
        if self._holiday_mode:
            self.root.after(1500, self._show_holiday_toast)

    def _pick_geometry(self, saved_geom):
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

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        work_left = 0
        work_top = 0
        work_right = screen_w
        work_bottom = screen_h
        try:
            import ctypes
            from ctypes import wintypes

            SPI_GETWORKAREA = 0x0030

            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", wintypes.LONG),
                    ("top", wintypes.LONG),
                    ("right", wintypes.LONG),
                    ("bottom", wintypes.LONG),
                ]

            rect = RECT()
            if ctypes.windll.user32.SystemParametersInfoW(
                SPI_GETWORKAREA, 0, ctypes.byref(rect), 0
            ):
                work_left = rect.left
                work_top = rect.top
                work_right = rect.right
                work_bottom = rect.bottom
        except Exception:
            pass

        work_w = work_right - work_left
        work_h = work_bottom - work_top

        w = min(w, work_w - 20)
        h = min(h, work_h - 20)

        x = work_left + (work_w - w) // 2
        y = work_bottom - h
        if y < work_top:
            y = work_top

        return f"{w}x{h}+{x}+{y}"
        
    def _check_ytdlp_update(self):
        """Проверяет и обновляет yt-dlp в фоне."""
        try:
            from modules import updater
            updated = updater.check_and_update(silent=True)
            if updated:
                self.root.after(0, lambda: show_toast(
                    self.root,
                    "📦 yt-dlp обновлён!\nПерезапусти приложение для применения",
                    duration=5000,
                ))
        except Exception as e:
            print(f"⚠️ Ошибка проверки обновлений: {e}")

    def _force_show(self):
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after(150, lambda: self.root.attributes("-topmost", False))
        except Exception:
            pass

    def _register_in_taskbar(self):
        try:
            import ctypes
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            self.root.withdraw()
            self.root.after(10, self._show_again)
        except Exception as e:
            print(f"⚠️ Не удалось зарегистрировать в панели задач: {e}")

    def _show_again(self):
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after(100, lambda: self.root.attributes("-topmost", False))
        except Exception:
            pass

    def _setup_window_frame(self):
        self.root.update_idletasks()
        self.root.overrideredirect(True)
        self.root.update_idletasks()

        self.titlebar = tk.Frame(self.root, bg=TITLEBAR_BG, height=34)
        self.titlebar.pack(fill="x", side="top")
        self.titlebar.pack_propagate(False)

        self.tb_left = tk.Frame(self.titlebar, bg=TITLEBAR_BG)
        self.tb_left.pack(side="left", fill="y")
        tk.Label(self.tb_left, text="🎬", bg=TITLEBAR_BG, fg=ACCENT,
                 font=("Segoe UI", 12)).pack(side="left", padx=(10, 4), pady=4)
        tk.Label(self.tb_left, text="YouTube Downloader", bg=TITLEBAR_BG, fg=FG,
                 font=("Segoe UI", 10, "bold")).pack(side="left", pady=4)

        btn_close = TitleBarButton(self.titlebar, "✕", self._on_close,
                                     hover_bg=TITLEBAR_CLOSE, hover_fg="white")
        btn_close.pack(side="right", fill="y")

        btn_max = TitleBarButton(self.titlebar, "▢", self._toggle_maximize)
        btn_max.pack(side="right", fill="y")

        for w in (self.titlebar, self.tb_left):
            w.bind("<ButtonPress-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)
            w.bind("<Double-Button-1>", lambda e: self._toggle_maximize())
        for w in self.tb_left.winfo_children():
            w.bind("<ButtonPress-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)
            w.bind("<Double-Button-1>", lambda e: self._toggle_maximize())

        self.cheek = GradientBar(self.root, height=3, bg=BG)
        self.cheek.pack(fill="x", side="top")

        self.bottom_panel = tk.Frame(self.root, bg=BG)
        self.bottom_panel.pack(side="bottom", fill="x")

        self.content = tk.Frame(self.root, bg=BG)
        self.content.pack(fill="both", expand=True, side="top")

    def _start_drag(self, event):
        self._drag_data["x"] = event.x_root - self.root.winfo_x()
        self._drag_data["y"] = event.y_root - self.root.winfo_y()

    def _on_drag(self, event):
        if self._is_maximized:
            return
        x = event.x_root - self._drag_data["x"]
        y = event.y_root - self._drag_data["y"]
        self.root.geometry(f"+{x}+{y}")

    def _toggle_maximize(self):
        if self._is_maximized:
            self.root.geometry(self._restore_geom)
            self._is_maximized = False
        else:
            # сохраняем нормальный размер, если ещё не развёрнуто
            if not self._is_maximized:
                self._restore_geom = self.root.geometry()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            self.root.geometry(f"{sw}x{sh}+0+0")
            self._is_maximized = True

    def _recalc_indicators(self):
        for ind in (getattr(self, "ind_cont", None),
                    getattr(self, "ind_audio", None),
                    getattr(self, "ind_codec", None),
                    getattr(self, "ind_mode", None)):
            if ind:
                try:
                    ind.force_recalc()
                except Exception:
                    pass

    def _play_radio(self, *args):
        if not self._silent:
            try:
                radio()
            except Exception:
                pass

    def _paste_from_clipboard(self):
        try:
            text = self.root.clipboard_get()
            if text:
                self.url_var.set(text.strip())
                self.url_entry.icursor("end")
        except Exception:
            pass

    def _build_suffix_for_check(self):
        suffix = ""
        if not self.mark_var.get():
            return suffix
        mode = self.mode_var.get()
        if mode == "audio":
            codec_c = self.audio_codec_var.get() if self.audio_codec_var.get() in ("mp3", "m4a") else "mp3"
            am_c = self.audio_mode_var.get()
            br_c = f"-{am_c}" if am_c.isdigit() else ""
            suffix = f"{codec_c}{br_c}"
        else:
            cont_c = self.container_var.get()
            am_c = self.audio_mode_var.get()
            codec_c = self.audio_codec_var.get()
            parts_c = [cont_c]
            if am_c == "none":
                parts_c.append("nosound")
            elif am_c.isdigit():
                parts_c.append(f"a{am_c}")
            if codec_c in ("aac", "opus", "mp3") and am_c != "none":
                parts_c.append(codec_c)
            suffix = "-".join(parts_c)
        return suffix

    def _check_duplicate(self, title, output_dir, suffix=""):
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title).strip()
        if suffix:
            base = f"{safe_title} [{suffix}]"
        else:
            base = safe_title

        possible_exts = ['.mp3', '.mp4', '.mkv', '.webm', '.m4a']
        found = []
        if os.path.isdir(output_dir):
            for f in os.listdir(output_dir):
                name_no_ext, ext = os.path.splitext(f)
                if ext.lower() in possible_exts:
                    if name_no_ext == base or name_no_ext.startswith(base + "_"):
                        found.append(f)

        if not found:
            return None

        result = {"action": "skip"}
        win = tk.Toplevel(self.root)
        win.title("Дубликат")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        self.root.update_idletasks()
        w, h = 480, 260
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(win, text="⚠️ Файл уже существует", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 14, "bold")).pack(pady=(20, 8))
        tk.Label(win, text=f"Найдено: {len(found)} совпадений",
                 bg=BG, fg=FG, font=("Segoe UI", 10)).pack(pady=(0, 4))
        tk.Label(win, text=found[0][:60], bg=BG, fg=FG_DIM,
                 font=("Consolas", 9), wraplength=440).pack(pady=(0, 12))

        def choose(action):
            result["action"] = action
            win.destroy()

        btn_row = tk.Frame(win, bg=BG)
        btn_row.pack(pady=(6, 12))

        HoverButton(btn_row, "⏭ Пропустить", lambda: choose("skip"),
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 10), padx=14, pady=8).pack(side="left", padx=(0, 8))
        HoverButton(btn_row, "📝 Переименовать", lambda: choose("rename"),
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 10), padx=14, pady=8).pack(side="left", padx=(0, 8))
        HoverButton(btn_row, "♻️ Перезаписать", lambda: choose("overwrite"),
                    bg=ACCENT, hover_bg=ACCENT_HOVER, fg="white",
                    font=("Segoe UI", 10), padx=14, pady=8).pack(side="left")

        win.wait_window()
        return result["action"]

    def _build_ui(self):
        header = tk.Frame(self.content, bg=BG)
        header.pack(fill="x", padx=20, pady=(10, 4))

        h_left = tk.Frame(header, bg=BG)
        h_left.pack(side="left", anchor="w")
        tk.Label(h_left, text="🎬 YouTube Downloader", bg=BG, fg=FG,
                 font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(h_left, text=f'v{APP_VERSION} — "{APP_BUILD_NAME}"',
                 bg=BG, fg=FG_DIM, font=("Segoe UI", 9, "italic")).pack(anchor="w")

        h_right = tk.Frame(header, bg=BG)
        h_right.pack(side="right", anchor="ne")
        HoverButton(h_right, "📜 История", self.on_show_history,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 9), padx=10, pady=4).pack(side="right", padx=(6, 0))
        HoverButton(h_right, "🎨 Тема", self.on_change_theme,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 9), padx=10, pady=4).pack(side="right", padx=(6, 0))
        HoverButton(h_right, "🎯 Профили", self.on_show_profiles,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 9), padx=10, pady=4).pack(side="right", padx=(6, 0))
        HoverButton(h_right, "⚙️ Настройки", self.on_show_settings,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 9), padx=10, pady=4).pack(side="right", padx=(6, 0))
        HoverButton(h_right, "🎵 Плеер", self.on_show_player,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 9), padx=10, pady=4).pack(side="right", padx=(6, 0))
        HoverButton(h_right, "📋 Что нового", self.on_show_changelog,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 9), padx=10, pady=4).pack(side="right")

        columns = tk.Frame(self.content, bg=BG)
        columns.pack(fill="both", expand=True, padx=20, pady=(6, 4))

        left_col = tk.Frame(columns, bg=BG)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # правая колонка — Canvas для эффектов
        right_col = tk.Canvas(columns, bg=BG, highlightthickness=0, bd=0)
        right_col.pack(side="right", fill="both", expand=True, padx=(8, 0))

        # фрейм поверх canvas — сюда карточки
        right_content = tk.Frame(right_col, bg=BG)
        self._right_content = right_content
        self._right_canvas = right_col

        def _resize_right(event=None):
            right_col.update_idletasks()
            w = right_col.winfo_width()
            h = right_col.winfo_height()
            if w > 1 and h > 1:
                right_col.itemconfig(self._right_window, width=w)
                right_col.coords(self._right_window, 0, 0)
                right_col.configure(scrollregion=(0, 0, w, h))

        self._right_window = right_col.create_window(
            (0, 0), window=right_content, anchor="nw"
        )
        right_col.bind("<Configure>", _resize_right)

        # ---------- URL ----------
        url_card = HoverCard(left_col)
        url_card.pack(fill="x", pady=(0, 6))
        uc = url_card.content()
        tk.Label(uc, text="Ссылка", bg=BG_CARD, fg=FG_DIM,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(10, 2))
        url_row = tk.Frame(uc, bg=BG_CARD)
        url_row.pack(fill="x", padx=14, pady=(0, 12))
        self.url_entry = tk.Entry(url_row, textvariable=self.url_var,
                                   font=("Segoe UI", 11), bg=BG_INPUT, fg=FG,
                                   insertbackground=FG, relief="flat", bd=0)
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self.url_entry.bind("<Control-KeyPress>", self._on_ctrl_key)
        self.url_entry.bind("<KeyRelease>", self._on_url_change)

        HoverButton(url_row, "📋", self._paste_from_clipboard,
                    bg=BG_INPUT, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 11), padx=10, pady=6).pack(side="right")

        # ---------- Папка ----------
        dir_card = HoverCard(left_col)
        dir_card.pack(fill="x", pady=6)
        dc = dir_card.content()
        d_row = tk.Frame(dc, bg=BG_CARD)
        d_row.pack(fill="x", padx=14, pady=10)
        tk.Label(d_row, text="📁", bg=BG_CARD, fg=FG,
                 font=("Segoe UI", 12)).pack(side="left")
        self.dir_label = tk.Label(d_row, text=settings.get_output_dir(self.settings),
                                   bg=BG_CARD, fg=FG_DIM,
                                   font=("Segoe UI", 9), anchor="w")
        self.dir_label.pack(side="left", fill="x", expand=True, padx=(8, 8))
        HoverButton(d_row, "Выбрать", self.on_choose_dir, icon="folder",
                    bg=BG_INPUT, hover_bg=BORDER_HOVER,
                    font=("Segoe UI", 9), padx=12, pady=4).pack(side="right")
        HoverButton(d_row, "📂", self.on_open_output_dir,
                    bg=BG_INPUT, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 9), padx=10, pady=4).pack(side="right", padx=(0, 4))

        # ---------- Настройки ----------
        opts_card = HoverCard(left_col)
        opts_card.pack(fill="x", pady=6)
        oc = opts_card.content()
        tk.Label(oc, text="Настройки", bg=BG_CARD, fg=FG,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(10, 4))

        cont_row = tk.Frame(oc, bg=BG_CARD)
        cont_row.pack(fill="x", padx=14, pady=3)
        tk.Label(cont_row, text="Контейнер:", bg=BG_CARD, fg=FG_DIM,
                 font=("Segoe UI", 9), width=10, anchor="w").pack(side="left")
        self.rb_cont = {}
        for val in ("mp4", "mkv", "webm"):
            rb = tk.Radiobutton(cont_row, text=val.upper(), variable=self.container_var,
                                value=val, bg=BG_CARD, fg=FG, selectcolor=BG_INPUT,
                                activebackground=BG_CARD, activeforeground=ACCENT,
                                font=("Segoe UI", 9), bd=0, highlightthickness=0,
                                command=self._on_container_change)
            rb.pack(side="left", padx=(8, 0))
            self.rb_cont[val] = rb
        cont_canvas = tk.Canvas(oc, height=3, bg=BG_CARD, highlightthickness=0, bd=0)
        cont_canvas.pack(fill="x", padx=14, pady=(0, 6))
        self.ind_cont = AnimatedIndicator(cont_canvas, self.container_var,
                                           ["mp4", "mkv", "webm"], fps=60)
        for val, rb in self.rb_cont.items():
            self.ind_cont.register(rb, val)

        br_row = tk.Frame(oc, bg=BG_CARD)
        br_row.pack(fill="x", padx=14, pady=3)
        tk.Label(br_row, text="Звук:", bg=BG_CARD, fg=FG_DIM,
                 font=("Segoe UI", 9), width=10, anchor="w").pack(side="left")
        self.rb_audio = {}
        audio_opts = [("best", "Лучший"), ("128", "128"), ("192", "192"),
                      ("256", "256"), ("320", "320"), ("none", "Без звука")]
        for val, label in audio_opts:
            rb = tk.Radiobutton(br_row, text=label, variable=self.audio_mode_var,
                                value=val, bg=BG_CARD, fg=FG, selectcolor=BG_INPUT,
                                activebackground=BG_CARD, activeforeground=ACCENT,
                                font=("Segoe UI", 9), bd=0, highlightthickness=0)
            rb.pack(side="left", padx=(6, 0))
            self.rb_audio[val] = rb
        audio_canvas = tk.Canvas(oc, height=3, bg=BG_CARD, highlightthickness=0, bd=0)
        audio_canvas.pack(fill="x", padx=14, pady=(0, 6))
        self.ind_audio = AnimatedIndicator(audio_canvas, self.audio_mode_var,
                                            [v for v, _ in audio_opts], fps=60)
        for val, rb in self.rb_audio.items():
            self.ind_audio.register(rb, val)

        codec_row = tk.Frame(oc, bg=BG_CARD)
        codec_row.pack(fill="x", padx=14, pady=(3, 6))
        tk.Label(codec_row, text="Кодек:", bg=BG_CARD, fg=FG_DIM,
                 font=("Segoe UI", 9), width=10, anchor="w").pack(side="left")
        self.rb_codec = {}
        codec_opts = [("aac", "AAC"), ("opus", "Opus"), ("mp3", "MP3")]
        for val, label in codec_opts:
            rb = tk.Radiobutton(codec_row, text=label, variable=self.audio_codec_var,
                                value=val, bg=BG_CARD, fg=FG, selectcolor=BG_INPUT,
                                activebackground=BG_CARD, activeforeground=ACCENT,
                                font=("Segoe UI", 9), bd=0, highlightthickness=0)
            rb.pack(side="left", padx=(6, 0))
            self.rb_codec[val] = rb
            if val == "opus":
                self.rb_opus = rb
        codec_canvas = tk.Canvas(oc, height=3, bg=BG_CARD, highlightthickness=0, bd=0)
        codec_canvas.pack(fill="x", padx=14, pady=(0, 10))
        self.ind_codec = AnimatedIndicator(codec_canvas, self.audio_codec_var,
                                            [v for v, _ in codec_opts], fps=60)
        for val, rb in self.rb_codec.items():
            self.ind_codec.register(rb, val)

        extra_row = tk.Frame(oc, bg=BG_CARD)
        extra_row.pack(fill="x", padx=14, pady=(0, 10))
        self.mark_var = tk.BooleanVar(value=self.settings.get("mark_settings", True))
        tk.Checkbutton(
            extra_row, text="Помечать настройки в имени файла",
            variable=self.mark_var, bg=BG_CARD, fg=FG,
            selectcolor=BG_INPUT, activebackground=BG_CARD,
            activeforeground=ACCENT, font=("Segoe UI", 9),
            bd=0, highlightthickness=0,
        ).pack(anchor="w")

        # ---------- Режим ----------
        mode_card = HoverCard(left_col)
        mode_card.pack(fill="x", pady=6)
        mc = mode_card.content()
        m_row = tk.Frame(mc, bg=BG_CARD)
        m_row.pack(fill="x", padx=14, pady=(10, 4))
        tk.Label(m_row, text="Режим:", bg=BG_CARD, fg=FG_DIM,
                 font=("Segoe UI", 9), width=10, anchor="w").pack(side="left")
        self.rb_mode_video = tk.Radiobutton(m_row, text="🎬 MP4", variable=self.mode_var,
                                             value="video", bg=BG_CARD, fg=FG, selectcolor=BG_INPUT,
                                             activebackground=BG_CARD, activeforeground=ACCENT,
                                             font=("Segoe UI", 10), bd=0, highlightthickness=0,
                                             command=self._on_mode_change)
        self.rb_mode_video.pack(side="left", padx=(6, 0))
        self.rb_mode_audio = tk.Radiobutton(m_row, text="🎵 MP3", variable=self.mode_var,
                                             value="audio", bg=BG_CARD, fg=FG, selectcolor=BG_INPUT,
                                             activebackground=BG_CARD, activeforeground=ACCENT,
                                             font=("Segoe UI", 10), bd=0, highlightthickness=0,
                                             command=self._on_mode_change)
        self.rb_mode_audio.pack(side="left", padx=(12, 0))
        mode_canvas = tk.Canvas(mc, height=4, bg=BG_CARD, highlightthickness=0, bd=0)
        mode_canvas.pack(fill="x", padx=14, pady=(0, 10))
        self.ind_mode = AnimatedIndicator(mode_canvas, self.mode_var,
                                           ["video", "audio"], fps=60)
        self.ind_mode.register(self.rb_mode_video, "video")
        self.ind_mode.register(self.rb_mode_audio, "audio")

        # ---------- ПРАВАЯ КОЛОНКА ----------
        info_card = HoverCard(right_content)
        info_card.pack(side="top", fill="x", pady=(0, 6))
        ic = info_card.content()

        self.thumb_label = tk.Label(ic, bg=BG_CARD, bd=0, cursor="hand2")
        self.thumb_label.pack(pady=(8, 4))
        self.thumb_label.bind("<Double-Button-1>", self._open_in_browser)

        self.title_label = tk.Label(ic, text="", bg=BG_CARD, fg=FG,
                                     font=("Segoe UI", 9, "bold"),
                                     wraplength=380, justify="center", anchor="center")
        self.title_label.pack(fill="x", padx=14, pady=(0, 8))

        fmt_card = HoverCard(right_content)
        fmt_card.pack(side="top", fill="x", pady=(6, 0))
        fc = fmt_card.content()
        tk.Label(fc, text="Качество", bg=BG_CARD, fg=FG,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
        self.quality_row = tk.Frame(fc, bg=BG_CARD)
        self.quality_row.pack(fill="x", padx=14, pady=(0, 10))
        self.quality_group = QualityGroup(
            self.quality_row,
            on_change=self._on_quality_change,
            columns=3
        )

        # ---------- НИЖНЯЯ ПАНЕЛЬ ----------
        bp = self.bottom_panel
        tk.Frame(bp, bg=BORDER, height=1).pack(fill="x")

        btn_row = tk.Frame(bp, bg=BG)
        btn_row.pack(fill="x", padx=20, pady=(8, 4))

        self.fetch_btn = HoverButton(btn_row, "Получить форматы", self.on_fetch,
                                      icon="search",
                                      font=("Segoe UI", 11, "bold"), padx=20, pady=8)
        self.fetch_btn.pack(side="left", padx=(0, 6))

        self.refresh_btn = HoverButton(btn_row, "🔄", self.on_fetch,
                                        bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                                        font=("Segoe UI", 11), padx=12, pady=8)
        self.refresh_btn.pack(side="left")

        self.download_btn = HoverButton(btn_row, "Скачать", self.on_download,
                                         icon="download",
                                         font=("Segoe UI", 12, "bold"), padx=28, pady=8)
        self.download_btn.pack(side="right")
        self.download_btn.set_enabled(False)

        prog_frame = tk.Frame(bp, bg=BG)
        prog_frame.pack(fill="x", padx=20, pady=(0, 4))
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.Horizontal.TProgressbar",
                        background=ACCENT, troughcolor=BG_CARD,
                        bordercolor=BG_CARD, lightcolor=ACCENT, darkcolor=ACCENT)
        self.progress = ttk.Progressbar(prog_frame, orient="horizontal",
                                         mode="determinate", maximum=100,
                                         style="Dark.Horizontal.TProgressbar")
        self.progress.pack(side="left", fill="x", expand=True)
        self.progress_label = tk.Label(prog_frame, text="0%", bg=BG, fg=FG_DIM,
                                        font=("Segoe UI", 9, "bold"), width=6, anchor="e")
        self.progress_label.pack(side="left", padx=(8, 0))

        tk.Label(bp, textvariable=self.status_var, bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 9), anchor="w").pack(fill="x", padx=20, pady=(0, 8))

    def _on_url_change(self, event=None):
        url = self.url_var.get().strip()
        if not url:
            self.set_status("Готов к работе")
            return
        plat = _detect_platform(url)
        self.set_status(f"🔗 {plat}")
        
    def _on_quality_change(self, value):
        """Смена качества."""
        for fmt in self.formats:
            if fmt.get('id') == value:
                self.selected_format = fmt
                self.set_status(f"Выбрано: {self._fmt_label(fmt)}")
                return
        self.selected_format = None

    def _fmt_label(self, fmt):
        """Подпись для кнопки."""
        size_bytes = fmt.get('filesize') or 0
        if not size_bytes:
            size_str = "?"
        elif size_bytes >= 1024 * 1024 * 1024:
            size_str = f"{size_bytes/(1024**3):.1f} GB"
        else:
            size_str = f"{size_bytes/(1024*1024):.0f} MB"

        if self.mode_var.get() == "audio":
            abr = fmt.get('abr') or 0
            return f"{abr:.0f} kbps · {size_str}"

        h = fmt.get('height') or 0
        fps = fmt.get('fps') or 0
        if fps and fps > 30:
            return f"{h}p{fps} · {size_str}"
        return f"{h}p · {size_str}"


    def set_status(self, text):
        self.status_var.set(text)
        self.root.update_idletasks()

    def _on_ctrl_key(self, event):
        key = event.keycode
        if key == 86:
            self.url_entry.event_generate("<<Paste>>")
            return "break"
        elif key == 67:
            self.url_entry.event_generate("<<Copy>>")
            return "break"
        elif key == 88:
            self.url_entry.event_generate("<<Cut>>")
            return "break"
        elif key == 65:
            self.url_entry.select_range(0, "end")
            self.url_entry.icursor("end")
            return "break"

    def on_choose_dir(self):
        current = settings.get_output_dir(self.settings)
        chosen = filedialog.askdirectory(title="Выбери папку", initialdir=current)
        if chosen:
            self.settings["output_dir"] = chosen
            self.dir_label.config(text=chosen)
            settings.save(self.settings)
            self.set_status(f"Папка: {chosen}")
            try:
                folder_pick()
            except Exception:
                pass

    def on_change_theme(self):
        win = tk.Toplevel(self.root)
        win.title("Выбор темы")
        win.configure(bg=BG)
        win.resizable(False, False)

        self.root.update_idletasks()
        w, h = 320, 280
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(win, text="🎨 Выбери тему", bg=BG, fg=FG,
                 font=("Segoe UI", 14, "bold")).pack(pady=(20, 12))

        current = self.settings.get("theme", "dark")
        for key, theme in THEMES.items():
            is_current = (key == current)
            label = theme["name"] + ("  ✓" if is_current else "")
            HoverButton(
                win, label,
                command=lambda k=key, w_=win: self._set_theme(k, w_),
                bg=theme["BG_CARD"], hover_bg=theme["BORDER_HOVER"],
                fg=theme["FG"],
                font=("Segoe UI", 11, "bold"), padx=20, pady=10
            ).pack(fill="x", padx=20, pady=4)
            
    def on_show_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Настройки")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        self.root.update_idletasks()
        w, h = 460, 520
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(win, text="⚙️ Настройки", bg=BG, fg=FG,
                 font=("Segoe UI", 14, "bold")).pack(pady=(18, 12))

        # --- фрейм с чекбоксами ---
        frame = tk.Frame(win, bg=BG)
        frame.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        # локальные переменные для чекбоксов
        vars_map = {}

        def make_check(key, label, hint=""):
            var = tk.BooleanVar(value=self.settings.get(key, True))
            vars_map[key] = var
            row = tk.Frame(frame, bg=BG)
            row.pack(fill="x", pady=(6, 0))
            cb = tk.Checkbutton(
                row, text=label, variable=var,
                bg=BG, fg=FG, selectcolor=BG_INPUT,
                activebackground=BG, activeforeground=ACCENT,
                font=("Segoe UI", 10), bd=0, highlightthickness=0,
                anchor="w", justify="left",
            )
            cb.pack(anchor="w")
            if hint:
                tk.Label(row, text=hint, bg=BG, fg=FG_DIM,
                         font=("Segoe UI", 8, "italic")).pack(anchor="w", padx=(22, 0))

        make_check("sounds_enabled", "🔊 Звуки",
                   "Клики, переключения, уведомления")
        make_check("toasts_enabled", "💬 Всплывающие уведомления",
                   "Тосты в правом нижнем углу")
        make_check("preview_enabled", "🖼 Показывать превью",
                   "Обложка и название трека")
        make_check("animations_enabled", "✨ Анимации",
                   "Плавные переходы, индикаторы")
        make_check("clear_thumb_cache", "🧹 Чистить кэш обложек",
                   "Чтобы Windows показывал свежие превью")
        make_check("embed_metadata", "📝 Метаданные в MP3",
                   "Артист, альбом, год (скоро)")
        make_check("auto_update_ytdlp", "📦 Автообновление yt-dlp",
                   "Скачивать свежую версию с PyPI")
        make_check("auto_sort", "📂 Автосортировка по папкам",
                   "MP3 → Музыка, MP4 → Видео, архив → Архив")
        make_check("check_updates", "🔄 Проверять обновления приложения",
                   "Уведомление при выходе новой версии")

        # --- кнопки ---
        btn_row = tk.Frame(win, bg=BG)
        btn_row.pack(fill="x", padx=24, pady=(0, 16))

        def save_and_close():
            for key, var in vars_map.items():
                self.settings[key] = var.get()
            settings.save(self.settings)
            win.destroy()
            self._apply_settings_live()
            show_toast(self.root, "✅ Настройки сохранены")

        def reset_defaults():
            for key, var in vars_map.items():
                from modules.settings import DEFAULTS
                default = DEFAULTS.get(key, True)
                var.set(default)

        HoverButton(btn_row, "🎨 Иконка", self.on_show_icon_manager,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 10), padx=14, pady=8).pack(side="left")
        HoverButton(btn_row, "Сбросить", reset_defaults,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 10), padx=14, pady=8).pack(side="left", padx=(8, 0))
        HoverButton(btn_row, "Сохранить", save_and_close,
                    bg=ACCENT, hover_bg=ACCENT_HOVER, fg="white",
                    font=("Segoe UI", 10, "bold"), padx=20, pady=8).pack(side="right")

    def _apply_settings_live(self):
        """Применяет настройки без перезапуска (где возможно)."""
        global ANIMATIONS_ENABLED
        ANIMATIONS_ENABLED = self.settings.get("animations_enabled", True)

        # --- звуки ---
        try:
            from modules import sounds
            sounds.SOUNDS_ENABLED = self.settings.get("sounds_enabled", True)
            print(f"🔊 Звуки: {'ON' if sounds.SOUNDS_ENABLED else 'OFF'}")
        except Exception as e:
            print(f"⚠️ Не удалось применить настройку звуков: {e}")

        # --- превью ---
        if not self.settings.get("preview_enabled", True):
            try:
                self.thumb_label.config(image="")
                self.thumb_photo = None
            except Exception:
                pass

    def on_show_changelog(self):
        win = tk.Toplevel(self.root)
        win.title("Что нового")
        win.configure(bg=BG)

        self.root.update_idletasks()
        w, h = 640, 560
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(win, text="📋 Что нового", bg=BG, fg=FG,
                 font=("Segoe UI", 14, "bold")).pack(pady=(15, 8))

        frame = tk.Frame(win, bg=BG)
        frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        txt = tk.Text(frame, yscrollcommand=scrollbar.set,
                      font=("Consolas", 10),
                      bg=BG_CARD, fg=FG, relief="flat",
                      wrap="word", bd=0, highlightthickness=0,
                      padx=12, pady=10)
        txt.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=txt.yview)

        content = "Changelog не найден."
        if os.path.exists(CHANGELOG_PATH):
            try:
                with open(CHANGELOG_PATH, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                content = f"Не удалось прочитать: {e}"
        txt.insert("1.0", content)
        txt.config(state="disabled")

        btn_row = tk.Frame(win, bg=BG)
        btn_row.pack(fill="x", padx=15, pady=(0, 12))

        def close_win():
            win.destroy()

        HoverButton(btn_row, "Закрыть", close_win,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 9), padx=14, pady=6).pack(side="right")

    def on_show_history(self):
        win = tk.Toplevel(self.root)
        win.title("История скачанного")
        win.configure(bg=BG)

        self.root.update_idletasks()
        w, h = 700, 500
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(win, text="📜 История", bg=BG, fg=FG,
                 font=("Segoe UI", 14, "bold")).pack(pady=(15, 8))

        frame = tk.Frame(win, bg=BG)
        frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set,
                              font=("Consolas", 9),
                              bg=BG_CARD, fg=FG,
                              selectbackground=ACCENT, selectforeground="white",
                              bd=0, highlightthickness=0)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        history = self.settings.get("history", [])

        if not history:
            tk.Label(win, text="История пуста", bg=BG, fg=FG_DIM,
                     font=("Segoe UI", 10, "italic")).pack(pady=20)
        else:
            for i, entry in enumerate(history, 1):
                date = entry.get("date", "?")
                file_path = entry.get("file", "")
                url = entry.get("url", "")
                title = entry.get("title", "")
                filename = os.path.basename(file_path) if file_path else "?"
                display = f"{i:2}. [{date}] {title or filename}"
                if url:
                    display += f"  🔗 {url}"
                listbox.insert("end", display)

        btn_row = tk.Frame(win, bg=BG)
        btn_row.pack(fill="x", padx=15, pady=(0, 12))

        def open_selected():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            if idx < len(history):
                f = history[idx].get("file", "")
                if f and os.path.exists(f):
                    open_file(f)

        def open_folder_selected():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            if idx < len(history):
                f = history[idx].get("file", "")
                if f:
                    open_folder(os.path.dirname(f))

        def clear_history():
            self.settings["history"] = []
            settings.save(self.settings)
            win.destroy()

        HoverButton(btn_row, "▶ Открыть файл", open_selected,
                    font=("Segoe UI", 9), padx=12, pady=6).pack(side="left", padx=(0, 6))
        HoverButton(btn_row, "📂 Папка", open_folder_selected,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 9), padx=12, pady=6).pack(side="left", padx=(0, 6))
        HoverButton(btn_row, "🗑 Очистить", clear_history,
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 9), padx=12, pady=6).pack(side="right")

    def _set_theme(self, theme_name, window):
        window.destroy()
        if theme_name == self.settings.get("theme"):
            return
        self.settings["theme"] = theme_name
        settings.save(self.settings)
        self._restart_gui()

    def _restart_gui(self):
        self.settings["mode"] = self.mode_var.get()
        self.settings["container"] = self.container_var.get()
        self.settings["audio_mode"] = self.audio_mode_var.get()
        self.settings["audio_codec"] = self.audio_codec_var.get()

        try:
            geom = self.root.geometry()
            size_part = geom.split("+")[0]
            self.settings["window_geometry"] = size_part
        except Exception:
            pass
        if hasattr(self, "_falling_fx"):
            try:
                self._falling_fx.stop()
            except Exception:
                pass
        settings.save(self.settings)
        for widget in self.root.winfo_children():
            widget.destroy()

        # 🎃 праздничная тема остаётся активной при перезапуске GUI
        if getattr(self, "_holiday_mode", False):
            theme_to_apply = self._holiday_theme
        else:
            theme_to_apply = self.settings.get("theme", "dark")
        _apply_theme_vars(theme_to_apply)
        self.root.configure(bg=BG)
        self._setup_window_frame()
        self._build_ui()
        self._on_mode_change()
        self.root.after(500, self._recalc_indicators)
        self.root.after(100, self._force_show)
        self.root.after(300, self._register_in_taskbar)

    def _on_mode_change(self):
        mode = self.mode_var.get()
        if mode == "audio":
            for rb in self.rb_cont.values():
                rb.config(state="disabled", fg=FG_DIM)
            self.rb_opus.config(state="normal", fg=FG)
            self.rb_audio["none"].config(state="disabled", fg=FG_DIM)
            if self.audio_mode_var.get() == "none":
                self._silent = True
                self.audio_mode_var.set("best")
                self._silent = False
        else:
            for rb in self.rb_cont.values():
                rb.config(state="normal", fg=FG)
            self.rb_audio["none"].config(state="normal", fg=FG)
            self._on_container_change()

    def _on_container_change(self):
        container = self.container_var.get()
        if container == 'mp4':
            self.rb_opus.config(state="disabled", fg=FG_DIM)
            if self.audio_codec_var.get() == 'opus':
                self._silent = True
                self.audio_codec_var.set('aac')
                self._silent = False
        else:
            self.rb_opus.config(state="normal", fg=FG)

    def _on_close(self):
        # сохраняем только НЕ развёрнутое состояние
        if not self._is_maximized:
            try:
                geom = self.root.geometry()
                size_part = geom.split("+")[0]
                self.settings["window_geometry"] = size_part
            except Exception:
                pass
        # остальные настройки
        self.settings["mode"] = self.mode_var.get()
        self.settings["container"] = self.container_var.get()
        self.settings["audio_mode"] = self.audio_mode_var.get()
        self.settings["audio_codec"] = self.audio_codec_var.get()
        self.settings["mark_settings"] = self.mark_var.get()

        try:
            geom = self.root.geometry()
            size_part = geom.split("+")[0]
            self.settings["window_geometry"] = size_part
        except Exception:
            pass
        # останавливаем анимацию
        if hasattr(self, "_falling_fx"):
            try:
                self._falling_fx.stop()
            except Exception:
                pass
        settings.save(self.settings)
        try:
            shutdown()
        except Exception:
            pass
        self.root.destroy()

    def on_fetch(self):
        if self.downloading:
            return
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("URL пустой", "Вставь ссылку.")
            try:
                warning()
            except Exception:
                pass
            return

        if ("playlist" in url.lower() or "list=" in url.lower()):
            self._ask_playlist(url)
            return

        try:
            fetch()
        except Exception:
            pass
        self.fetch_btn.set_enabled(False)
        self.refresh_btn.set_enabled(False)
        self.download_btn.set_enabled(False)
        self.quality_group.clear()
        self.selected_format = None
        self.title_label.config(text="")
        self.thumb_label.config(image="")
        self.thumb_photo = None
        plat = _detect_platform(url)
        self.set_status(f"Получаю форматы с {plat}...")
        threading.Thread(target=self._fetch_worker, args=(url,), daemon=True).start()

    def _fetch_worker(self, url):
        try:
            title, videos, audios, thumb_url, meta = core.get_formats(url)
            self.title_text = title
            self.meta = meta
            self.current_url = url
            if self.mode_var.get() == "audio":
                sorted_fmts = core.unique_sorted_audio(audios)
                lines = [f"{f['abr']:.0f} kbps | {f['acodec']} | {f['ext']} | "
                         f"{f['filesize']/(1024*1024):.1f} MB" for f in sorted_fmts]
            else:
                sorted_fmts = core.unique_sorted_video(videos)
                lines = [f"{f['height']}p{f['fps']} | {f['ext']} | "
                         f"{f['filesize']/(1024*1024):.1f} MB" for f in sorted_fmts]
            self.formats = sorted_fmts
            self.root.after(0, self._populate_formats, title, lines, thumb_url)
        except Exception as e:
            self.root.after(0, self._fetch_error, str(e))

    def _populate_formats(self, title, lines, thumb_url=None):
        self.title_label.config(text=f"🎬 {title}")

        # заполняем кнопки качества
        items = []
        for fmt in self.formats:
            items.append((self._fmt_label(fmt), fmt['id']))
        self.quality_group.set_items(items)

        self.fetch_btn.set_enabled(True)
        self.refresh_btn.set_enabled(True)
        self.download_btn.set_enabled(bool(self.formats))
        self.set_status(f"Найдено: {len(self.formats)}")

        self.thumb_photo = None
        self.thumb_label.config(image="")

        if thumb_url:
            threading.Thread(
                target=self._load_thumb_worker, args=(thumb_url,), daemon=True
            ).start()

    def _load_thumb_worker(self, url):
        if not self.settings.get("preview_enabled", True):
            return
        result = load_thumbnail(url, target_w=200)
        if result:
            photo, w, h = result
            self.root.after(0, self._set_thumb, photo, w, h)

    def _set_thumb(self, photo, w, h):
        self.thumb_photo = photo
        self.thumb_label.config(image=photo, width=w, height=h)
        self._thumb_ratio = (w, h)

    def _fetch_error(self, msg):
        self.fetch_btn.set_enabled(True)
        self.refresh_btn.set_enabled(True)
        self.set_status("Ошибка получения форматов")
        messagebox.showerror("Ошибка", msg)
        try:
            error()
        except Exception:
            pass

    def on_download(self):
        if self.downloading:
            return
        fmt = getattr(self, "selected_format", None)
        if not fmt:
            messagebox.showwarning("Качество не выбрано", "Выбери качество.")
            try:
                warning()
            except Exception:
                pass
            return
        url = self.url_var.get().strip()
        ...
        # fmt уже определён выше

        suffix_for_check = self._build_suffix_for_check()
        output_dir_check = self._get_output_dir()
        action = self._check_duplicate(self.title_text, output_dir_check, suffix_for_check)
        if action == "skip":
            self.set_status("⏭ Пропущено (файл уже есть)")
            return
        self._rename_flag = (action == "rename")

        self.downloading = True
        self.fetch_btn.set_enabled(False)
        self.refresh_btn.set_enabled(False)
        self._set_download_btn_cancel_mode()
        self.set_status("Скачиваю...")
        try:
            download_start()
        except Exception:
            pass
        mode = self.mode_var.get()
        threading.Thread(target=self._download_worker, args=(url, fmt, mode), daemon=True).start()

    def _download_worker(self, url, fmt, mode):
        try:
            core.PROGRESS_CALLBACK = self._on_progress
            output_dir = self._get_output_dir()
            suffix = self._build_suffix_for_check()

            if mode == "audio":
                codec = self.audio_codec_var.get()
                if codec not in ("mp3", "m4a"):
                    codec = "mp3"
                bitrate = None
                am = self.audio_mode_var.get()
                if am.isdigit():
                    bitrate = int(am)

                final_path = core.download_audio(
                    url, fmt['id'], output_dir,
                    codec=codec, bitrate=bitrate,
                    name_suffix=suffix,
                    rename_if_exists=self._rename_flag
                )
                self._last_downloaded_file = final_path

                # --- ЕДИНСТВЕННЫЙ вызов embed_cover ---
                mp3_path = final_path or embed.find_latest_mp3(output_dir)
                if mp3_path and os.path.exists(mp3_path):
                    thumb = embed.find_thumbnail(mp3_path)
                    cover = thumb if thumb else (COVER_PATH if os.path.exists(COVER_PATH) else None)
                    if cover:
                        embed.embed_cover(mp3_path, cover)

                    # метаданные (артист, альбом, год)
                    if self.settings.get("embed_metadata", True) and self.meta:
                        embed.embed_metadata(mp3_path, self.meta)

                    # метаданные (артист, альбом, год)
                    if self.settings.get("embed_metadata", True) and self.meta:
                        embed.embed_metadata(mp3_path, self.meta)

                # --- чистка временных ---
                try:
                    embed.cleanup_temp_files(output_dir)
                except Exception:
                    pass
            else:
                container = self.container_var.get()
                am = self.audio_mode_var.get()
                audio_mode = 'best'
                audio_bitrate = None
                audio_codec = None

                if am == 'none':
                    audio_mode = 'none'
                elif am.isdigit():
                    audio_mode = 'bitrate'
                    audio_bitrate = int(am)

                # В видео-режиме НЕ конвертируем аудио — оставляем как есть!
                # (выбор кодека актуален только для аудио-режима)
                pass

                final_path = core.download_video(
                    url, fmt['id'], output_dir,
                    container=container,
                    audio_mode=audio_mode,
                    audio_bitrate=audio_bitrate,
                    audio_codec=audio_codec,
                    name_suffix=suffix,
                    rename_if_exists=self._rename_flag
                )
                self._last_downloaded_file = final_path

            core.PROGRESS_CALLBACK = None
            self.root.after(0, self._download_done)
        except yt_dlp.utils.DownloadCancelled:
            core.PROGRESS_CALLBACK = None
            self.root.after(0, self._download_cancelled)
        except Exception as e:
            core.PROGRESS_CALLBACK = None
            self.root.after(0, self._download_error, str(e))

    def _download_done(self):
        self.downloading = False
        self.fetch_btn.set_enabled(True)
        self.refresh_btn.set_enabled(True)
        self._set_download_btn_normal_mode()
        output_dir = self._get_output_dir()
        self.set_status(f"✅ Готово! Файл в: {output_dir}")

        self.settings["mode"] = self.mode_var.get()
        self.settings["container"] = self.container_var.get()
        self.settings["audio_mode"] = self.audio_mode_var.get()
        self.settings["audio_codec"] = self.audio_codec_var.get()
        self.settings["mark_settings"] = self.mark_var.get()

        saved_url = self.url_var.get().strip()
        settings.add_recent_url(self.settings, saved_url)
        self.url_var.set("")

        latest_file = getattr(self, "_last_downloaded_file", None)
        if latest_file and os.path.exists(latest_file):
            settings.add_to_history(self.settings, latest_file,
                                    url=saved_url,
                                    title=self.title_text)
        self._last_downloaded_file = None
        self.selected_format = None

        # чистим кэш ПОСЛЕ вшивания
        if self.settings.get("clear_thumb_cache", True):
            try:
                from modules import cache
                n1 = cache.clear_thumbnail_cache(latest_file)
                n2 = cache.clear_vlc_cache()
                print(f"🧹 Кэш: Windows ({n1}), VLC ({n2})")
            except Exception as e:
                print(f"⚠️ Ошибка чистки кэша: {e}")

        settings.save(self.settings)
        try:
            done()
            file_saved()
        except Exception:
            pass

        if latest_file:
            show_toast(self.root, f"✅ Файл сохранён:\n{os.path.basename(latest_file)}",
                       folder=output_dir, file_path=latest_file)
        else:
            show_toast(self.root, f"✅ Файл сохранён:\n{output_dir}", folder=output_dir)

    def _download_error(self, msg):
        self.downloading = False
        self.fetch_btn.set_enabled(True)
        self.refresh_btn.set_enabled(True)
        self._set_download_btn_normal_mode()
        try:
            error()
        except Exception:
            pass
        show_toast(self.root, f"❌ Ошибка:\n{msg}", bg="#3a1010", fg="#ffaaaa")

    def _ask_playlist(self, url):
        win = tk.Toplevel(self.root)
        win.title("Плейлист обнаружен")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        self.root.update_idletasks()
        w, h = 440, 220
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(win, text="📚 Плейлист обнаружен", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 14, "bold")).pack(pady=(20, 8))
        tk.Label(win, text="Скачать весь плейлист в подпапку?",
                 bg=BG, fg=FG, font=("Segoe UI", 10)).pack(pady=(0, 16))

        def choose(playlist):
            win.destroy()
            if playlist:
                self._download_playlist(url)
            else:
                try:
                    fetch()
                except Exception:
                    pass
                self.fetch_btn.set_enabled(False)
                self.refresh_btn.set_enabled(False)
                self.download_btn.set_enabled(False)
                self.quality_group.clear()
                self.title_label.config(text="")
                threading.Thread(target=self._fetch_worker, args=(url,), daemon=True).start()

        btn_row = tk.Frame(win, bg=BG)
        btn_row.pack()

        HoverButton(btn_row, "📚 Весь плейлист", lambda: choose(True),
                    bg=ACCENT, hover_bg=ACCENT_HOVER, fg="white",
                    font=("Segoe UI", 10, "bold"), padx=16, pady=8).pack(side="left", padx=(0, 8))
        HoverButton(btn_row, "🎬 Одно видео", lambda: choose(False),
                    bg=BG_CARD, hover_bg=BORDER_HOVER, fg=FG,
                    font=("Segoe UI", 10), padx=16, pady=8).pack(side="left")

    def _download_playlist(self, url):
        if self.downloading:
            return
        self.downloading = True
        self.fetch_btn.set_enabled(False)
        self.refresh_btn.set_enabled(False)
        self.download_btn.set_enabled(False)
        self.formats_list.delete(0, "end")
        self.title_label.config(text="")
        self.set_status("📚 Получаю плейлист...")
        threading.Thread(target=self._playlist_worker, args=(url,), daemon=True).start()

    def _playlist_worker(self, url):
        try:
            output_dir = settings.get_output_dir(self.settings)
            mode = self.mode_var.get()
            suffix = self._build_suffix_for_check()

            core.PROGRESS_CALLBACK = self._on_progress

            if mode == "audio":
                codec = self.audio_codec_var.get() if self.audio_codec_var.get() in ("mp3", "m4a") else "mp3"
                playlist_dir, title = core.download_playlist(
                    url, output_dir, mode='audio', codec=codec, name_suffix=suffix
                )
            else:
                container = self.container_var.get()
                playlist_dir, title = core.download_playlist(
                    url, output_dir, mode='video', container=container, name_suffix=suffix
                )

            core.PROGRESS_CALLBACK = None

            if mode == "audio" and os.path.isdir(playlist_dir):
                for f in os.listdir(playlist_dir):
                    if f.lower().endswith('.mp3'):
                        mp3_path = os.path.join(playlist_dir, f)
                        thumb = embed.find_thumbnail(mp3_path)
                        cover = thumb if thumb else (COVER_PATH if os.path.exists(COVER_PATH) else None)
                        if cover:
                            embed.embed_cover(mp3_path, cover)
                try:
                    embed.cleanup_temp_files(playlist_dir)
                except Exception:
                    pass

            self.root.after(0, self._playlist_done, playlist_dir, title)
        except Exception as e:
            core.PROGRESS_CALLBACK = None
            self.root.after(0, self._download_error, str(e))

    def _playlist_done(self, playlist_dir, title):
        self.downloading = False
        self.fetch_btn.set_enabled(True)
        self.refresh_btn.set_enabled(True)
        self.download_btn.set_enabled(True)
        self.set_status(f"✅ Плейлист сохранён: {title}")
        try:
            done()
        except Exception:
            pass
        show_toast(self.root, f"✅ Плейлист сохранён:\n{title}",
                   folder=playlist_dir)

    def _on_progress(self, d):
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                percent = downloaded / total * 100
                self.root.after(0, self._set_progress_target, percent)

            # скорость и ETA
            speed = d.get('speed') or 0
            eta = d.get('eta')
            self.root.after(0, self._set_download_info, speed, eta)

        elif d.get('status') == 'finished':
            self.root.after(0, self._set_progress_target, 100)
            
    def _set_download_info(self, speed_bps, eta_sec):
        """Обновляет статус с прогрессом, скоростью и ETA."""
        speed_str = _fmt_speed(speed_bps)
        eta_str = _fmt_eta(eta_sec)
        percent = self.progress_target

        self.set_status(f"⬇ {percent:.0f}% · {speed_str} · осталось {eta_str}")

    def _set_progress_target(self, percent):
        self.progress_target = float(percent)
        if self.progress_anim_id is None:
            self._tick_progress()

    def _tick_progress(self):
        diff = self.progress_target - self.progress_current
        if abs(diff) < 0.3:
            self.progress_current = self.progress_target
            self.progress['value'] = self.progress_current
            self.progress_label.config(text=f"{self.progress_current:.0f}%")
            self.progress_anim_id = None
            return
        self.progress_current += diff * 0.2
        self.progress['value'] = self.progress_current
        self.progress_label.config(text=f"{self.progress_current:.0f}%")
        self.progress_anim_id = self.root.after(16, self._tick_progress)

    def _set_progress(self, percent):
        self.progress_current = float(percent)
        self.progress_target = float(percent)
        self.progress['value'] = percent
        self.progress_label.config(text=f"{percent:.0f}%")


def run():
    try:
        startup()
    except Exception:
        pass

    root = tk.Tk()
    root.withdraw()

    show_splash(root, duration_ms=1200)

    def open_main():
        app = DownloaderApp(root)
        root.after(100, app._force_show)
        root.after(300, app._register_in_taskbar)

    root.after(1200, open_main)
    root.mainloop()