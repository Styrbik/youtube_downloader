import tkinter as tk
import os
import subprocess
import sys


def open_folder(path):
    """Открывает папку в проводнике."""
    if not os.path.exists(path):
        return
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"⚠️ Не удалось открыть папку: {e}")


def open_file(path):
    """Открывает файл в программе по умолчанию."""
    if not os.path.exists(path):
        return
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"⚠️ Не удалось открыть файл: {e}")


def show_toast(root, text, duration=2500, bg="#2a2a2a", fg="#e0e0e0",
               folder=None, file_path=None):
    # проверяем, включены ли тосты
    try:
        from modules import settings
        s = settings.load()
        if not s.get("toasts_enabled", True):
            return
    except Exception:
        pass
    """Всплывашка. Клик → открыть папку. Двойной клик → открыть файл."""
    toast = tk.Toplevel(root)
    toast.overrideredirect(True)
    toast.configure(bg=bg)

    label = tk.Label(toast, text=text, bg=bg, fg=fg, font=("Segoe UI", 10),
                     padx=20, pady=12, justify="left",
                     cursor="hand2" if (folder or file_path) else "")
    label.pack()

    if folder or file_path:
        _click_timer = {"id": None}

        def do_single():
            _click_timer["id"] = None
            if folder:
                open_folder(folder)
            toast.destroy()

        def on_click(e):
            if not file_path:
                if folder:
                    open_folder(folder)
                toast.destroy()
                return
            if _click_timer["id"] is not None:
                toast.after_cancel(_click_timer["id"])
            _click_timer["id"] = toast.after(250, do_single)

        def on_double(e):
            if _click_timer["id"] is not None:
                toast.after_cancel(_click_timer["id"])
                _click_timer["id"] = None
            if file_path:
                open_file(file_path)
            toast.destroy()

        def on_enter(e):
            label.config(bg="#3a3a3a")
            toast.config(bg="#3a3a3a")

        def on_leave(e):
            label.config(bg=bg)
            toast.config(bg=bg)

        def on_right_click(e):
            """ПКМ — показать файл в проводнике."""
            if file_path and os.path.exists(file_path):
                try:
                    subprocess.Popen(["explorer", "/select,", os.path.normpath(file_path)])
                except Exception as ex:
                    print(f"⚠️ Не удалось открыть проводник: {ex}")
            elif folder and os.path.exists(folder):
                open_folder(folder)
            toast.destroy()

        label.bind("<Button-1>", on_click)
        label.bind("<Double-Button-1>", on_double)
        label.bind("<Button-3>", on_right_click)
        label.bind("<Enter>", on_enter)
        label.bind("<Leave>", on_leave)

        hint_text = "📂 1 клик — папка"
        if file_path:
            hint_text += "  •  🎵 2 клика — открыть  •  📍 ПКМ — показать"
        tk.Label(toast, text=hint_text, bg=bg, fg="#888",
                 font=("Segoe UI", 8)).pack(pady=(0, 6))

    root.update_idletasks()
    w = toast.winfo_reqwidth()
    h = toast.winfo_reqheight()
    x = root.winfo_screenwidth() - w - 30
    y = root.winfo_screenheight() - h - 60
    toast.geometry(f"{w}x{h}+{x}+{y}")

    toast.attributes("-alpha", 0.0)

    def fade_in(alpha=0.0):
        if alpha >= 1.0:
            toast.after(duration, fade_out)
            return
        alpha += 0.1
        toast.attributes("-alpha", alpha)
        toast.after(20, lambda: fade_in(alpha))

    def fade_out(alpha=1.0):
        if alpha <= 0.0:
            toast.destroy()
            return
        alpha -= 0.1
        toast.attributes("-alpha", alpha)
        toast.after(20, lambda: fade_out(alpha))

    fade_in()