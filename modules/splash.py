import tkinter as tk
from config import APP_VERSION, APP_BUILD_NAME


def show_splash(root, duration_ms=1200):
    """Показывает заставку при запуске."""
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    splash.configure(bg="#1e1e1e")

    w, h = 420, 240
    root.update_idletasks()
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    splash.geometry(f"{w}x{h}+{x}+{y}")

    # Логотип
    tk.Label(splash, text="YouTube Downloader", bg="#1e1e1e", fg="#e0e0e0",
             font=("Segoe UI", 22, "bold")).pack(expand=True, pady=(50, 0))
    tk.Label(splash, text=f"v{APP_VERSION} — {APP_BUILD_NAME}",
             bg="#1e1e1e", fg="#888888",
             font=("Segoe UI", 10, "italic")).pack()
    tk.Label(splash, text="🎬", bg="#1e1e1e", fg="#e62117",
             font=("Segoe UI", 36)).pack(pady=(0, 20))

    splash.attributes("-alpha", 0.0)

    def fade_in(alpha=0.0):
        if alpha >= 1.0:
            splash.after(duration_ms, fade_out)
            return
        alpha += 0.1
        splash.attributes("-alpha", alpha)
        splash.after(20, lambda: fade_in(alpha))

    def fade_out(alpha=1.0):
        if alpha <= 0.0:
            splash.destroy()
            return
        alpha -= 0.1
        splash.attributes("-alpha", alpha)
        splash.after(20, lambda: fade_out(alpha))

    fade_in()
    splash.update()