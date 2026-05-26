import tkinter as tk
from tkinter import ttk


COLORS = {
    "bg": "#f6f8fc",
    "panel": "#ffffff",
    "panel_alt": "#eff4fb",
    "ink": "#101828",
    "muted": "#667085",
    "line": "#e4e7ec",
    "green": "#2563eb",
    "green_dark": "#1d4ed8",
    "gold": "#d97706",
    "red": "#dc2626",
    "success": "#ecfdf3",
    "warning": "#fff7ed",
    "blue_soft": "#eff6ff",
}


def configure_theme(root: tk.Tk) -> ttk.Style:
    root.configure(bg=COLORS["bg"])
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(".", background=COLORS["bg"], foreground=COLORS["ink"], font=("Segoe UI", 10))
    style.configure("App.TFrame", background=COLORS["bg"])
    style.configure("Panel.TFrame", background=COLORS["panel"])
    style.configure("Muted.TLabel", background=COLORS["panel"], foreground=COLORS["muted"])
    style.configure("PageTitle.TLabel", background=COLORS["bg"], foreground=COLORS["ink"], font=("Segoe UI", 24, "bold"))
    style.configure("Subtitle.TLabel", background=COLORS["bg"], foreground=COLORS["muted"], font=("Segoe UI", 10))
    style.configure("CardTitle.TLabel", background=COLORS["panel"], foreground=COLORS["ink"], font=("Segoe UI", 14, "bold"))
    style.configure("Card.TLabel", background=COLORS["panel"], foreground=COLORS["ink"], font=("Segoe UI", 10))
    style.configure("Primary.TButton", background=COLORS["green"], foreground="#ffffff", font=("Segoe UI", 10, "bold"), borderwidth=0, padding=(17, 10))
    style.map("Primary.TButton", background=[("active", COLORS["green_dark"]), ("disabled", "#b2c5f4")])
    style.configure("Quiet.TButton", background=COLORS["panel_alt"], foreground=COLORS["ink"], borderwidth=0, padding=(13, 9))
    style.configure("Danger.TButton", background="#fef2f2", foreground=COLORS["red"], borderwidth=0, padding=(13, 9))
    style.map("Danger.TButton", background=[("active", "#fee2e2")])
    style.configure("Nav.TButton", background=COLORS["bg"], foreground=COLORS["muted"], borderwidth=0, padding=(12, 9))
    style.map("Nav.TButton", foreground=[("active", COLORS["green"])], background=[("active", COLORS["panel_alt"])])
    style.configure("TEntry", fieldbackground="#ffffff", padding=7)
    style.configure("TCombobox", fieldbackground="#ffffff", padding=5)
    style.configure("Treeview", background=COLORS["panel"], fieldbackground=COLORS["panel"], borderwidth=0, rowheight=38)
    style.configure("Treeview.Heading", background=COLORS["panel_alt"], foreground=COLORS["muted"], relief="flat", font=("Segoe UI", 9, "bold"))
    style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", background=COLORS["panel_alt"], foreground=COLORS["muted"], padding=(17, 11))
    style.map("TNotebook.Tab", background=[("selected", COLORS["panel"])], foreground=[("selected", COLORS["green"])])
    style.configure("Horizontal.TProgressbar", troughcolor=COLORS["panel_alt"], background=COLORS["green"])
    return style
