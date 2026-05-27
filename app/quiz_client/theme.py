import tkinter as tk
from tkinter import ttk


COLORS = {
    "bg": "#f5f7fa",
    "panel": "#ffffff",
    "panel_alt": "#edf2f8",
    "ink": "#1f2937",
    "muted": "#5f6b7a",
    "line": "#d8dee8",
    "green": "#1177d1",
    "green_dark": "#0f67b4",
    "gold": "#f98012",
    "red": "#c9403a",
    "success": "#eaf7ef",
    "warning": "#fff3e6",
    "blue_soft": "#e9f2ff",
    "brand": "#0f6cbf",
    "brand_dark": "#0c5ea7",
    "chip_bg": "#eef4fb",
    "chip_border": "#cbd9eb",
    "chip_text": "#24446b",
    "hover_soft": "#f7fafc",
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
    style.configure("PageTitle.TLabel", background=COLORS["panel"], foreground=COLORS["ink"], font=("Segoe UI", 22, "bold"))
    style.configure("Subtitle.TLabel", background=COLORS["panel"], foreground=COLORS["muted"], font=("Segoe UI", 10))
    style.configure("CardTitle.TLabel", background=COLORS["panel"], foreground=COLORS["ink"], font=("Segoe UI", 13, "bold"))
    style.configure("Card.TLabel", background=COLORS["panel"], foreground=COLORS["ink"], font=("Segoe UI", 10))
    style.configure("Primary.TButton", background=COLORS["brand"], foreground="#ffffff", font=("Segoe UI", 10, "bold"), borderwidth=0, padding=(16, 10))
    style.map("Primary.TButton", background=[("active", COLORS["brand_dark"]), ("disabled", "#9fbfdf")])
    style.configure("Quiet.TButton", background=COLORS["panel_alt"], foreground=COLORS["ink"], borderwidth=0, padding=(12, 9))
    style.map("Quiet.TButton", background=[("active", COLORS["blue_soft"])])
    style.configure("Danger.TButton", background="#fdeeee", foreground=COLORS["red"], borderwidth=0, padding=(12, 9))
    style.map("Danger.TButton", background=[("active", "#f9dfdf")])
    style.configure("Nav.TButton", background=COLORS["panel"], foreground=COLORS["muted"], borderwidth=0, padding=(12, 8))
    style.map("Nav.TButton", foreground=[("active", COLORS["brand"])], background=[("active", COLORS["blue_soft"])])
    style.configure("TEntry", fieldbackground="#ffffff", padding=7, bordercolor=COLORS["line"], lightcolor=COLORS["line"], darkcolor=COLORS["line"])
    style.configure("TCombobox", fieldbackground="#ffffff", foreground=COLORS["ink"], padding=5)
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", "#ffffff")],
        selectbackground=[("readonly", "#ffffff")],
        foreground=[("readonly", COLORS["ink"])],
        selectforeground=[("readonly", COLORS["ink"])],
    )
    style.configure("Treeview", background=COLORS["panel"], fieldbackground=COLORS["panel"], borderwidth=0, rowheight=36)
    style.map("Treeview", background=[("selected", COLORS["blue_soft"])], foreground=[("selected", COLORS["ink"])])
    style.configure("Treeview.Heading", background=COLORS["blue_soft"], foreground=COLORS["muted"], relief="flat", font=("Segoe UI", 9, "bold"))
    style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", background=COLORS["panel_alt"], foreground=COLORS["muted"], padding=(16, 10))
    style.map("TNotebook.Tab", background=[("selected", COLORS["brand"])], foreground=[("selected", "#ffffff")])
    style.configure("Horizontal.TProgressbar", troughcolor=COLORS["panel_alt"], background=COLORS["brand"])
    return style
