import json
import random
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


def app_dir():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


APP_DIR = app_dir()
TEST_FILES = {
    "v1": APP_DIR / "data" / "v1.json",
    "v2": APP_DIR / "data" / "v2.json",
}

THEMES = {
    "Светлая": {
        "bg": "#f4f7fb",
        "panel": "#ffffff",
        "panel_soft": "#edf4fb",
        "ink": "#142033",
        "muted": "#637083",
        "line": "#d8e1ec",
        "blue": "#2364aa",
        "blue_dark": "#184f86",
        "green": "#1f8a5b",
        "green_soft": "#e9f7ef",
        "red": "#c2413b",
        "red_soft": "#fdeeee",
        "amber": "#b47618",
        "amber_soft": "#fff4db",
    },
    "Синяя": {
        "bg": "#eef6fb",
        "panel": "#ffffff",
        "panel_soft": "#e4f1f8",
        "ink": "#102a43",
        "muted": "#586f83",
        "line": "#c8dae8",
        "blue": "#0f6c81",
        "blue_dark": "#0a5162",
        "green": "#247a4d",
        "green_soft": "#e5f5ec",
        "red": "#b9433d",
        "red_soft": "#faeceb",
        "amber": "#a56b10",
        "amber_soft": "#fff3d8",
    },
    "Темная": {
        "bg": "#111827",
        "panel": "#182234",
        "panel_soft": "#22304a",
        "ink": "#f4f7fb",
        "muted": "#aebbd0",
        "line": "#324158",
        "blue": "#58a6ff",
        "blue_dark": "#2f81f7",
        "green": "#56d68b",
        "green_soft": "#173828",
        "red": "#ff7770",
        "red_soft": "#3d2024",
        "amber": "#f5bf4f",
        "amber_soft": "#3a2e17",
    },
}

COLORS = THEMES["Светлая"].copy()


def correct_answer_indices(options):
    explicit = [i for i, opt in enumerate(options) if bool(opt.get("is_correct", False))]
    if explicit:
        return explicit

    best_idx = 0
    best_val = -1.0
    for i, opt in enumerate(options):
        val = float(opt.get("stat", 0.0) or 0.0)
        if val > best_val:
            best_idx = i
            best_val = val
    return [best_idx]


def answer_texts(question, indices):
    options = question.get("options", [])
    return [options[i].get("text", "") for i in indices if 0 <= i < len(options)]


class ScrollFrame(ttk.Frame):
    def __init__(self, parent, height=None):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, bg=COLORS["bg"])
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.content = ttk.Frame(self.canvas, style="Panel.TFrame")
        self.window_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        if height:
            self.canvas.configure(height=height)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.content.bind("<Configure>", self._refresh_scroll)
        self.canvas.bind("<Configure>", self._resize_window)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _refresh_scroll(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_window(self, event):
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _on_mousewheel(self, event):
        if self.winfo_ismapped():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class QuizApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Quiz Trainer")
        self.geometry("1240x820")
        self.minsize(1080, 720)

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.test_key = None
        self.questions = []
        self.current = 0
        self.answers = {}
        self.checked_results = {}
        self.choice_vars = []
        self.option_rows = []
        self.screen = "select"
        self.sidebar_container = None
        self.map_window = None
        self.shuffle_mode = tk.BooleanVar(value=False)
        self.show_only_mistakes = tk.BooleanVar(value=False)
        self.theme_var = tk.StringVar(value="Светлая")

        self.configure_styles()
        self.container = ttk.Frame(self, style="App.TFrame", padding=22)
        self.container.pack(fill="both", expand=True)
        self.bind("<Return>", self.handle_enter)
        self.bind("<KP_Enter>", self.handle_enter)
        self.bind("<BackSpace>", self.handle_backspace)
        self.bind("<Left>", self.handle_backspace)
        self.bind("<Right>", self.handle_enter)
        for digit in range(1, 10):
            self.bind(str(digit), self.handle_digit)
        self.show_select_screen()

    def apply_theme(self, redraw=True):
        global COLORS
        COLORS = THEMES[self.theme_var.get()].copy()
        self.configure_styles()
        if redraw:
            self.show_select_screen()

    def configure_styles(self):
        self.configure(bg=COLORS["bg"])
        self.style.configure("App.TFrame", background=COLORS["bg"])
        self.style.configure("Panel.TFrame", background=COLORS["panel"])
        self.style.configure("Soft.TFrame", background=COLORS["panel_soft"])
        self.style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["ink"], font=("Segoe UI", 24, "bold"))
        self.style.configure("Subtitle.TLabel", background=COLORS["bg"], foreground=COLORS["muted"], font=("Segoe UI", 11))
        self.style.configure("PanelTitle.TLabel", background=COLORS["panel"], foreground=COLORS["ink"], font=("Segoe UI", 15, "bold"))
        self.style.configure("Body.TLabel", background=COLORS["panel"], foreground=COLORS["ink"], font=("Segoe UI", 11))
        self.style.configure("Muted.TLabel", background=COLORS["panel"], foreground=COLORS["muted"], font=("Segoe UI", 10))
        self.style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), padding=(14, 9))
        self.style.configure("Quiet.TButton", font=("Segoe UI", 10), padding=(12, 8))
        self.style.configure("TProgressbar", thickness=10, troughcolor=COLORS["line"], background=COLORS["blue"])

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def make_panel(self, parent, padding=18):
        panel = tk.Frame(parent, bg=COLORS["panel"], bd=0, highlightthickness=1, highlightbackground=COLORS["line"])
        inner = ttk.Frame(panel, style="Panel.TFrame", padding=padding)
        inner.pack(fill="both", expand=True)
        return panel, inner

    def info_banner(self, parent, title, text, accent=None, bg=None, pady=(0, 16)):
        accent = accent or COLORS["blue"]
        bg = bg or COLORS["panel_soft"]
        frame = tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=COLORS["line"])
        frame.pack(fill="x", pady=pady)
        inner = tk.Frame(frame, bg=bg, padx=16, pady=12)
        inner.pack(fill="x")
        tk.Label(inner, text=title, bg=bg, fg=accent, font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x")
        tk.Label(inner, text=text, bg=bg, fg=COLORS["ink"], font=("Segoe UI", 10), wraplength=980, justify="left", anchor="w").pack(fill="x", pady=(4, 0))

    def load_questions(self, key):
        path = TEST_FILES[key]
        if not path.exists():
            messagebox.showerror("Файл не найден", f"Не найден файл вопросов:\n{path}")
            return False

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("Ошибка чтения", f"Не удалось прочитать {path}:\n{exc}")
            return False

        filtered = []
        skipped = []
        for i, question in enumerate(data, start=1):
            options = question.get("options")
            if not isinstance(options, list) or len(options) < 2:
                skipped.append(i)
                continue
            copied = dict(question)
            copied["original_number"] = i
            copied["options"] = [dict(option) for option in options]
            filtered.append(copied)

        if not filtered:
            messagebox.showerror("Ошибка формата", "Нет валидных вопросов для запуска теста")
            return False

        if skipped:
            messagebox.showwarning("Некоторые вопросы пропущены", f"Пропущены вопросы без вариантов: {', '.join(map(str, skipped))}")

        self.questions = filtered
        return True

    def show_select_screen(self):
        self.screen = "select"
        self.clear_container()

        header = ttk.Frame(self.container, style="App.TFrame")
        header.pack(fill="x", pady=(8, 22))
        ttk.Label(header, text="Quiz Trainer", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Тренажер по сетевым технологиям с точными ключами, темами оформления и подробной статистикой.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(6, 0))

        self.info_banner(
            self.container,
            "Инструкция",
            "Выберите V1, настройте тему и порядок вопросов. В тесте отметьте один или несколько вариантов и нажмите Enter или кнопку Далее: ответ автоматически фиксируется, а справа сразу обновляется прогресс.",
            accent=COLORS["blue"],
        )

        grid = ttk.Frame(self.container, style="App.TFrame")
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(0, weight=2)
        grid.columnconfigure(1, weight=1)

        left_panel, left = self.make_panel(grid, padding=22)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        ttk.Label(left, text="Выберите вариант теста", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(left, text="Проверка ответа появится только после нажатия кнопки.", style="Muted.TLabel").pack(anchor="w", pady=(4, 20))

        cards = ttk.Frame(left, style="Panel.TFrame")
        cards.pack(fill="x")
        self.test_card(cards, "v1", "V1", "Базовые сети, OSI, TCP/IP, Ethernet, IP-адресация", 0)
        self.test_card(cards, "v2", "V2", "VLAN, STP, NAT, OSPF, RIP, статическая маршрутизация", 1)
        self.info_banner(
            left,
            "Важно про V2",
            "V2 сейчас считается сырой базой: ответы и формулировки могут быть неточными. Для демонстрации преподавателю лучше проходить V1.",
            accent=COLORS["amber"],
            bg=COLORS["amber_soft"],
            pady=(12, 0),
        )

        right_panel, right = self.make_panel(grid, padding=22)
        right_panel.grid(row=0, column=1, sticky="nsew")
        ttk.Label(right, text="Настройки", style="PanelTitle.TLabel").pack(anchor="w")

        ttk.Label(right, text="Тема оформления", style="Body.TLabel").pack(anchor="w", pady=(20, 8))
        for name in THEMES:
            self.radio(right, name, name, self.theme_var, command=lambda: self.apply_theme(redraw=True))

        ttk.Separator(right).pack(fill="x", pady=22)
        ttk.Label(right, text="Порядок вопросов", style="Body.TLabel").pack(anchor="w", pady=(0, 8))
        self.radio(right, "По порядку", False, self.shuffle_mode)
        self.radio(right, "Вперемешку", True, self.shuffle_mode)

        ttk.Separator(right).pack(fill="x", pady=22)
        ttk.Label(right, text="Во время теста", style="Body.TLabel").pack(anchor="w")
        ttk.Label(
            right,
            text="Справа будет виден живой прогресс: проверено, правильно, ошибки, пропуски и точность.",
            style="Muted.TLabel",
            wraplength=300,
        ).pack(anchor="w", pady=(6, 0))

    def radio(self, parent, text, value, variable, command=None):
        tk.Radiobutton(
            parent,
            text=text,
            value=value,
            variable=variable,
            command=command,
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            activebackground=COLORS["panel"],
            activeforeground=COLORS["ink"],
            selectcolor=COLORS["panel_soft"],
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=4)

    def test_card(self, parent, key, title, description, column):
        frame = tk.Frame(parent, bg=COLORS["panel_soft"], highlightthickness=1, highlightbackground=COLORS["line"])
        frame.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 10, 0), pady=(0, 8))
        parent.columnconfigure(column, weight=1)

        inner = tk.Frame(frame, bg=COLORS["panel_soft"], padx=18, pady=18)
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text=title, bg=COLORS["panel_soft"], fg=COLORS["blue_dark"], font=("Segoe UI", 26, "bold")).pack(anchor="w")
        tk.Label(inner, text=description, bg=COLORS["panel_soft"], fg=COLORS["muted"], font=("Segoe UI", 10), wraplength=310, justify="left").pack(anchor="w", pady=(8, 18))
        tk.Button(
            inner,
            text=f"Начать {title}",
            command=lambda: self.start_test(key),
            bg=COLORS["blue"],
            fg="white",
            activebackground=COLORS["blue_dark"],
            activeforeground="white",
            relief="flat",
            padx=16,
            pady=10,
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
        ).pack(anchor="w")

    def start_test(self, key):
        if key == "v2":
            proceed = messagebox.askyesno(
                "V2 пока сырая",
                "V2 отмечена как сырая база: ответы и формулировки могут быть неточными.\n\nРекомендуется проходить V1. Все равно запустить V2?",
            )
            if not proceed:
                return
        if not self.load_questions(key):
            return
        self.test_key = key
        self.current = 0
        self.answers = {}
        self.checked_results = {}
        self.show_only_mistakes.set(False)
        for question in self.questions:
            random.shuffle(question["options"])
        if self.shuffle_mode.get():
            random.shuffle(self.questions)
        self.show_question_screen()

    def live_stats(self):
        total = len(self.questions)
        answered = sum(1 for value in self.answers.values() if value)
        checked = len(self.checked_results)
        correct = sum(1 for value in self.checked_results.values() if value)
        wrong = checked - correct
        skipped = total - answered
        accuracy = round(correct / checked * 100) if checked else 0
        return total, answered, checked, correct, wrong, skipped, accuracy

    def show_question_screen(self):
        self.screen = "quiz"
        self.clear_container()
        question = self.questions[self.current]
        total, answered, _checked, _correct, _wrong, _skipped, _accuracy = self.live_stats()

        shell = ttk.Frame(self.container, style="App.TFrame")
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.columnconfigure(1, weight=0)
        shell.rowconfigure(1, weight=1)

        top = ttk.Frame(shell, style="App.TFrame")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        ttk.Label(top, text=f"{self.test_key.upper()} • Вопрос {self.current + 1} из {total}", style="Title.TLabel").pack(side="left")
        ttk.Label(top, text=f"Выбраны ответы: {answered}/{total}", style="Subtitle.TLabel").pack(side="right", pady=(12, 0))

        question_panel, content = self.make_panel(shell, padding=22)
        question_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 16))
        sidebar_panel, sidebar = self.make_panel(shell, padding=12)
        sidebar_panel.grid(row=1, column=1, sticky="ns")
        self.sidebar_container = sidebar
        self.render_sidebar(sidebar)

        self.info_banner(
            content,
            "Как проходить",
            "Отметьте ответ мышью или клавишами 1-9. Enter/Далее фиксирует ответ и переходит дальше, Backspace возвращает назад. Кнопка Проверить показывает правильный ответ до перехода.",
            accent=COLORS["blue"],
            pady=(0, 16),
        )

        ttk.Label(content, text=f"Вопрос #{question['original_number']}", style="Muted.TLabel").pack(anchor="w")
        ttk.Label(content, text=question["question"], style="PanelTitle.TLabel", wraplength=800, justify="left").pack(anchor="w", pady=(8, 18))

        hint = "Можно выбрать несколько вариантов" if len(correct_answer_indices(question["options"])) > 1 else "Выберите один вариант"
        ttk.Label(content, text=f"{hint}. Enter — зафиксировать и перейти дальше.", style="Muted.TLabel").pack(anchor="w", pady=(0, 8))

        scroll = ScrollFrame(content, height=340)
        scroll.pack(fill="both", expand=True, pady=(0, 10))

        selected = set(self.answers.get(self.current, []))
        self.choice_vars = []
        self.option_rows = []
        for index, option in enumerate(question["options"]):
            var = tk.BooleanVar(value=index in selected)
            self.choice_vars.append(var)
            row = tk.Frame(scroll.content, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"], cursor="hand2")
            row.pack(fill="x", pady=5, padx=(0, 8))
            self.option_rows.append(row)
            check = tk.Checkbutton(
                row,
                text=f"{index + 1}. {option.get('text', '')}",
                variable=var,
                command=self.on_select,
                bg=COLORS["panel"],
                fg=COLORS["ink"],
                activebackground=COLORS["panel"],
                activeforeground=COLORS["ink"],
                selectcolor=COLORS["panel_soft"],
                font=("Segoe UI", 11),
                wraplength=780,
                justify="left",
                anchor="w",
                padx=12,
                pady=10,
                cursor="hand2",
            )
            check.pack(fill="x")
            row.bind("<Button-1>", lambda _event, i=index: self.toggle_option(i))
            check.bind("<Enter>", lambda _event, r=row: r.configure(highlightbackground=COLORS["blue"]))
            check.bind("<Leave>", lambda _event: self.refresh_option_rows())

        self.refresh_option_rows()

        self.result_var = tk.StringVar(value="")
        result = tk.Label(content, textvariable=self.result_var, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 11, "bold"), anchor="w", justify="left", wraplength=860)
        result.pack(fill="x", pady=(6, 0))

        if self.current in self.checked_results:
            self.show_answer_explanation()

        controls = ttk.Frame(content, style="Panel.TFrame")
        controls.pack(fill="x", pady=(18, 0))
        ttk.Button(controls, text="Назад", style="Quiet.TButton", command=self.go_prev).pack(side="left")
        ttk.Button(controls, text="К выбору теста", style="Quiet.TButton", command=self.show_select_screen).pack(side="left", padx=8)
        ttk.Button(controls, text="Проверить ответ", style="Primary.TButton", command=self.check_current_answer).pack(side="right", padx=(8, 0))
        if self.current == total - 1:
            ttk.Button(controls, text="Завершить (Enter)", style="Quiet.TButton", command=self.finish_with_current_answer).pack(side="right")
        else:
            ttk.Button(controls, text="Далее (Enter)", style="Quiet.TButton", command=self.go_next).pack(side="right")

    def render_sidebar(self, parent):
        total, answered, checked, correct, wrong, skipped, accuracy = self.live_stats()
        ttk.Label(parent, text="Прогресс", style="PanelTitle.TLabel").pack(anchor="w")
        ttk.Label(parent, text=f"Позиция {self.current + 1}/{total}", style="Muted.TLabel").pack(anchor="w", pady=(3, 8))

        ttk.Progressbar(parent, maximum=total, value=self.current + 1).pack(fill="x", pady=(0, 10))

        metrics = tk.Frame(parent, bg=COLORS["panel"])
        metrics.pack(fill="x")
        for col in range(2):
            metrics.columnconfigure(col, weight=1)
        self.sidebar_metric(metrics, "Ответы", f"{answered}/{total}", COLORS["blue"], 0, 0)
        self.sidebar_metric(metrics, "Проверено", f"{checked}/{total}", COLORS["blue_dark"], 0, 1)
        self.sidebar_metric(metrics, "Верно", str(correct), COLORS["green"], 1, 0)
        self.sidebar_metric(metrics, "Ошибки", str(wrong), COLORS["red"], 1, 1)
        self.sidebar_metric(metrics, "Пусто", str(skipped), COLORS["amber"], 2, 0)
        self.sidebar_metric(metrics, "Точность", f"{accuracy}%", COLORS["blue"], 2, 1)

        ttk.Separator(parent).pack(fill="x", pady=10)
        current_status = "не проверен"
        if self.current in self.checked_results:
            current_status = "верно" if self.checked_results[self.current] else "ошибка"
        status_card = tk.Frame(parent, bg=COLORS["panel_soft"], highlightthickness=1, highlightbackground=COLORS["line"])
        status_card.pack(fill="x", pady=(0, 8))
        tk.Label(status_card, text="Текущий вопрос", bg=COLORS["panel_soft"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(7, 0))
        tk.Label(status_card, text=current_status, bg=COLORS["panel_soft"], fg=COLORS["ink"], font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=(0, 7))

        hotkeys = tk.Frame(parent, bg=COLORS["panel"])
        hotkeys.pack(fill="x", pady=(0, 8))
        tk.Label(hotkeys, text="1-9 выбор • Enter далее • Backspace назад", bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w")

        ttk.Button(parent, text="Карта вопросов", style="Primary.TButton", command=self.show_question_map_popup).pack(fill="x", pady=(0, 7))

        quick = tk.Frame(parent, bg=COLORS["panel"])
        quick.pack(fill="x")
        quick.columnconfigure(0, weight=1)
        quick.columnconfigure(1, weight=1)
        ttk.Button(quick, text="Пустой", style="Quiet.TButton", command=self.jump_next_unanswered).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(quick, text="Ошибка", style="Quiet.TButton", command=self.jump_next_wrong).grid(row=0, column=1, sticky="ew", padx=(4, 0))

    def sidebar_metric(self, parent, label, value, accent, row, column):
        frame = tk.Frame(parent, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
        frame.grid(row=row, column=column, sticky="ew", padx=(0 if column == 0 else 4, 4 if column == 0 else 0), pady=3)
        tk.Label(frame, text=label, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 8)).pack(anchor="w", padx=8, pady=(5, 0))
        tk.Label(frame, text=value, bg=COLORS["panel"], fg=accent, font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=8, pady=(0, 5))

    def show_question_map_popup(self):
        if self.map_window and self.map_window.winfo_exists():
            self.map_window.lift()
            self.map_window.focus_force()
            return

        self.map_window = tk.Toplevel(self)
        self.map_window.title("Карта вопросов")
        self.map_window.configure(bg=COLORS["bg"])
        self.map_window.geometry("620x560")
        self.map_window.minsize(520, 420)
        self.map_window.transient(self)

        header = tk.Frame(self.map_window, bg=COLORS["bg"], padx=18, pady=14)
        header.pack(fill="x")
        tk.Label(header, text="Карта вопросов", bg=COLORS["bg"], fg=COLORS["ink"], font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(
            header,
            text="Кликните номер вопроса для перехода. Зеленый - верно, красный - ошибка, синий - выбран, серый - пусто.",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10),
            wraplength=560,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        body = tk.Frame(self.map_window, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"], padx=14, pady=14)
        body.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        scroll = ScrollFrame(body)
        scroll.pack(fill="both", expand=True)
        self.render_question_map(scroll.content, columns=10, close_popup=True)

    def render_question_map(self, parent, columns=7, close_popup=False):
        grid = tk.Frame(parent, bg=COLORS["panel"])
        grid.pack(fill="x", pady=(2, 0))
        for index, _question in enumerate(self.questions):
            if index in self.checked_results:
                bg = COLORS["green"] if self.checked_results[index] else COLORS["red"]
                fg = "white"
            elif self.answers.get(index):
                bg = COLORS["blue"]
                fg = "white"
            else:
                bg = COLORS["panel_soft"]
                fg = COLORS["ink"]
            if index == self.current:
                border = COLORS["amber"]
            else:
                border = COLORS["line"]
            button = tk.Button(
                grid,
                text=str(index + 1),
                command=lambda i=index: self.jump_to_question(i, close_popup=close_popup),
                bg=bg,
                fg=fg,
                activebackground=COLORS["blue_dark"],
                activeforeground="white",
                relief="flat",
                highlightthickness=2,
                highlightbackground=border,
                width=3,
                height=1,
                font=("Segoe UI", 8, "bold"),
                cursor="hand2",
                takefocus=0,
            )
            button.bind("<Button-1>", lambda _event, i=index: self.jump_to_question(i, close_popup=close_popup))
            button.grid(row=index // columns, column=index % columns, padx=3, pady=3)

    def jump_to_question(self, index, close_popup=False):
        if not (0 <= index < len(self.questions)):
            return
        self.process_current_answer(show_message=False)
        self.current = index
        if close_popup and self.map_window and self.map_window.winfo_exists():
            self.map_window.destroy()
            self.map_window = None
        self.show_question_screen()

    def jump_next_unanswered(self):
        if not self.questions:
            return
        for offset in range(1, len(self.questions) + 1):
            index = (self.current + offset) % len(self.questions)
            if not self.answers.get(index):
                self.jump_to_question(index)
                return

    def jump_next_wrong(self):
        if not self.questions:
            return
        for offset in range(1, len(self.questions) + 1):
            index = (self.current + offset) % len(self.questions)
            if index in self.checked_results and not self.checked_results[index]:
                self.jump_to_question(index)
                return

    def on_select(self):
        chosen = [i for i, var in enumerate(self.choice_vars) if var.get()]
        self.answers[self.current] = chosen
        if self.current in self.checked_results:
            del self.checked_results[self.current]
        self.result_var.set("")
        self.refresh_option_rows()
        self.refresh_sidebar()

    def toggle_option(self, index):
        if not (0 <= index < len(self.choice_vars)):
            return
        self.choice_vars[index].set(not self.choice_vars[index].get())
        self.on_select()

    def refresh_option_rows(self):
        if not self.option_rows:
            return
        question = self.questions[self.current]
        correct = set(correct_answer_indices(question["options"]))
        checked = self.current in self.checked_results
        for index, row in enumerate(self.option_rows):
            selected = self.choice_vars[index].get()
            bg = COLORS["panel"]
            border = COLORS["line"]
            if checked and index in correct:
                bg = COLORS["green_soft"]
                border = COLORS["green"]
            elif checked and selected:
                bg = COLORS["red_soft"]
                border = COLORS["red"]
            elif selected:
                bg = COLORS["panel_soft"]
                border = COLORS["blue"]
            row.configure(bg=bg, highlightbackground=border)
            for child in row.winfo_children():
                child.configure(bg=bg, activebackground=bg)

    def refresh_sidebar(self):
        if not self.sidebar_container:
            return
        for widget in self.sidebar_container.winfo_children():
            widget.destroy()
        self.render_sidebar(self.sidebar_container)

    def check_current_answer(self):
        if not self.process_current_answer(show_message=True):
            return
        self.show_question_screen()

    def process_current_answer(self, show_message=False):
        chosen = self.answers.get(self.current, [])
        if not chosen:
            if show_message:
                self.result_var.set("Сначала выберите вариант ответа, затем нажмите проверку.")
            return False

        question = self.questions[self.current]
        correct = set(correct_answer_indices(question["options"]))
        self.checked_results[self.current] = set(chosen) == correct
        self.refresh_option_rows()
        return True

    def show_answer_explanation(self):
        question = self.questions[self.current]
        chosen = self.answers.get(self.current, [])
        correct = correct_answer_indices(question["options"])
        is_correct = self.checked_results.get(self.current, False)
        prefix = "Правильно." if is_correct else "Неправильно."
        chosen_text = "; ".join(answer_texts(question, chosen))
        correct_text = "; ".join(answer_texts(question, correct))
        self.result_var.set(f"{prefix}\nВаш ответ: {chosen_text}\nПравильный ответ: {correct_text}")

    def go_prev(self):
        if self.current > 0:
            self.current -= 1
            self.show_question_screen()

    def go_next(self):
        self.process_current_answer(show_message=False)
        if self.current < len(self.questions) - 1:
            self.current += 1
            self.show_question_screen()

    def finish_with_current_answer(self):
        self.process_current_answer(show_message=False)
        self.show_summary()

    def handle_enter(self, _event=None):
        if self.screen != "quiz" or not self.questions:
            return
        if self.current >= len(self.questions) - 1:
            self.finish_with_current_answer()
        else:
            self.go_next()

    def handle_backspace(self, _event=None):
        if self.screen == "quiz":
            self.go_prev()

    def handle_digit(self, event):
        if self.screen != "quiz":
            return
        index = int(event.char) - 1
        self.toggle_option(index)

    def collect_results(self):
        rows = []
        correct_count = 0
        unanswered_count = 0
        unchecked_count = 0
        for seq, question in enumerate(self.questions):
            user = self.answers.get(seq, [])
            correct = correct_answer_indices(question["options"])
            is_unanswered = len(user) == 0
            is_checked = seq in self.checked_results
            is_correct = bool(user) and is_checked and set(user) == set(correct)
            correct_count += int(is_correct)
            unanswered_count += int(is_unanswered)
            unchecked_count += int(bool(user) and not is_checked)
            rows.append(
                {
                    "seq": seq + 1,
                    "original": question["original_number"],
                    "question": question,
                    "user": user,
                    "correct": correct,
                    "is_correct": is_correct,
                    "is_unanswered": is_unanswered,
                    "is_checked": is_checked,
                }
            )
        return rows, correct_count, unanswered_count, unchecked_count

    def show_summary(self):
        self.screen = "summary"
        rows, correct_count, unanswered_count, unchecked_count = self.collect_results()
        total = len(rows)
        wrong_count = sum(1 for row in rows if row["is_checked"] and not row["is_correct"])
        checked_count = sum(1 for row in rows if row["is_checked"])
        accuracy = round(correct_count / checked_count * 100) if checked_count else 0

        self.clear_container()
        header = ttk.Frame(self.container, style="App.TFrame")
        header.pack(fill="x", pady=(0, 16))
        ttk.Label(header, text=f"Итоги {self.test_key.upper()}", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="К выбору теста", style="Quiet.TButton", command=self.show_select_screen).pack(side="right")
        ttk.Button(header, text="Пройти заново", style="Quiet.TButton", command=lambda: self.start_test(self.test_key)).pack(side="right", padx=8)

        metrics = ttk.Frame(self.container, style="App.TFrame")
        metrics.pack(fill="x", pady=(0, 16))
        for col in range(5):
            metrics.columnconfigure(col, weight=1)
        self.metric_card(metrics, "Точность", f"{accuracy}%", COLORS["blue"], 0)
        self.metric_card(metrics, "Правильно", f"{correct_count}/{total}", COLORS["green"], 1)
        self.metric_card(metrics, "Ошибки", str(wrong_count), COLORS["red"], 2)
        self.metric_card(metrics, "Не проверено", str(unchecked_count), COLORS["amber"], 3)
        self.metric_card(metrics, "Пропущено", str(unanswered_count), COLORS["amber"], 4)

        panel, content = self.make_panel(self.container, padding=18)
        panel.pack(fill="both", expand=True)
        toolbar = ttk.Frame(content, style="Panel.TFrame")
        toolbar.pack(fill="x", pady=(0, 10))
        ttk.Label(toolbar, text=f"Подробный отчет • проверено {checked_count}/{total}", style="PanelTitle.TLabel").pack(side="left")
        tk.Checkbutton(
            toolbar,
            text="Показывать только ошибки, пропуски и непроверенные",
            variable=self.show_only_mistakes,
            command=lambda: self.render_summary_rows(summary.content, rows),
            bg=COLORS["panel"],
            fg=COLORS["ink"],
            activebackground=COLORS["panel"],
            activeforeground=COLORS["ink"],
            selectcolor=COLORS["panel_soft"],
            font=("Segoe UI", 10),
        ).pack(side="right")

        summary = ScrollFrame(content)
        summary.pack(fill="both", expand=True)
        self.render_summary_rows(summary.content, rows)

    def metric_card(self, parent, title, value, accent, column):
        frame = tk.Frame(parent, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
        frame.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 10, 0), ipady=10)
        tk.Label(frame, text=title, bg=COLORS["panel"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", padx=14, pady=(12, 0))
        tk.Label(frame, text=value, bg=COLORS["panel"], fg=accent, font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=14, pady=(2, 12))

    def render_summary_rows(self, parent, rows):
        for widget in parent.winfo_children():
            widget.destroy()

        visible_rows = rows
        if self.show_only_mistakes.get():
            visible_rows = [row for row in rows if not row["is_correct"]]

        for row in visible_rows:
            if row["is_correct"]:
                status, accent, soft = "Верно", COLORS["green"], COLORS["green_soft"]
            elif row["is_unanswered"]:
                status, accent, soft = "Пропущено", COLORS["amber"], COLORS["amber_soft"]
            elif not row["is_checked"]:
                status, accent, soft = "Не проверено", COLORS["amber"], COLORS["amber_soft"]
            else:
                status, accent, soft = "Ошибка", COLORS["red"], COLORS["red_soft"]

            card = tk.Frame(parent, bg=soft, highlightthickness=1, highlightbackground=COLORS["line"])
            card.pack(fill="x", pady=7, padx=(0, 8))
            inner = tk.Frame(card, bg=soft, padx=14, pady=12)
            inner.pack(fill="x")
            tk.Label(
                inner,
                text=f"{status} • Вопрос #{row['original']} (позиция {row['seq']})",
                bg=soft,
                fg=accent,
                font=("Segoe UI", 11, "bold"),
                anchor="w",
            ).pack(fill="x")
            tk.Label(
                inner,
                text=row["question"]["question"],
                bg=soft,
                fg=COLORS["ink"],
                font=("Segoe UI", 10),
                wraplength=980,
                justify="left",
                anchor="w",
            ).pack(fill="x", pady=(6, 8))
            user_texts = answer_texts(row["question"], row["user"])
            correct_texts = answer_texts(row["question"], row["correct"])
            tk.Label(
                inner,
                text="Ваш ответ: " + ("; ".join(user_texts) if user_texts else "не выбран"),
                bg=soft,
                fg=COLORS["ink"],
                font=("Segoe UI", 10),
                wraplength=980,
                justify="left",
                anchor="w",
            ).pack(fill="x")
            tk.Label(
                inner,
                text="Правильный ответ: " + "; ".join(correct_texts),
                bg=soft,
                fg=COLORS["ink"],
                font=("Segoe UI", 10, "bold"),
                wraplength=980,
                justify="left",
                anchor="w",
            ).pack(fill="x", pady=(4, 0))


if __name__ == "__main__":
    QuizApp().mainloop()
