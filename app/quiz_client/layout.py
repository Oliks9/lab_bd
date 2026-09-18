import tkinter as tk
from tkinter import ttk


class ScrollArea(ttk.Frame):
    def __init__(self, parent, padding=0):
        super().__init__(parent, style="App.TFrame")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, width=1, height=1, highlightthickness=0, background="#f5f7fa")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        horizontal = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.content = ttk.Frame(self.canvas, style="App.TFrame", padding=padding)
        self.window = self.canvas.create_window(0, 0, anchor="nw", window=self.content)
        self.canvas.bind("<Configure>", self.resize)
        self.content.bind("<Configure>", self.resize)

    def resize(self, _event=None):
        width = max(self.canvas.winfo_width(), self.content.winfo_reqwidth())
        height = max(self.canvas.winfo_height(), self.content.winfo_reqheight())
        self.canvas.itemconfigure(self.window, width=width, height=height)
        self.canvas.configure(scrollregion=(0, 0, width, height))

    def reveal(self, widget):
        self.update_idletasks()
        self.resize()
        self.update_idletasks()
        for axis in ("x", "y"):
            start = getattr(widget, f"winfo_root{axis}")() - getattr(self.content, f"winfo_root{axis}")()
            length = widget.winfo_width() if axis == "x" else widget.winfo_height()
            extent = self.content.winfo_width() if axis == "x" else self.content.winfo_height()
            visible = self.canvas.winfo_width() if axis == "x" else self.canvas.winfo_height()
            offset = getattr(self.canvas, f"canvas{axis}")(0)
            margin = min(8, max(0, (visible - length) // 2))
            if start < offset:
                getattr(self.canvas, f"{axis}view_moveto")(max(0, start - margin) / max(1, extent))
            elif start + length > offset + visible:
                target = start if length > visible else start + length + margin - visible
                getattr(self.canvas, f"{axis}view_moveto")(max(0, target) / max(1, extent))


class ScrollTable(ttk.Treeview):
    def __init__(self, parent, **kwargs):
        self.shell = ttk.Frame(parent, style="Panel.TFrame")
        self.shell.rowconfigure(0, weight=1)
        self.shell.columnconfigure(0, weight=1)
        super().__init__(self.shell, **kwargs)
        super().grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(self.shell, orient="vertical", command=self.yview)
        horizontal = ttk.Scrollbar(self.shell, orient="horizontal", command=self.xview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)

    def pack(self, **kwargs):
        return self.shell.pack(**kwargs)


def flow_row(parent, gap=8):
    children = list(parent.winfo_children())
    if not children:
        return
    for child in children:
        child.pack_forget()
    parent.pack_propagate(False)
    parent.configure(width=max(child.winfo_reqwidth() for child in children))

    def arrange(_event=None):
        parent.configure(width=max(child.winfo_reqwidth() for child in children))
        width = max(parent.winfo_width(), parent.winfo_reqwidth())
        x = y = row_height = 0
        for child in children:
            child_width = child.winfo_reqwidth()
            child_height = child.winfo_reqheight()
            if x and x + child_width > width:
                x = 0
                y += row_height + gap
                row_height = 0
            child.place(x=x, y=y, width=child_width, height=child_height)
            x += child_width + gap
            row_height = max(row_height, child_height)
        parent.configure(height=y + row_height)

    parent.bind("<Configure>", arrange, add="+")
    arrange()
    return arrange


def scroll_event(event):
    widget = event.widget
    if isinstance(widget, (tk.Text, ttk.Treeview, ttk.Combobox, tk.Listbox)):
        return
    while widget is not None:
        if isinstance(widget, tk.Canvas):
            axis = "x" if event.state & 1 else "y"
            first, last = getattr(widget, f"{axis}view")()
            delta = getattr(event, "delta", 0)
            step = -1 if delta > 0 or getattr(event, "num", None) == 4 else 1
            if (step < 0 and first > 0) or (step > 0 and last < 1):
                getattr(widget, f"{axis}view_scroll")(step * 3, "units")
                return "break"
        widget = getattr(widget, "master", None)


def responsive_columns(parent, panels):
    canvas = parent.master
    mode = None

    def arrange(_event=None):
        nonlocal mode
        if not parent.winfo_exists():
            return
        horizontal = canvas.winfo_width() >= sum(panel.winfo_reqwidth() + 16 for panel in panels)
        if horizontal == mode:
            return
        mode = horizontal
        for panel in panels:
            panel.pack_forget()
            panel.pack(side="left" if horizontal else "top", fill="both" if horizontal else "x",
                       expand=horizontal, padx=4 if horizontal else 0, pady=(0, 8))

    canvas.bind("<Configure>", arrange, add="+")
    parent.after_idle(arrange)


def reveal_widget(widget):
    if not isinstance(widget, tk.Misc) or not widget.winfo_exists():
        return
    parent = widget.master
    while parent is not None:
        if isinstance(parent, ScrollArea):
            parent.reveal(widget)
        parent = getattr(parent, "master", None)
