import random
import tkinter as tk
from tkinter import messagebox, ttk

from .config import ConnectionSettings, load_settings, save_settings
from .database import OracleGateway, SessionUser
from .theme import COLORS, configure_theme

ROLE_NAMES = {
    "USER": "Участник",
    "AUTHOR": "Автор",
    "ADMIN": "Администратор",
}
STATUS_NAMES = {
    "DRAFT": "Черновик",
    "PUBLISHED": "Опубликован",
    "ARCHIVED": "В архиве",
}
ACCESS_NAMES = {
    "PUBLIC": "Публичный",
    "RESTRICTED": "По приглашению",
}
TIMER_MODE_NAMES = {
    "QUIZ": "На весь тест",
    "QUESTION": "На каждый вопрос",
}
SPACING = {
    "xs": 8,
    "sm": 12,
    "md": 16,
    "lg": 24,
}
ACTION_ICONS = {
    "connect": "↗",
    "login": "→",
    "logout": "↩",
    "register": "+",
    "start": "▶",
    "save": "✓",
    "finish": "■",
    "publish": "↑",
    "hide": "↓",
    "delete": "×",
    "grant": "→",
    "reset": "↺",
    "catalog": "☰",
    "history": "◷",
    "studio": "✎",
    "open": "↦",
    "add": "+",
    "clear": "⟲",
    "up": "↑",
    "down": "↓",
    "shuffle": "⇅",
    "author": "✦",
    "user": "•",
    "disable": "⛔",
    "enable": "✓",
}


class QuizApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Oracle Quiz Platform")
        self.geometry("1240x820")
        self.minsize(1060, 700)
        configure_theme(self)

        self.gateway = OracleGateway()
        self.user: SessionUser | None = None
        self.page = ttk.Frame(self, style="App.TFrame", padding=SPACING["lg"])
        self.page.pack(fill="both", expand=True)
        self.active_attempt_id = None
        self.active_questions = []
        self.active_index = 0
        self.active_header = None
        self.remaining_seconds = None
        self.timer_caption = "Осталось времени"
        self.timer_job = None
        self.connected_dsn = None
        self.toast_widget = None
        self.toast_hide_job = None
        self._patch_messageboxes()
        self.show_connection()

    def _patch_messageboxes(self):
        original_info = messagebox.showinfo
        original_warning = messagebox.showwarning

        def toast_info(title, message, *args, **kwargs):
            self.show_toast(message, kind="success")
            return "ok"

        def toast_warning(title, message, *args, **kwargs):
            self.show_toast(message, kind="warning")
            return "ok"

        self._messagebox_original_info = original_info
        self._messagebox_original_warning = original_warning
        messagebox.showinfo = toast_info
        messagebox.showwarning = toast_warning

    def show_toast(self, message: str, kind: str = "info", duration_ms: int = 2400):
        palette = {
            "info": ("#e9f2ff", COLORS["brand"], COLORS["brand_dark"]),
            "success": ("#eaf7ef", "#2f7a41", "#245c32"),
            "warning": ("#fff3e6", "#a8611f", "#834a14"),
        }
        bg, border, fg = palette.get(kind, palette["info"])
        if self.toast_hide_job:
            self.after_cancel(self.toast_hide_job)
            self.toast_hide_job = None
        if self.toast_widget is not None:
            self.toast_widget.destroy()
            self.toast_widget = None

        toast = tk.Frame(self, bg=bg, highlightthickness=1, highlightbackground=border, padx=14, pady=10)
        tk.Label(toast, text=message, bg=bg, fg=fg, font=("Segoe UI", 10), justify="left", wraplength=820).pack(anchor="w")
        toast.place(relx=0.5, rely=1.0, anchor="s", y=26)
        self.toast_widget = toast

        def animate_in(step=0):
            start_y, end_y, total = 26, -22, 6
            y = int(start_y + (end_y - start_y) * (step / total))
            toast.place_configure(y=y)
            if step < total:
                self.after(22, lambda: animate_in(step + 1))

        def hide():
            if self.toast_widget is toast:
                toast.destroy()
                self.toast_widget = None
            self.toast_hide_job = None

        animate_in()
        self.toast_hide_job = self.after(duration_ms, hide)

    def icon_text(self, key: str, text: str) -> str:
        icon = ACTION_ICONS.get(key, "")
        return f"{icon} {text}".strip()

    def tone_for_status(self, status_code: str) -> str:
        if status_code == "DRAFT":
            return "warning"
        if status_code == "PUBLISHED":
            return "success"
        if status_code == "ARCHIVED":
            return "default"
        return "default"

    def tone_for_access(self, access_mode: str) -> str:
        return "brand" if access_mode == "RESTRICTED" else "default"

    def format_attempt_limit(self, attempt_limit) -> str:
        if attempt_limit in (None, "", 0):
            return "Без лимита попыток"
        try:
            value = int(attempt_limit)
        except (TypeError, ValueError):
            return "Без лимита попыток"
        if value <= 0:
            return "Без лимита попыток"
        if value % 10 == 1 and value % 100 != 11:
            suffix = "попытка"
        elif value % 10 in (2, 3, 4) and value % 100 not in (12, 13, 14):
            suffix = "попытки"
        else:
            suffix = "попыток"
        return f"{value} {suffix}"

    def clear_page(self):
        self.cancel_timer()
        self.unbind("<Return>")
        for widget in self.page.winfo_children():
            widget.destroy()

    def set_enter_action(self, action):
        self.unbind("<Return>")
        if action is None:
            return
        self.bind("<Return>", lambda _event: action())

    def panel(self, parent, padding=20):
        outer = tk.Frame(parent, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
        accent = tk.Frame(outer, bg=COLORS["brand"], height=3)
        accent.pack(fill="x")
        inner = ttk.Frame(outer, style="Panel.TFrame", padding=padding)
        inner.pack(fill="both", expand=True)
        return outer, inner

    def heading(self, title, subtitle="", with_navigation=True):
        shell = tk.Frame(self.page, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
        shell.pack(fill="x", pady=(0, 20))
        topbar = tk.Frame(shell, bg=COLORS["brand"], height=40)
        topbar.pack(fill="x")
        tk.Label(
            topbar,
            text="Oracle Quiz LMS",
            bg=COLORS["brand"],
            fg="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=8,
        ).pack(side="left")
        if self.user:
            role_name = ROLE_NAMES.get(self.user.role_code, self.user.role_code)
            tk.Label(
                topbar,
                text=f"{self.user.full_name} · {role_name}",
                bg=COLORS["brand"],
                fg="#ffffff",
                font=("Segoe UI", 9),
                padx=14,
                pady=8,
            ).pack(side="right")

        header = ttk.Frame(shell, style="Panel.TFrame", padding=(16, 14))
        header.pack(fill="x")
        left = ttk.Frame(header, style="Panel.TFrame")
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text=title, style="PageTitle.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(left, text=subtitle, style="Subtitle.TLabel").pack(anchor="w", pady=(5, 0))
        if with_navigation and self.user:
            nav = ttk.Frame(header, style="Panel.TFrame")
            nav.pack(side="right", anchor="n")
            ttk.Button(nav, text=self.icon_text("catalog", "Каталог"), style="Nav.TButton", command=self.show_catalog).pack(side="left", padx=3)
            ttk.Button(nav, text=self.icon_text("history", "Мои результаты"), style="Nav.TButton", command=self.show_history).pack(side="left", padx=3)
            if self.user.role_code in ("ADMIN", "AUTHOR"):
                ttk.Button(nav, text=self.icon_text("studio", "Студия тестов"), style="Nav.TButton", command=self.show_admin).pack(side="left", padx=3)
            ttk.Button(nav, text=self.icon_text("logout", "Выйти"), style="Quiet.TButton", command=self.logout).pack(side="left", padx=(12, 0))

    def add_chip_row(self, parent, chips):
        row = tk.Frame(parent, bg=COLORS["panel"])
        row.pack(anchor="w", pady=(SPACING["xs"], 0))
        for text, tone in chips:
            tone_colors = {
                "default": (COLORS["chip_bg"], COLORS["chip_border"], COLORS["chip_text"]),
                "success": ("#eaf7ef", "#c7e5cf", "#2f7a41"),
                "warning": ("#fff3e6", "#f4d7ba", "#a8611f"),
                "brand": ("#e9f2ff", "#c5daf3", COLORS["brand_dark"]),
            }
            bg, border, fg = tone_colors.get(tone, tone_colors["default"])
            chip = tk.Label(
                row,
                text=text,
                bg=bg,
                fg=fg,
                font=("Segoe UI", 9, "bold"),
                padx=8,
                pady=3,
                highlightthickness=1,
                highlightbackground=border,
            )
            chip.pack(side="left", padx=(0, 8))

    def report_error(self, exc):
        message = str(exc)
        if "ORA-" in message and ":" in message:
            message = message.split(":", 1)[1].strip()
        messagebox.showerror("Операция не выполнена", message)

    def show_connection(self):
        self.clear_page()
        self.heading(
            "Шаг 1. Подключение Oracle",
            "Укажите технические данные схемы. После подключения откроется обычный экран входа пользователей.",
            with_navigation=False,
        )
        settings = load_settings()
        outer, form = self.panel(self.page, padding=28)
        outer.pack(fill="x", padx=(140, 140), pady=(28, 0))
        ttk.Label(form, text="Подключение к базе", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 18))
        ttk.Label(form, text="DSN (host:port/service)", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=6)
        dsn = ttk.Entry(form, width=48)
        dsn.insert(0, settings.dsn)
        dsn.grid(row=1, column=1, sticky="ew", padx=(18, 0), pady=6)
        ttk.Label(form, text="Пользователь схемы", style="Card.TLabel").grid(row=2, column=0, sticky="w", pady=6)
        schema_user = ttk.Entry(form, width=48)
        schema_user.insert(0, settings.schema_user)
        schema_user.grid(row=2, column=1, sticky="ew", padx=(18, 0), pady=6)
        ttk.Label(form, text="Пароль схемы", style="Card.TLabel").grid(row=3, column=0, sticky="w", pady=6)
        schema_password = ttk.Entry(form, show="*", width=48)
        schema_password.grid(row=3, column=1, sticky="ew", padx=(18, 0), pady=6)
        form.columnconfigure(1, weight=1)

        note = (
            "Эти данные используются для соединения с Oracle. "
            "В Docker-конфигурации оставьте значения по умолчанию и укажите пароль QuizSchema2026."
        )
        ttk.Label(form, text=note, style="Muted.TLabel", wraplength=690, justify="left").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(15, 18)
        )

        def connect():
            try:
                self.gateway.connect(dsn.get().strip(), schema_user.get().strip(), schema_password.get())
                self.connected_dsn = dsn.get().strip()
                save_settings(ConnectionSettings(dsn.get().strip(), schema_user.get().strip()))
                self.show_login_page()
            except Exception as exc:
                self.report_error(exc)

        ttk.Button(form, text=self.icon_text("connect", "Подключиться"), style="Primary.TButton", command=connect).grid(row=5, column=0, columnspan=2, sticky="w")
        self.set_enter_action(connect)
        dsn.focus_set()

    def show_auth(self):
        self.show_login_page()

    def auth_panel(self, title, subtitle):
        self.clear_page()
        connection_note = self.connected_dsn or load_settings().dsn
        self.heading(
            title,
            f"{subtitle} Подключение к БД: {connection_note}",
            with_navigation=False,
        )
        outer, form = self.panel(self.page, padding=28)
        outer.pack(fill="x", padx=(250, 250), pady=(20, 0))
        return form

    def show_login_page(self, prefill_login=""):
        form = self.auth_panel("Вход", "Шаг 2. Войдите под логином и паролем.")
        ttk.Label(form, text="Логин", style="Card.TLabel").pack(anchor="w")
        login_value = ttk.Entry(form)
        login_value.pack(fill="x", pady=(5, 14))
        if prefill_login:
            login_value.insert(0, prefill_login)
        ttk.Label(form, text="Пароль", style="Card.TLabel").pack(anchor="w")
        password_value = ttk.Entry(form, show="*")
        password_value.pack(fill="x", pady=(5, 18))

        def authenticate(_event=None):
            if not login_value.get().strip() or not password_value.get():
                messagebox.showwarning("Вход", "Введите логин и пароль.")
                return
            try:
                self.user = self.gateway.authenticate(login_value.get().strip(), password_value.get())
                self.show_catalog()
            except Exception as exc:
                self.report_error(exc)

        ttk.Button(form, text=self.icon_text("login", "Войти"), style="Primary.TButton", command=authenticate).pack(anchor="w")
        ttk.Label(
            form,
            text="Демонстрационный администратор\nadmin / Admin123!",
            style="Muted.TLabel",
            justify="left",
        ).pack(anchor="w", pady=(18, 10))
        actions = ttk.Frame(form, style="Panel.TFrame")
        actions.pack(fill="x")
        ttk.Button(actions, text=self.icon_text("register", "Зарегистрироваться"), style="Quiet.TButton", command=self.show_register_page).pack(side="left")
        ttk.Button(actions, text=self.icon_text("connect", "Изменить подключение Oracle"), style="Quiet.TButton", command=self.show_connection).pack(side="right")
        login_value.focus_set()
        self.set_enter_action(authenticate)

    def show_register_page(self):
        form = self.auth_panel("Регистрация", "Создайте учетную запись участника.")
        ttk.Label(form, text="Имя", style="Card.TLabel").pack(anchor="w")
        full_name = ttk.Entry(form)
        full_name.pack(fill="x", pady=(5, 12))
        ttk.Label(form, text="Логин", style="Card.TLabel").pack(anchor="w")
        new_login = ttk.Entry(form)
        new_login.pack(fill="x", pady=(5, 12))
        ttk.Label(form, text="Пароль (от 6 символов)", style="Card.TLabel").pack(anchor="w")
        new_password = ttk.Entry(form, show="*")
        new_password.pack(fill="x", pady=(5, 12))
        ttk.Label(form, text="Повторите пароль", style="Card.TLabel").pack(anchor="w")
        confirm_password = ttk.Entry(form, show="*")
        confirm_password.pack(fill="x", pady=(5, 18))

        def register_user(_event=None):
            if not full_name.get().strip() or not new_login.get().strip() or not new_password.get():
                messagebox.showwarning("Регистрация", "Заполните имя, логин и пароль.")
                return
            if new_password.get() != confirm_password.get():
                messagebox.showwarning("Регистрация", "Пароли не совпадают.")
                return
            try:
                self.gateway.register(new_login.get().strip(), new_password.get(), full_name.get().strip())
                messagebox.showinfo("Регистрация", "Учетная запись создана. Теперь войдите с вашим паролем.")
                self.show_login_page(new_login.get().strip())
            except Exception as exc:
                self.report_error(exc)

        ttk.Button(form, text=self.icon_text("register", "Создать учетную запись"), style="Primary.TButton", command=register_user).pack(anchor="w")
        actions = ttk.Frame(form, style="Panel.TFrame")
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text=self.icon_text("login", "У меня уже есть аккаунт"), style="Quiet.TButton", command=self.show_login_page).pack(side="left")
        ttk.Button(actions, text=self.icon_text("connect", "Изменить подключение Oracle"), style="Quiet.TButton", command=self.show_connection).pack(side="right")
        full_name.focus_set()
        self.set_enter_action(register_user)

    def abandon_active_attempt(self):
        if self.active_attempt_id is None:
            return
        attempt_id = self.active_attempt_id
        self.active_attempt_id = None
        self.active_questions = []
        self.active_index = 0
        self.active_header = None
        self.cancel_timer()
        try:
            self.gateway.abandon_attempt(attempt_id)
        except Exception:
            # Ignore transport errors during app shutdown/logout.
            pass

    def logout(self):
        self.abandon_active_attempt()
        self.user = None
        self.show_login_page()

    def show_catalog(self):
        self.clear_page()
        role_name = ROLE_NAMES.get(self.user.role_code, self.user.role_code)
        self.heading(
            "Доступные тесты",
            f"{self.user.full_name}  |  {role_name}. Выберите тест и начните попытку.",
        )
        controls_outer, controls = self.panel(self.page, padding=SPACING["sm"])
        controls_outer.pack(fill="x", pady=(0, SPACING["sm"]))
        ttk.Label(controls, text="Фильтр по тематике", style="Card.TLabel").pack(side="left", padx=(0, 12))
        topics = self.gateway.topics()
        labels = ["Все тематики"] + [topic["title"] for topic in topics]
        topic_by_label = {topic["title"]: topic["topic_id"] for topic in topics}
        selected_topic = ttk.Combobox(controls, state="readonly", values=labels, width=38)
        selected_topic.set(labels[0])
        selected_topic.pack(side="left")

        outer, content = self.panel(self.page, padding=SPACING["md"])
        outer.pack(fill="both", expand=True)
        columns = ("topic", "quiz", "questions", "duration", "points", "author")
        tree = ttk.Treeview(content, columns=columns, show="headings", selectmode="browse")
        headers = {
            "topic": ("Тематика", 210),
            "quiz": ("Тест", 300),
            "questions": ("Вопросов", 90),
            "duration": ("Минут", 75),
            "points": ("Баллов", 75),
            "author": ("Автор", 190),
        }
        for name, (title, width) in headers.items():
            tree.heading(name, text=title)
            tree.column(name, width=width, anchor="w" if name in ("topic", "quiz", "author") else "center")
        tree.pack(fill="both", expand=True)
        rows_by_id = {}

        detail_outer, detail = self.panel(self.page, padding=SPACING["md"])
        detail_outer.pack(fill="x", pady=(SPACING["sm"], 0))
        selected_title = ttk.Label(detail, text="Выберите тест из списка", style="CardTitle.TLabel")
        selected_title.pack(anchor="w")
        selected_info = ttk.Label(detail, text="Здесь появятся описание, время и количество вопросов.", style="Muted.TLabel", wraplength=840, justify="left")
        selected_info.pack(anchor="w", pady=(6, 0))
        chips_anchor = tk.Frame(detail, bg=COLORS["panel"])
        chips_anchor.pack(anchor="w", pady=(2, 0))

        footer = ttk.Frame(detail, style="Panel.TFrame")
        footer.pack(side="right", anchor="e")

        def load_catalog(_event=None):
            for item in tree.get_children():
                tree.delete(item)
            rows_by_id.clear()
            topic_id = topic_by_label.get(selected_topic.get())
            try:
                rows = self.gateway.catalog(self.user.user_id, topic_id)
            except Exception as exc:
                self.report_error(exc)
                return
            for row in rows:
                tree.insert(
                    "", "end", iid=str(row["quiz_id"]),
                    values=(row["topic_title"], row["quiz_title"], row["question_count"], row["duration_minutes"], row["max_points"], row["author_name"]),
                )
                rows_by_id[str(row["quiz_id"])] = row
            if rows:
                tree.selection_set(str(rows[0]["quiz_id"]))
                show_selected()
            else:
                selected_title.configure(text="По выбранной тематике тестов нет")
                selected_info.configure(text="Администратор или автор может опубликовать новый тест в студии.")
                for child in chips_anchor.winfo_children():
                    child.destroy()

        selected_topic.bind("<<ComboboxSelected>>", load_catalog)

        def start_selected():
            chosen = tree.selection()
            if not chosen:
                messagebox.showwarning("Тест", "Выберите тест из каталога.")
                return
            try:
                attempt_id = self.gateway.start_attempt(self.user.user_id, int(chosen[0]))
                self.start_quiz_screen(attempt_id)
            except Exception as exc:
                self.report_error(exc)

        def show_selected(_event=None):
            chosen = tree.selection()
            if not chosen or chosen[0] not in rows_by_id:
                return
            row = rows_by_id[chosen[0]]
            selected_title.configure(text=row["quiz_title"])
            description = row["description"] or "Описание не указано."
            timer_mode = row.get("timer_mode") or "QUIZ"
            attempt_mode = self.format_attempt_limit(row.get("attempt_limit"))
            timing = (
                f"{row['duration_minutes']} мин. на весь тест"
                if timer_mode == "QUIZ"
                else f"{row['duration_minutes']} мин. на каждый вопрос"
            )
            selected_info.configure(
                text=f"{description}\n{row['question_count']} вопросов  |  {timing}  |  {attempt_mode}  |  {row['max_points']} баллов  |  Автор: {row['author_name']}"
            )
            for child in chips_anchor.winfo_children():
                child.destroy()
            self.add_chip_row(
                chips_anchor,
                [
                    (STATUS_NAMES.get(row.get("status"), "Опубликован"), self.tone_for_status(row.get("status"))),
                    (ACCESS_NAMES.get(row.get("access_mode"), "Публичный"), self.tone_for_access(row.get("access_mode"))),
                    (TIMER_MODE_NAMES.get(timer_mode, timer_mode), "warning"),
                    (attempt_mode, "default"),
                ],
            )

        tree.bind("<<TreeviewSelect>>", show_selected)
        tree.bind("<Double-1>", lambda _event: start_selected())
        ttk.Button(footer, text=self.icon_text("start", "Начать выбранный тест"), style="Primary.TButton", command=start_selected).pack(side="right")
        self.set_enter_action(start_selected)
        load_catalog()

    def start_quiz_screen(self, attempt_id):
        self.active_attempt_id = attempt_id
        try:
            self.active_questions = self.gateway.attempt_questions(attempt_id)
        except Exception as exc:
            self.report_error(exc)
            self.show_catalog()
            return
        self.active_index = 0
        if not self.refresh_timer_state():
            return
        self.show_question()

    def refresh_timer_state(self):
        if self.active_attempt_id is None:
            return False
        try:
            self.active_header = self.gateway.attempt_header(self.active_attempt_id)
        except Exception as exc:
            self.report_error(exc)
            self.show_catalog()
            return False

        timer_mode = self.active_header.get("timer_mode") or "QUIZ"
        if timer_mode == "QUESTION":
            self.timer_caption = "На вопрос"
            self.remaining_seconds = int(self.active_header.get("question_remaining_seconds") or 0)
        else:
            self.timer_caption = "На тест"
            self.remaining_seconds = int(self.active_header.get("remaining_seconds") or 0)
        return True

    def show_question(self):
        self.clear_page()
        if self.active_index >= len(self.active_questions):
            self.finish_active_attempt()
            return
        if not self.refresh_timer_state():
            return

        question = self.active_questions[self.active_index]
        total = len(self.active_questions)
        timer_mode = self.active_header.get("timer_mode") or "QUIZ"
        timer_mode_name = TIMER_MODE_NAMES.get(timer_mode, timer_mode)
        self.heading(
            self.active_header["quiz_title"],
            f"Вопрос {self.active_index + 1} из {total} | {question['category_title']} | {question['difficulty_name']} | {question['points']} балл(а)",
            with_navigation=False,
        )
        top_outer, top = self.panel(self.page, padding=14)
        top_outer.pack(fill="x", pady=(0, 14))
        ttk.Label(
            top,
            text=f"Шаг {self.active_index + 1} из {total}. Режим времени: {timer_mode_name}",
            style="Card.TLabel",
        ).pack(anchor="w")
        self.add_chip_row(
            top,
            [
                (question["category_title"], "default"),
                (question["difficulty_name"], "warning"),
                (f"{question['points']} балл(а)", "brand"),
                (timer_mode_name, "default"),
            ],
        )
        progress = ttk.Progressbar(top, maximum=total, value=self.active_index + 1)
        progress.pack(fill="x", pady=(SPACING["sm"], 0))
        timer_label = tk.Label(top, bg=COLORS["panel"], fg=COLORS["gold"], font=("Segoe UI", 11, "bold"))
        timer_label.pack(anchor="e", pady=(SPACING["xs"], 0))
        self.update_timer(timer_label)

        outer, card = self.panel(self.page, padding=24)
        outer.pack(fill="both", expand=True)
        ttk.Label(card, text=question["question_text"], style="CardTitle.TLabel", wraplength=1040, justify="left").pack(anchor="w", pady=(0, 20))
        ttk.Label(
            card,
            text="Ответ сохраняется сразу. После перехода к следующему вопросу вернуться назад нельзя.",
            style="Muted.TLabel",
            wraplength=980,
            justify="left",
        ).pack(anchor="w", pady=(0, 14))
        type_code = question["type_code"]
        text_entry = None
        ordering_state = []
        selected_state = {"single": None, "multi": set()}

        def build_choice_cards(options, allow_multi=False):
            shell = tk.Frame(card, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground=COLORS["line"])
            shell.pack(fill="x", pady=(0, SPACING["xs"]))
            body = tk.Frame(shell, bg=COLORS["panel_alt"])
            body.pack(fill="x", padx=SPACING["xs"], pady=SPACING["xs"])

            def refresh():
                for child in body.winfo_children():
                    child.destroy()
                for idx, option in enumerate(options, 1):
                    option_id = option["option_id"]
                    is_selected = option_id in selected_state["multi"] if allow_multi else selected_state["single"] == option_id
                    row_bg = COLORS["blue_soft"] if is_selected else "#ffffff"
                    border = COLORS["brand"] if is_selected else COLORS["line"]
                    marker_bg = COLORS["brand"] if is_selected else "#ffffff"
                    marker_fg = "#ffffff" if is_selected else COLORS["muted"]
                    marker_text = "✓" if allow_multi else "●"
                    if not is_selected:
                        marker_text = "○" if not allow_multi else "+"

                    row = tk.Frame(
                        body,
                        bg=row_bg,
                        highlightthickness=1,
                        highlightbackground=border,
                        padx=SPACING["sm"],
                        pady=SPACING["xs"],
                        cursor="hand2",
                    )
                    row.pack(fill="x", pady=4)
                    marker = tk.Label(
                        row,
                        text=marker_text,
                        bg=marker_bg,
                        fg=marker_fg,
                        width=2,
                        font=("Segoe UI", 10, "bold"),
                        padx=4,
                    )
                    marker.pack(side="left")
                    number = tk.Label(
                        row,
                        text=str(idx),
                        bg=row_bg,
                        fg=COLORS["muted"],
                        font=("Segoe UI", 9, "bold"),
                        padx=SPACING["xs"],
                    )
                    number.pack(side="left")
                    caption = tk.Label(
                        row,
                        text=option["option_text"],
                        bg=row_bg,
                        fg=COLORS["ink"],
                        font=("Segoe UI", 10),
                        anchor="w",
                        justify="left",
                    )
                    caption.pack(side="left", fill="x", expand=True)

                    def on_pick(_event=None, picked_id=option_id):
                        if allow_multi:
                            if picked_id in selected_state["multi"]:
                                selected_state["multi"].remove(picked_id)
                            else:
                                selected_state["multi"].add(picked_id)
                        else:
                            selected_state["single"] = picked_id
                        refresh()

                    def build_hover_handlers(
                        row_widget=row,
                        marker_widget=marker,
                        number_widget=number,
                        caption_widget=caption,
                        selected=is_selected,
                        selected_bg=row_bg,
                        selected_border=border,
                        selected_marker_bg=marker_bg,
                        selected_marker_fg=marker_fg,
                    ):
                        def repaint(hovered=False):
                            local_bg = selected_bg if selected else (COLORS["hover_soft"] if hovered else "#ffffff")
                            local_border = selected_border if selected else ("#c8d9ec" if hovered else COLORS["line"])
                            local_marker_bg = selected_marker_bg if selected else ("#f2f6fb" if hovered else "#ffffff")
                            row_widget.configure(bg=local_bg, highlightbackground=local_border)
                            marker_widget.configure(bg=local_marker_bg, fg=selected_marker_fg)
                            number_widget.configure(bg=local_bg)
                            caption_widget.configure(bg=local_bg)

                        def on_enter(_event=None):
                            repaint(hovered=True)

                        def on_leave(_event=None):
                            repaint(hovered=False)

                        return repaint, on_enter, on_leave

                    repaint, on_enter, on_leave = build_hover_handlers()

                    for widget in (row, marker, number, caption):
                        widget.bind("<Button-1>", on_pick)
                        widget.bind("<Enter>", on_enter)
                        widget.bind("<Leave>", on_leave)

                    repaint(hovered=False)

            refresh()

        if type_code in ("SINGLE_CHOICE", "BOOLEAN", "MULTIPLE_CHOICE"):
            options = self.gateway.question_options(question["question_id"])
            if type_code == "MULTIPLE_CHOICE":
                ttk.Label(card, text="Можно выбрать несколько вариантов.", style="Muted.TLabel").pack(anchor="w", pady=(0, 8))
                build_choice_cards(options, allow_multi=True)
            else:
                build_choice_cards(options, allow_multi=False)
        elif type_code == "ORDERING":
            options = self.gateway.question_options(question["question_id"])
            if len(options) < 2:
                ttk.Label(card, text="Для вопроса этого типа нужно минимум два элемента последовательности.", style="Muted.TLabel").pack(anchor="w", pady=(0, 8))
            else:
                ttk.Label(card, text="Расположите элементы в правильном порядке.", style="Card.TLabel").pack(anchor="w", pady=(0, 3))
                ttk.Label(
                    card,
                    text="Перетаскивайте элементы мышью или используйте кнопки «Вверх/Вниз».",
                    style="Muted.TLabel",
                ).pack(anchor="w", pady=(0, SPACING["xs"]))
                wrapper = ttk.Frame(card, style="Panel.TFrame")
                wrapper.pack(fill="x", pady=(0, SPACING["xs"]))
                list_shell = tk.Frame(wrapper, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground=COLORS["line"])
                list_shell.pack(side="left", fill="both", expand=True)
                row_height = 48
                max_rows = min(max(len(options), 3), 7)
                list_canvas = tk.Canvas(
                    list_shell,
                    bg=COLORS["panel_alt"],
                    highlightthickness=0,
                    bd=0,
                    height=max_rows * row_height,
                    cursor="hand2",
                )
                list_canvas.pack(side="left", fill="both", expand=True)
                scroll = ttk.Scrollbar(list_shell, orient="vertical", command=list_canvas.yview)
                scroll.pack(side="left", fill="y")
                list_canvas.configure(yscrollcommand=scroll.set)
                rows_holder = tk.Frame(list_canvas, bg=COLORS["panel_alt"])
                holder_window = list_canvas.create_window((0, 0), window=rows_holder, anchor="nw")
                controls = ttk.Frame(wrapper, style="Panel.TFrame")
                controls.pack(side="left", anchor="n", padx=(SPACING["sm"], 0))
                ordering_state = [{"option_id": row["option_id"], "option_text": row["option_text"]} for row in options]
                baseline = [row["option_id"] for row in ordering_state]
                random.shuffle(ordering_state)
                if len(ordering_state) > 1 and [row["option_id"] for row in ordering_state] == baseline:
                    random.shuffle(ordering_state)
                drag_state = {"index": None}
                selected_order = {"index": 0}

                def on_holder_configure(_event=None):
                    list_canvas.configure(scrollregion=list_canvas.bbox("all"))

                def on_canvas_configure(event):
                    list_canvas.itemconfigure(holder_window, width=event.width)

                def clamp_index(index):
                    if not ordering_state:
                        return 0
                    return max(0, min(index, len(ordering_state) - 1))

                def resolve_order_row(widget):
                    current = widget
                    while current is not None and current is not rows_holder:
                        if getattr(current, "_ordering_row", False):
                            return current
                        current = getattr(current, "master", None)
                    return None

                def refresh_ordering_cards():
                    selected_order["index"] = clamp_index(selected_order["index"])
                    for child in rows_holder.winfo_children():
                        child.destroy()
                    for idx, row in enumerate(ordering_state):
                        active = idx == selected_order["index"]
                        row_bg = COLORS["blue_soft"] if active else "#ffffff"
                        border = COLORS["brand"] if active else COLORS["line"]
                        row_frame = tk.Frame(
                            rows_holder,
                            bg=row_bg,
                            highlightthickness=1,
                            highlightbackground=border,
                            padx=SPACING["sm"],
                            pady=SPACING["xs"],
                            cursor="hand2",
                        )
                        row_frame._ordering_row = True
                        row_frame._ordering_index = idx
                        row_frame.pack(fill="x", padx=8, pady=4)
                        badge = tk.Label(
                            row_frame,
                            text=str(idx + 1),
                            bg=COLORS["brand"],
                            fg="#ffffff",
                            width=2,
                            font=("Segoe UI", 9, "bold"),
                            padx=4,
                        )
                        badge.pack(side="left")
                        handle = tk.Label(
                            row_frame,
                            text="≡",
                            bg=row_bg,
                            fg=COLORS["muted"],
                            font=("Segoe UI", 10, "bold"),
                            padx=SPACING["xs"],
                        )
                        handle.pack(side="left")
                        caption = tk.Label(
                            row_frame,
                            text=row["option_text"],
                            bg=row_bg,
                            fg=COLORS["ink"],
                            font=("Segoe UI", 10),
                            anchor="w",
                            justify="left",
                        )
                        caption.pack(side="left", fill="x", expand=True)

                        def build_hover_handlers(
                            row_widget=row_frame,
                            handle_widget=handle,
                            caption_widget=caption,
                            is_active=active,
                            active_bg=row_bg,
                            active_border=border,
                        ):
                            def repaint(hovered=False):
                                local_bg = active_bg if is_active else (COLORS["hover_soft"] if hovered else "#ffffff")
                                local_border = active_border if is_active else ("#c8d9ec" if hovered else COLORS["line"])
                                row_widget.configure(bg=local_bg, highlightbackground=local_border)
                                handle_widget.configure(bg=local_bg)
                                caption_widget.configure(bg=local_bg)

                            def on_enter(_event=None):
                                repaint(hovered=True)

                            def on_leave(_event=None):
                                repaint(hovered=False)

                            return repaint, on_enter, on_leave

                        repaint, on_enter, on_leave = build_hover_handlers()

                        for widget in (row_frame, badge, handle, caption):
                            widget.bind("<ButtonPress-1>", on_drag_start)
                            widget.bind("<B1-Motion>", on_drag_motion)
                            widget.bind("<ButtonRelease-1>", on_drag_end)
                            widget.bind("<Enter>", on_enter)
                            widget.bind("<Leave>", on_leave)
                        repaint(hovered=False)
                    on_holder_configure()

                def find_target_index(y_root):
                    rows = rows_holder.winfo_children()
                    if not rows:
                        return 0
                    for idx, row_widget in enumerate(rows):
                        midpoint = row_widget.winfo_rooty() + row_widget.winfo_height() / 2
                        if y_root < midpoint:
                            return idx
                    return len(rows) - 1

                def move_ordering(step):
                    if not ordering_state:
                        return
                    source = clamp_index(selected_order["index"])
                    target = source + step
                    if target < 0 or target >= len(ordering_state):
                        return
                    ordering_state[source], ordering_state[target] = ordering_state[target], ordering_state[source]
                    selected_order["index"] = target
                    refresh_ordering_cards()

                def on_drag_start(event):
                    row_widget = resolve_order_row(event.widget)
                    if row_widget is None:
                        return
                    index = clamp_index(row_widget._ordering_index)
                    selected_order["index"] = index
                    drag_state["index"] = index
                    refresh_ordering_cards()

                def on_drag_motion(event):
                    if drag_state["index"] is None or not ordering_state:
                        return
                    source = clamp_index(drag_state["index"])
                    target = clamp_index(find_target_index(event.y_root))
                    if target == source:
                        return
                    moved = ordering_state.pop(source)
                    ordering_state.insert(target, moved)
                    drag_state["index"] = target
                    selected_order["index"] = target
                    refresh_ordering_cards()

                def on_drag_end(_event):
                    drag_state["index"] = None
                    refresh_ordering_cards()

                def reshuffle_ordering():
                    if len(ordering_state) < 2:
                        return
                    random.shuffle(ordering_state)
                    if [row["option_id"] for row in ordering_state] == baseline:
                        random.shuffle(ordering_state)
                    selected_order["index"] = 0
                    refresh_ordering_cards()

                ttk.Button(controls, text=self.icon_text("up", "Вверх"), style="Quiet.TButton", command=lambda: move_ordering(-1)).pack(fill="x")
                ttk.Button(controls, text=self.icon_text("down", "Вниз"), style="Quiet.TButton", command=lambda: move_ordering(1)).pack(fill="x", pady=(SPACING["xs"], 0))
                ttk.Button(controls, text=self.icon_text("shuffle", "Перемешать"), style="Quiet.TButton", command=reshuffle_ordering).pack(fill="x", pady=(SPACING["xs"], 0))
                rows_holder.bind("<Configure>", on_holder_configure)
                list_canvas.bind("<Configure>", on_canvas_configure)
                refresh_ordering_cards()
        else:
            prompt = "Введите ответ"
            ttk.Label(card, text=prompt, style="Card.TLabel").pack(anchor="w", pady=(0, 7))
            input_shell = tk.Frame(card, bg=COLORS["panel_alt"], highlightthickness=1, highlightbackground=COLORS["line"])
            input_shell.pack(fill="x")
            if type_code == "TEXT":
                text_entry = tk.Text(
                    input_shell,
                    height=4,
                    wrap="word",
                    bg="#ffffff",
                    fg=COLORS["ink"],
                    relief="flat",
                    font=("Segoe UI", 10),
                    highlightthickness=0,
                )
                text_entry.pack(fill="x", padx=SPACING["xs"], pady=SPACING["xs"])
            else:
                text_entry = ttk.Entry(input_shell, width=75)
                text_entry.pack(fill="x", padx=SPACING["xs"], pady=SPACING["xs"])

        actions = ttk.Frame(card, style="Panel.TFrame")
        actions.pack(fill="x", side="bottom", pady=(SPACING["lg"], 0))

        def submit_and_continue():
            selected_ids = ""
            answer_text = ""
            if type_code == "MULTIPLE_CHOICE":
                selected = [str(option_id) for option_id in sorted(selected_state["multi"])]
                selected_ids = ",".join(selected)
            elif type_code in ("SINGLE_CHOICE", "BOOLEAN"):
                if selected_state["single"] is not None:
                    selected_ids = str(selected_state["single"])
            elif type_code == "ORDERING":
                selected_ids = ",".join(str(row["option_id"]) for row in ordering_state)
            else:
                if isinstance(text_entry, tk.Text):
                    answer_text = text_entry.get("1.0", "end").strip()
                else:
                    answer_text = text_entry.get().strip() if text_entry is not None else ""
            if not selected_ids and not answer_text:
                messagebox.showwarning("Ответ", "Введите или выберите ответ перед продолжением.")
                return
            try:
                self.gateway.submit_answer(self.active_attempt_id, question["question_id"], selected_ids, answer_text)
                self.active_index += 1
                self.show_question()
            except Exception as exc:
                raw = str(exc)
                if "ORA-20203" in raw or "-20203" in raw:
                    if (self.active_header or {}).get("timer_mode") == "QUESTION":
                        self.handle_question_timeout()
                    else:
                        messagebox.showinfo("Время", "Лимит времени истек. Попытка будет завершена.")
                        self.finish_active_attempt()
                    return
                self.report_error(exc)

        def finish_by_user():
            if messagebox.askyesno("Завершить тест", "Завершить попытку сейчас? Ответы уже сохраненные останутся."):
                self.finish_active_attempt()

        next_text = "Завершить и показать результат" if self.active_index + 1 == total else "Сохранить ответ и дальше"
        next_key = "finish" if self.active_index + 1 == total else "save"
        ttk.Button(actions, text=self.icon_text(next_key, next_text), style="Primary.TButton", command=submit_and_continue).pack(side="right")
        ttk.Button(actions, text=self.icon_text("finish", "Завершить тест"), style="Quiet.TButton", command=finish_by_user).pack(side="right", padx=(0, SPACING["xs"]))
        if text_entry is not None:
            text_entry.focus_set()
        self.set_enter_action(submit_and_continue)

    def update_timer(self, label):
        if self.remaining_seconds is None:
            return
        seconds = max(0, self.remaining_seconds)
        minutes, remainder = divmod(seconds, 60)
        label.configure(text=f"{self.timer_caption}: {minutes:02d}:{remainder:02d}")
        if seconds <= 0:
            if (self.active_header or {}).get("timer_mode") == "QUESTION":
                self.handle_question_timeout()
            else:
                messagebox.showinfo("Время", "Время теста истекло. Попытка будет завершена.")
                self.finish_active_attempt()
            return
        self.remaining_seconds -= 1
        self.timer_job = self.after(1000, lambda: self.update_timer(label))

    def handle_question_timeout(self):
        if self.active_attempt_id is None:
            return
        try:
            self.gateway.expire_question(self.active_attempt_id)
        except Exception as exc:
            self.report_error(exc)
            self.finish_active_attempt()
            return
        self.active_index += 1
        if self.active_index >= len(self.active_questions):
            self.finish_active_attempt()
        else:
            self.show_question()

    def cancel_timer(self):
        if self.timer_job:
            self.after_cancel(self.timer_job)
            self.timer_job = None

    def finish_active_attempt(self):
        self.cancel_timer()
        if self.active_attempt_id is None:
            return
        attempt_id = self.active_attempt_id
        try:
            self.gateway.finish_attempt(attempt_id)
        except Exception as exc:
            self.report_error(exc)
            return
        self.active_attempt_id = None
        self.remaining_seconds = None
        self.timer_caption = "Осталось времени"
        self.show_result(attempt_id)

    def show_result(self, attempt_id):
        self.clear_page()
        try:
            result = self.gateway.attempt_result(attempt_id)
            header = self.gateway.attempt_header(attempt_id)
            details = self.gateway.attempt_details(attempt_id)
        except Exception as exc:
            self.report_error(exc)
            self.show_history()
            return
        self.heading("Результат попытки", f"{result['topic_title']} | {result['quiz_title']}")
        summary_outer, summary = self.panel(self.page, padding=18)
        summary_outer.pack(fill="x", pady=(0, 14))
        result_tone = "success" if result["status"] == "FINISHED" else "warning" if result["status"] == "EXPIRED" else "default"
        feedback_name = "Пояснения включены" if int(header["show_feedback"]) == 1 else "Пояснения скрыты"
        timer_mode_name = TIMER_MODE_NAMES.get(header.get("timer_mode") or "QUIZ", "На весь тест")
        self.add_chip_row(
            summary,
            [
                (result["status"], result_tone),
                (feedback_name, "brand"),
                (timer_mode_name, "default"),
            ],
        )
        cells = [
            ("Итог", f"{result['score_percent'] or 0}%"),
            ("Баллы", f"{result['awarded_points'] or 0} / {result['max_points'] or 0}"),
            ("Верно", f"{result['correct_count']} / {result['question_count']}"),
            ("Статус", result["status"]),
        ]
        stats_grid = ttk.Frame(summary, style="Panel.TFrame")
        stats_grid.pack(fill="x", pady=(SPACING["sm"], 0))
        for index, (title, value) in enumerate(cells):
            frame = ttk.Frame(stats_grid, style="Panel.TFrame")
            frame.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 18, 0))
            ttk.Label(frame, text=title, style="Muted.TLabel").pack(anchor="w")
            ttk.Label(frame, text=str(value), style="CardTitle.TLabel").pack(anchor="w", pady=(5, 0))
            stats_grid.columnconfigure(index, weight=1)

        outer, body = self.panel(self.page, padding=15)
        outer.pack(fill="both", expand=True)
        show_feedback = int(header["show_feedback"]) == 1
        columns = ("number", "status", "question", "given", "correct", "explanation")
        tree = ttk.Treeview(body, columns=columns, show="headings")
        for name, title, width in (
            ("number", "#", 45),
            ("status", "Результат", 100),
            ("question", "Вопрос", 300),
            ("given", "Ваш ответ", 200),
            ("correct", "Правильный ответ", 220),
            ("explanation", "Пояснение автора", 320),
        ):
            tree.heading(name, text=title)
            tree.column(name, width=width)
        tree.pack(fill="both", expand=True)
        for row in details:
            status = "Верно" if row["is_correct"] == 1 else "Ошибка" if row["is_correct"] == 0 else "Пропущено"
            correct = (row["correct_answer"] or "-") if show_feedback else "Скрыто настройками теста"
            explanation = (
                row["explanation"] or "Пояснение не добавлено автором."
            ) if show_feedback else "Скрыто настройками теста"
            tree.insert(
                "",
                "end",
                values=(row["display_order"], status, row["question_text"], row["given_answer"] or "-", correct, explanation),
            )

    def show_history(self):
        self.clear_page()
        self.heading("История попыток", "Результаты рассчитываются и хранятся в Oracle.")
        outer, content = self.panel(self.page, padding=15)
        outer.pack(fill="both", expand=True)
        columns = ("topic", "quiz", "date", "status", "score", "correct")
        tree = ttk.Treeview(content, columns=columns, show="headings", selectmode="browse")
        for name, title, width in (
            ("topic", "Тематика", 210), ("quiz", "Тест", 310), ("date", "Начало", 175),
            ("status", "Статус", 110), ("score", "%", 75), ("correct", "Верно", 95),
        ):
            tree.heading(name, text=title)
            tree.column(name, width=width)
        tree.pack(fill="both", expand=True)
        for result in self.gateway.history(self.user.user_id):
            tree.insert(
                "", "end", iid=str(result["attempt_id"]),
                values=(result["topic_title"], result["quiz_title"], result["started_at"], result["status"], result["score_percent"] or "-", f"{result['correct_count']}/{result['question_count']}"),
            )
        ttk.Button(
            self.page, text=self.icon_text("open", "Открыть результат"), style="Primary.TButton",
            command=lambda: self.show_result(int(tree.selection()[0])) if tree.selection() else messagebox.showwarning("История", "Выберите попытку."),
        ).pack(anchor="e", pady=(SPACING["sm"], 0))

    def show_admin(self, selected_tab=None):
        self.clear_page()
        role_name = ROLE_NAMES.get(self.user.role_code, self.user.role_code)
        self.heading("Студия тестов", f"{role_name}: материалы, вопросы, публикация и результаты в одном рабочем пространстве.")
        notebook = ttk.Notebook(self.page)
        notebook.pack(fill="both", expand=True)
        self.build_admin_dictionaries(notebook)
        self.build_admin_quiz_editor(notebook)
        self.build_admin_question_editor(notebook)
        self.build_admin_publication(notebook)
        self.build_admin_statistics(notebook)
        if self.user.role_code == "ADMIN":
            self.build_admin_progress(notebook)
            self.build_admin_users(notebook)
        if selected_tab:
            for tab_id in notebook.tabs():
                if notebook.tab(tab_id, "text") == selected_tab:
                    notebook.select(tab_id)
                    break

    def build_admin_dictionaries(self, notebook):
        tab = ttk.Frame(notebook, style="App.TFrame", padding=16)
        notebook.add(tab, text="Материалы")
        topic_outer, topic = self.panel(tab, padding=18)
        topic_outer.pack(side="left", fill="both", expand=True, padx=(0, 8))
        category_outer, category = self.panel(tab, padding=18)
        category_outer.pack(side="left", fill="both", expand=True, padx=(8, 0))
        ttk.Label(topic, text="Тематики", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(topic, text="Области знаний, в которых находятся тесты.", style="Muted.TLabel").pack(anchor="w", pady=(3, 14))
        ttk.Label(topic, text="Название", style="Muted.TLabel").pack(anchor="w")
        topic_title = ttk.Entry(topic)
        topic_title.pack(fill="x", pady=(3, 9))
        ttk.Label(topic, text="Описание", style="Muted.TLabel").pack(anchor="w")
        topic_description = tk.Text(topic, height=3, bg="#ffffff", relief="solid", bd=1, font=("Segoe UI", 10))
        topic_description.pack(fill="x", pady=(3, 12))
        topic_actions = ttk.Frame(topic, style="Panel.TFrame")
        topic_actions.pack(fill="x", pady=(0, 14))
        topic_tree = ttk.Treeview(topic, columns=("title", "categories", "tests"), show="headings", height=6)
        for name, title_text, width in (("title", "Тематика", 235), ("categories", "Категорий", 85), ("tests", "Тестов", 70)):
            topic_tree.heading(name, text=title_text)
            topic_tree.column(name, width=width)
        topic_tree.pack(fill="both", expand=True)

        ttk.Label(category, text="Категории вопросов", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(category, text="Автор может сразу добавить категорию для своего нового теста.", style="Muted.TLabel").pack(anchor="w", pady=(3, 14))
        ttk.Label(category, text="Тематика", style="Muted.TLabel").pack(anchor="w")
        topic_combo = ttk.Combobox(category, state="readonly")
        topic_combo.pack(fill="x", pady=(3, 9))
        ttk.Label(category, text="Название категории", style="Muted.TLabel").pack(anchor="w")
        category_title = ttk.Entry(category)
        category_title.pack(fill="x", pady=(3, 12))
        category_actions = ttk.Frame(category, style="Panel.TFrame")
        category_actions.pack(fill="x", pady=(0, 14))
        category_tree = ttk.Treeview(category, columns=("title", "questions"), show="headings", height=8)
        category_tree.heading("title", text="Категория")
        category_tree.column("title", width=295)
        category_tree.heading("questions", text="Вопросов")
        category_tree.column("questions", width=85)
        category_tree.pack(fill="both", expand=True)

        def refresh_topics():
            rows = self.gateway.admin_topics()
            values = [f"{row['topic_id']} | {row['title']}" for row in rows]
            current = topic_combo.get()
            topic_combo["values"] = values
            for item in topic_tree.get_children():
                topic_tree.delete(item)
            for row in rows:
                topic_tree.insert("", "end", iid=str(row["topic_id"]), values=(row["title"], row["category_count"], row["quiz_count"]))
            if current in values:
                topic_combo.set(current)
            elif values:
                topic_combo.set(values[0])
            refresh_categories()

        def refresh_categories(_event=None):
            for item in category_tree.get_children():
                category_tree.delete(item)
            if not topic_combo.get():
                return
            topic_id = int(topic_combo.get().split("|", 1)[0])
            for row in self.gateway.admin_categories(topic_id):
                category_tree.insert("", "end", iid=str(row["category_id"]), values=(row["title"], row["question_count"]))

        def select_topic(_event=None):
            if not topic_tree.selection():
                return
            topic_id = topic_tree.selection()[0]
            for value in topic_combo["values"]:
                if value.startswith(f"{topic_id} |"):
                    topic_combo.set(value)
                    refresh_categories()
                    break

        def create_topic():
            if not topic_title.get().strip():
                messagebox.showwarning("Тематика", "Введите название тематики.")
                return
            try:
                self.gateway.create_topic(self.user.user_id, topic_title.get().strip(), topic_description.get("1.0", "end").strip())
                messagebox.showinfo("Тематика", "Тематика создана.")
                self.show_admin("Материалы")
            except Exception as exc:
                self.report_error(exc)

        def create_category():
            if not topic_combo.get() or not category_title.get().strip():
                messagebox.showwarning("Категория", "Выберите тематику и введите название категории.")
                return
            try:
                topic_id = int(topic_combo.get().split("|", 1)[0])
                self.gateway.create_category(self.user.user_id, topic_id, category_title.get().strip())
                messagebox.showinfo("Категория", "Категория создана и уже доступна в конструкторе вопросов.")
                self.show_admin("Материалы")
            except Exception as exc:
                self.report_error(exc)

        def delete_topic():
            if not topic_tree.selection():
                messagebox.showwarning("Тематика", "Выберите тематику в списке.")
                return
            topic_id = int(topic_tree.selection()[0])
            title = topic_tree.item(topic_tree.selection()[0], "values")[0]
            if not messagebox.askyesno("Удалить тематику", f"Удалить тематику «{title}»?\nУдаление возможно только если она пустая."):
                return
            try:
                self.gateway.delete_topic(self.user.user_id, topic_id)
                self.show_admin("Материалы")
            except Exception as exc:
                self.report_error(exc)

        def delete_category():
            if not category_tree.selection():
                messagebox.showwarning("Категория", "Выберите категорию в списке.")
                return
            category_id = int(category_tree.selection()[0])
            title = category_tree.item(category_tree.selection()[0], "values")[0]
            if not messagebox.askyesno("Удалить категорию", f"Удалить категорию «{title}»?\nИспользуемые в вопросах категории защищены."):
                return
            try:
                self.gateway.delete_category(self.user.user_id, category_id)
                self.show_admin("Материалы")
            except Exception as exc:
                self.report_error(exc)

        ttk.Button(topic_actions, text=self.icon_text("add", "Добавить"), style="Primary.TButton", command=create_topic).pack(side="left")
        ttk.Button(category_actions, text=self.icon_text("add", "Добавить"), style="Primary.TButton", command=create_category).pack(side="left")
        if self.user.role_code == "ADMIN":
            ttk.Button(topic_actions, text=self.icon_text("delete", "Удалить выбранную"), style="Danger.TButton", command=delete_topic).pack(side="left", padx=(8, 0))
            ttk.Button(category_actions, text=self.icon_text("delete", "Удалить выбранную"), style="Danger.TButton", command=delete_category).pack(side="left", padx=(8, 0))
        topic_combo.bind("<<ComboboxSelected>>", refresh_categories)
        topic_tree.bind("<<TreeviewSelect>>", select_topic)
        refresh_topics()

    def build_admin_quiz_editor(self, notebook):
        tab = ttk.Frame(notebook, style="App.TFrame", padding=16)
        notebook.add(tab, text="Новый тест")
        intro_outer, intro = self.panel(tab, padding=16)
        intro_outer.pack(fill="x", padx=(80, 80), pady=(0, 12))
        ttk.Label(intro, text="Шаг 1 из 2: создайте параметры теста", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            intro,
            text="После создания черновика переходите во вкладку «Вопросы» и заполните содержание теста.",
            style="Muted.TLabel",
            wraplength=920,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        outer, form = self.panel(tab, padding=22)
        outer.pack(fill="x", padx=(80, 80), pady=(0, 0))
        topics = self.gateway.admin_topics()
        topic_values = [f"{row['topic_id']} | {row['title']}" for row in topics]
        ttk.Label(form, text="Тематика", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=7)
        quiz_topic = ttk.Combobox(form, values=topic_values, state="readonly", width=48)
        quiz_topic.grid(row=0, column=1, sticky="ew", padx=(20, 0), pady=7)
        if topic_values:
            quiz_topic.set(topic_values[0])
        ttk.Label(form, text="Название теста", style="Card.TLabel").grid(row=1, column=0, sticky="w", pady=7)
        quiz_title = ttk.Entry(form)
        quiz_title.grid(row=1, column=1, sticky="ew", padx=(20, 0), pady=7)
        ttk.Label(form, text="Краткое описание", style="Card.TLabel").grid(row=2, column=0, sticky="nw", pady=7)
        quiz_description = tk.Text(form, height=3, bg="#ffffff", relief="solid", bd=1, font=("Segoe UI", 10))
        quiz_description.grid(row=2, column=1, sticky="ew", padx=(20, 0), pady=7)

        ttk.Label(form, text="Режим лимита времени", style="Card.TLabel").grid(row=3, column=0, sticky="w", pady=7)
        timer_mode = ttk.Combobox(form, values=["На весь тест", "На каждый вопрос"], state="readonly")
        timer_mode.set("На весь тест")
        timer_mode.grid(row=3, column=1, sticky="ew", padx=(20, 0), pady=7)

        ttk.Label(form, text="Лимит времени", style="Card.TLabel").grid(row=4, column=0, sticky="w", pady=7)
        duration_row = ttk.Frame(form, style="Panel.TFrame")
        duration_row.grid(row=4, column=1, sticky="ew", padx=(20, 0), pady=7)
        duration = ttk.Entry(duration_row, width=14)
        duration.insert(0, "15")
        duration.pack(side="left")
        duration_hint = ttk.Label(duration_row, text="минут на весь тест", style="Muted.TLabel")
        duration_hint.pack(side="left", padx=(10, 0))

        ttk.Label(form, text="Лимит попыток на пользователя", style="Card.TLabel").grid(row=5, column=0, sticky="w", pady=7)
        attempt_limit_row = ttk.Frame(form, style="Panel.TFrame")
        attempt_limit_row.grid(row=5, column=1, sticky="ew", padx=(20, 0), pady=7)
        attempt_limit = ttk.Entry(attempt_limit_row, width=14)
        attempt_limit.insert(0, "0")
        attempt_limit.pack(side="left")
        ttk.Label(attempt_limit_row, text="0 = без ограничений", style="Muted.TLabel").pack(side="left", padx=(10, 0))

        ttk.Label(form, text="Доступ", style="Card.TLabel").grid(row=6, column=0, sticky="w", pady=7)
        access = ttk.Combobox(form, values=["Публичный", "По приглашению"], state="readonly")
        access.set("Публичный")
        access.grid(row=6, column=1, sticky="ew", padx=(20, 0), pady=7)
        feedback = tk.BooleanVar(value=True)
        ttk.Checkbutton(form, text="Показывать правильные ответы после завершения", variable=feedback).grid(
            row=7, column=1, sticky="w", padx=(20, 0), pady=(8, 17)
        )
        form.columnconfigure(1, weight=1)

        def sync_timer_hint(_event=None):
            if timer_mode.get() == "На каждый вопрос":
                duration_hint.configure(text="минут на каждый вопрос")
            else:
                duration_hint.configure(text="минут на весь тест")

        timer_mode.bind("<<ComboboxSelected>>", sync_timer_hint)
        sync_timer_hint()

        def create_quiz():
            if not quiz_topic.get() or not quiz_title.get().strip():
                messagebox.showwarning("Тест", "Выберите тематику и укажите название теста.")
                return
            try:
                topic_id = int(quiz_topic.get().split("|", 1)[0])
                duration_value = int(duration.get())
                if duration_value < 1 or duration_value > 1440:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Тест", "Укажите корректный лимит времени: от 1 до 1440 минут.")
                return

            try:
                attempt_limit_raw = int(attempt_limit.get())
                if attempt_limit_raw < 0 or attempt_limit_raw > 1000:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Тест", "Лимит попыток указывается числом от 0 до 1000 (0 = без ограничений).")
                return

            try:
                timer_mode_code = "QUESTION" if timer_mode.get() == "На каждый вопрос" else "QUIZ"
                attempt_limit_value = attempt_limit_raw if attempt_limit_raw > 0 else None
                self.gateway.create_quiz(
                    self.user.user_id,
                    topic_id,
                    quiz_title.get().strip(),
                    quiz_description.get("1.0", "end").strip(),
                    timer_mode_code,
                    duration_value,
                    attempt_limit_value,
                    int(feedback.get()),
                    "PUBLIC" if access.get() == "Публичный" else "RESTRICTED",
                )
                messagebox.showinfo("Тест", "Черновик теста создан. Добавьте вопросы и опубликуйте его.")
                self.show_admin("Вопросы")
            except Exception as exc:
                self.report_error(exc)

        ttk.Button(form, text=self.icon_text("add", "Создать черновик и перейти к вопросам"), style="Primary.TButton", command=create_quiz).grid(
            row=8, column=1, sticky="w", padx=(20, 0)
        )

    def build_admin_question_editor(self, notebook):
        tab = ttk.Frame(notebook, style="App.TFrame", padding=16)
        notebook.add(tab, text="Вопросы")
        form_outer, form = self.panel(tab, padding=16)
        form_outer.pack(side="left", fill="both", expand=True, padx=(0, 7))
        list_outer, listing = self.panel(tab, padding=16)
        list_outer.pack(side="left", fill="both", expand=True, padx=(7, 0))
        editor_title = ttk.Label(form, text="Новый вопрос", style="CardTitle.TLabel")
        editor_title.pack(anchor="w")
        editor_note = ttk.Label(form, text="Заполните поля и добавьте вопрос в выбранный черновик.", style="Muted.TLabel")
        editor_note.pack(anchor="w", pady=(3, 10))
        quiz_chip_anchor = tk.Frame(form, bg=COLORS["panel"])
        quiz_chip_anchor.pack(anchor="w", pady=(0, SPACING["xs"]))
        managed_quizzes = [row for row in self.gateway.admin_quizzes(self.user) if row["status"] != "ARCHIVED"]
        quiz_values = [f"{row['quiz_id']} | {row['title']} ({STATUS_NAMES.get(row['status'], row['status'])})" for row in managed_quizzes]
        quiz_topics = {row["quiz_id"]: row["topic_id"] for row in managed_quizzes}
        quiz_statuses = {row["quiz_id"]: row["status"] for row in managed_quizzes}
        quiz_access_modes = {row["quiz_id"]: row["access_mode"] for row in managed_quizzes}
        quiz_timer_modes = {row["quiz_id"]: row["timer_mode"] for row in managed_quizzes}
        quiz_attempt_limits = {row["quiz_id"]: row.get("attempt_limit") for row in managed_quizzes}
        types, difficulties = self.gateway.dictionaries()
        type_values = [f"{row['type_code']} | {row['type_name']}" for row in types]
        diff_values = [f"{row['difficulty_code']} | {row['difficulty_name']}" for row in difficulties]
        type_modes = {row["type_code"]: row["answer_mode"] for row in types}
        editor_state = {"question_id": None}
        questions_by_id = {}
        ttk.Label(form, text="Черновик теста", style="Muted.TLabel").pack(anchor="w")
        q_quiz = ttk.Combobox(form, values=quiz_values, state="readonly")
        q_quiz.pack(fill="x", pady=(3, 7))
        ttk.Label(form, text="Категория вопроса", style="Muted.TLabel").pack(anchor="w")
        q_category = ttk.Combobox(form, state="readonly")
        q_category.pack(fill="x", pady=(3, 7))
        question_settings = ttk.Frame(form, style="Panel.TFrame")
        question_settings.pack(fill="x", pady=(0, 7))
        type_field = ttk.Frame(question_settings, style="Panel.TFrame")
        type_field.pack(side="left", fill="x", expand=True, padx=(0, 5))
        difficulty_field = ttk.Frame(question_settings, style="Panel.TFrame")
        difficulty_field.pack(side="left", fill="x", expand=True, padx=(5, 0))
        ttk.Label(type_field, text="Тип ответа", style="Muted.TLabel").pack(anchor="w")
        q_type = ttk.Combobox(type_field, values=type_values, state="readonly")
        q_type.pack(fill="x", pady=(3, 0))
        ttk.Label(difficulty_field, text="Сложность", style="Muted.TLabel").pack(anchor="w")
        q_diff = ttk.Combobox(difficulty_field, values=diff_values, state="readonly")
        q_diff.pack(fill="x", pady=(3, 0))
        for box, values in ((q_quiz, quiz_values), (q_type, type_values), (q_diff, diff_values)):
            if values:
                box.set(values[0])
        ttk.Label(form, text="Текст вопроса", style="Muted.TLabel").pack(anchor="w")
        q_text = ttk.Entry(form)
        q_text.pack(fill="x", pady=(3, 7))
        details = ttk.Frame(form, style="Panel.TFrame")
        details.pack(fill="x", pady=(0, 7))
        explanation_field = ttk.Frame(details, style="Panel.TFrame")
        explanation_field.pack(side="left", fill="x", expand=True, padx=(0, 5))
        points_field = ttk.Frame(details, style="Panel.TFrame")
        points_field.pack(side="left", padx=(5, 0))
        ttk.Label(explanation_field, text="Пояснение после проверки", style="Muted.TLabel").pack(anchor="w")
        explanation = ttk.Entry(explanation_field)
        explanation.pack(fill="x", pady=(3, 0))
        ttk.Label(points_field, text="Баллы", style="Muted.TLabel").pack(anchor="w")
        points = ttk.Entry(points_field, width=10)
        points.insert(0, "1")
        points.pack(pady=(3, 0))

        answer_area = ttk.Frame(form, style="Panel.TFrame")
        answer_area.pack(fill="x", pady=(1, 5))
        expected_field = ttk.Frame(answer_area, style="Panel.TFrame")
        expected_label = ttk.Label(expected_field, text="Правильный ответ", style="Muted.TLabel")
        expected_label.pack(anchor="w")
        expected = ttk.Entry(expected_field)
        expected.pack(fill="x", pady=(3, 0))
        option_field = ttk.Frame(answer_area, style="Panel.TFrame")
        options_label = ttk.Label(option_field, text="Варианты: один вариант в каждой строке", style="Muted.TLabel")
        options_label.pack(anchor="w")
        options = tk.Text(option_field, height=3, bg="#ffffff", relief="solid", bd=1, font=("Segoe UI", 9))
        options.pack(fill="x", pady=(3, 5))
        correct_field = ttk.Frame(option_field, style="Panel.TFrame")
        ttk.Label(correct_field, text="Номера правильных вариантов (например, 1 или 1,3)", style="Muted.TLabel").pack(anchor="w")
        correct = ttk.Entry(correct_field)
        correct.pack(fill="x", pady=(3, 0))
        boolean_field = ttk.Frame(answer_area, style="Panel.TFrame")
        ttk.Label(boolean_field, text="Правильный ответ", style="Muted.TLabel").pack(anchor="w")
        boolean_answer = ttk.Combobox(boolean_field, values=["Верно", "Неверно"], state="readonly")
        boolean_answer.set("Верно")
        boolean_answer.pack(fill="x", pady=(3, 0))

        ttk.Label(listing, text="Вопросы выбранного черновика", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 9))
        question_tree = ttk.Treeview(listing, columns=("number", "text", "type", "points"), show="headings")
        for name, title, width in (("number", "#", 38), ("text", "Вопрос", 260), ("type", "Тип", 120), ("points", "Баллы", 60)):
            question_tree.heading(name, text=title)
            question_tree.column(name, width=width)
        question_tree.pack(fill="both", expand=True)

        def type_code():
            return q_type.get().split("|", 1)[0].strip() if q_type.get() else ""

        def set_combobox_value(box, values, key):
            for value in values:
                if value.startswith(f"{key} |"):
                    box.set(value)
                    return

        def update_answer_fields(_event=None):
            expected_field.pack_forget()
            option_field.pack_forget()
            correct_field.pack_forget()
            boolean_field.pack_forget()
            code = type_code()
            if code == "BOOLEAN":
                boolean_field.pack(fill="x")
            elif code == "ORDERING":
                options_label.configure(text="Элементы последовательности: каждый с новой строки в правильном порядке")
                option_field.pack(fill="x")
            elif type_modes.get(code) == "OPTIONS":
                options_label.configure(text="Варианты: один вариант в каждой строке")
                option_field.pack(fill="x")
                correct_field.pack(fill="x", pady=(0, 0))
            else:
                expected_labels = {
                    "TEXT": "Правильный текстовый ответ",
                    "NUMBER": "Правильное число",
                }
                expected_label.configure(text=expected_labels.get(code, "Правильный ответ"))
                expected_field.pack(fill="x")

        def clear_fields():
            editor_state["question_id"] = None
            editor_title.configure(text="Новый вопрос")
            editor_note.configure(text="Заполните поля и добавьте вопрос в выбранный черновик.")
            save_button.configure(text=self.icon_text("add", "Добавить вопрос"))
            q_text.delete(0, "end")
            expected.delete(0, "end")
            explanation.delete(0, "end")
            points.delete(0, "end")
            points.insert(0, "1")
            options.delete("1.0", "end")
            correct.delete(0, "end")
            boolean_answer.set("Верно")
            if type_values:
                q_type.set(type_values[0])
            if diff_values:
                q_diff.set(diff_values[0])
            update_answer_fields()
            question_tree.selection_remove(*question_tree.selection())

        def refresh_question_context(_event=None):
            clear_fields()
            for item in question_tree.get_children():
                question_tree.delete(item)
            questions_by_id.clear()
            for child in quiz_chip_anchor.winfo_children():
                child.destroy()
            if not q_quiz.get():
                q_category["values"] = []
                q_category.set("")
                return
            quiz_id = int(q_quiz.get().split("|", 1)[0])
            self.add_chip_row(
                quiz_chip_anchor,
                [
                    (STATUS_NAMES.get(quiz_statuses.get(quiz_id), "Черновик"), self.tone_for_status(quiz_statuses.get(quiz_id))),
                    (ACCESS_NAMES.get(quiz_access_modes.get(quiz_id), "Публичный"), self.tone_for_access(quiz_access_modes.get(quiz_id))),
                    (TIMER_MODE_NAMES.get(quiz_timer_modes.get(quiz_id) or "QUIZ", "На весь тест"), "default"),
                    (self.format_attempt_limit(quiz_attempt_limits.get(quiz_id)), "default"),
                ],
            )
            topic_id = quiz_topics[quiz_id]
            categories = self.gateway.admin_categories(topic_id)
            category_values = [f"{row['category_id']} | {row['title']}" for row in categories]
            q_category["values"] = category_values
            q_category.set(category_values[0] if category_values else "")
            for row in self.gateway.admin_questions(quiz_id):
                questions_by_id[row["question_id"]] = row
                question_tree.insert("", "end", iid=str(row["question_id"]), values=(row["seq_no"], row["question_text"], row["type_code"], row["points"]))

        def load_question(_event=None):
            if not question_tree.selection():
                return
            question_id = int(question_tree.selection()[0])
            question = questions_by_id[question_id]
            editor_state["question_id"] = question_id
            editor_title.configure(text="Редактирование вопроса")
            editor_note.configure(text="Изменения применяются к выбранному вопросу черновика.")
            save_button.configure(text=self.icon_text("save", "Сохранить изменения"))
            set_combobox_value(q_category, list(q_category["values"]), question["category_id"])
            set_combobox_value(q_type, type_values, question["type_code"])
            set_combobox_value(q_diff, diff_values, question["difficulty_code"])
            q_text.delete(0, "end")
            q_text.insert(0, question["question_text"] or "")
            expected.delete(0, "end")
            expected.insert(0, question["expected_answer"] or "")
            explanation.delete(0, "end")
            explanation.insert(0, question["explanation"] or "")
            points.delete(0, "end")
            points.insert(0, str(question["points"]))
            options.delete("1.0", "end")
            correct.delete(0, "end")
            stored_options = self.gateway.admin_question_options(question_id)
            options.insert("1.0", "\n".join(row["option_text"] for row in stored_options))
            correct.insert(0, ",".join(str(row["seq_no"]) for row in stored_options if row["is_correct"] == 1))
            if question["type_code"] == "BOOLEAN":
                correct_option = next((row["option_text"] for row in stored_options if row["is_correct"] == 1), "Верно")
                boolean_answer.set(correct_option)
            update_answer_fields()

        def save_question():
            if not q_quiz.get() or not q_category.get() or not q_text.get().strip():
                messagebox.showwarning("Вопрос", "Выберите черновик и категорию, затем введите текст вопроса.")
                return
            quiz_id = int(q_quiz.get().split("|", 1)[0])
            if quiz_statuses.get(quiz_id) != "DRAFT":
                messagebox.showwarning("Вопрос", "Добавлять и редактировать можно только вопросы в тесте со статусом «Черновик».")
                return
            try:
                code = type_code()
                options_list = []
                if code == "BOOLEAN":
                    options_list = [
                        ("Верно", int(boolean_answer.get() == "Верно")),
                        ("Неверно", int(boolean_answer.get() == "Неверно")),
                    ]
                elif code == "ORDERING" or type_modes.get(code) == "OPTIONS":
                    raw_options = [line.strip() for line in options.get("1.0", "end").splitlines() if line.strip()]
                    if code == "ORDERING":
                        if len(raw_options) < 2:
                            messagebox.showwarning("Вопрос", "Для последовательности добавьте минимум два элемента.")
                            return
                        options_list = [(text, 1) for text in raw_options]
                    else:
                        indexes = {int(value.strip()) for value in correct.get().split(",") if value.strip().isdigit()}
                        if not raw_options or not indexes:
                            messagebox.showwarning("Вопрос", "Для вопроса с выбором заполните варианты и номер правильного ответа.")
                            return
                        options_list = [(text, int(index in indexes)) for index, text in enumerate(raw_options, 1)]
                fields = (
                    self.user.user_id,
                    int(q_category.get().split("|", 1)[0]),
                    code,
                    q_diff.get().split("|", 1)[0].strip(),
                    q_text.get().strip(),
                    expected.get().strip() if type_modes.get(code) != "OPTIONS" and code != "ORDERING" else "",
                    explanation.get().strip(),
                    float(points.get()),
                    options_list,
                )
                if editor_state["question_id"] is None:
                    self.gateway.create_question(fields[0], quiz_id, *fields[1:])
                    messagebox.showinfo("Вопрос", "Вопрос добавлен в черновик.")
                else:
                    self.gateway.update_question(fields[0], editor_state["question_id"], *fields[1:])
                    messagebox.showinfo("Вопрос", "Изменения вопроса сохранены.")
                self.show_admin("Вопросы")
            except Exception as exc:
                self.report_error(exc)

        def delete_question():
            if not question_tree.selection():
                messagebox.showwarning("Вопрос", "Выберите вопрос в списке.")
                return
            if not messagebox.askyesno(
                "Удалить вопрос",
                "Удалить выбранный вопрос?\n"
                "Для опубликованных тестов статистика будет пересчитана по оставшимся вопросам.",
            ):
                return
            try:
                self.gateway.delete_question(self.user.user_id, int(question_tree.selection()[0]))
                self.show_admin("Вопросы")
            except Exception as exc:
                self.report_error(exc)

        form_actions = ttk.Frame(form, style="Panel.TFrame")
        form_actions.pack(fill="x", pady=(8, 0))
        save_button = ttk.Button(form_actions, text=self.icon_text("add", "Добавить вопрос"), style="Primary.TButton", command=save_question)
        save_button.pack(side="left")
        ttk.Button(form_actions, text=self.icon_text("clear", "Очистить форму"), style="Quiet.TButton", command=clear_fields).pack(side="left", padx=(8, 0))
        ttk.Button(listing, text=self.icon_text("delete", "Удалить выбранный вопрос"), style="Danger.TButton", command=delete_question).pack(anchor="e", pady=(10, 0))
        q_quiz.bind("<<ComboboxSelected>>", refresh_question_context)
        q_type.bind("<<ComboboxSelected>>", update_answer_fields)
        question_tree.bind("<<TreeviewSelect>>", load_question)
        update_answer_fields()
        refresh_question_context()

    def build_admin_publication(self, notebook):
        tab = ttk.Frame(notebook, style="App.TFrame", padding=16)
        notebook.add(tab, text="Публикация")
        outer, content = self.panel(tab, padding=15)
        outer.pack(fill="both", expand=True)
        ttk.Label(content, text="Управление тестами", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(content, text="Публикуйте готовые черновики и выдавайте доступ к закрытым тестам.", style="Muted.TLabel").pack(anchor="w", pady=(3, 12))
        tree = ttk.Treeview(content, columns=("topic", "title", "access", "status"), show="headings", height=9)
        for name, title, width in (("topic", "Тематика", 250), ("title", "Тест", 390), ("access", "Доступ", 130), ("status", "Статус", 130)):
            tree.heading(name, text=title)
            tree.column(name, width=width)
        tree.pack(fill="x")
        quizzes = self.gateway.admin_quizzes(self.user)
        quiz_map = {row["quiz_id"]: row for row in quizzes}
        for row in quizzes:
            tree.insert(
                "", "end", iid=str(row["quiz_id"]),
                values=(row["topic_title"], row["title"], ACCESS_NAMES.get(row["access_mode"], row["access_mode"]), STATUS_NAMES.get(row["status"], row["status"])),
            )

        settings_outer, settings = self.panel(tab, padding=12)
        settings_outer.pack(fill="x", pady=(10, 0))
        ttk.Label(settings, text="Настройки выбранного теста", style="CardTitle.TLabel").pack(anchor="w")
        state_actions = ttk.Frame(settings, style="Panel.TFrame")
        state_actions.pack(fill="x", pady=(8, 0))
        feedback_var = tk.BooleanVar(value=True)
        feedback_toggle = ttk.Checkbutton(
            settings,
            text="Показывать правильные ответы и пояснения автора в результате",
            variable=feedback_var,
        )
        feedback_toggle.pack(anchor="w", pady=(8, 0))
        feedback_hint = ttk.Label(settings, text="", style="Muted.TLabel")
        feedback_hint.pack(anchor="w", pady=(4, 0))
        attempts_row = ttk.Frame(settings, style="Panel.TFrame")
        attempts_row.pack(anchor="w", pady=(8, 0))
        ttk.Label(attempts_row, text="Лимит попыток на пользователя", style="Muted.TLabel").pack(side="left")
        attempt_limit_value = tk.StringVar(value="0")
        attempt_limit_entry = ttk.Entry(attempts_row, width=10, textvariable=attempt_limit_value)
        attempt_limit_entry.pack(side="left", padx=(10, 0))
        ttk.Label(attempts_row, text="0 = без ограничений", style="Muted.TLabel").pack(side="left", padx=(10, 0))
        chips_anchor = tk.Frame(settings, bg=COLORS["panel"])
        chips_anchor.pack(anchor="w", pady=(SPACING["xs"], 0))

        def selected_quiz():
            if not tree.selection():
                return None
            return quiz_map.get(int(tree.selection()[0]))

        def refresh_feedback_controls(_event=None):
            row = selected_quiz()
            if row is None:
                feedback_var.set(True)
                attempt_limit_value.set("0")
                feedback_toggle.configure(state="disabled")
                save_feedback.configure(state="disabled")
                attempt_limit_entry.configure(state="disabled")
                save_attempt_limit.configure(state="disabled")
                feedback_hint.configure(text="Выберите тест. Изменение доступно только для черновика.")
                for child in chips_anchor.winfo_children():
                    child.destroy()
                return
            for child in chips_anchor.winfo_children():
                child.destroy()
            self.add_chip_row(
                chips_anchor,
                [
                    (STATUS_NAMES.get(row["status"], row["status"]), self.tone_for_status(row["status"])),
                    (ACCESS_NAMES.get(row["access_mode"], row["access_mode"]), self.tone_for_access(row["access_mode"])),
                    (TIMER_MODE_NAMES.get(row.get("timer_mode") or "QUIZ", "На весь тест"), "default"),
                    (self.format_attempt_limit(row.get("attempt_limit")), "default"),
                ],
            )
            feedback_var.set(int(row.get("show_feedback") or 0) == 1)
            attempt_limit_value.set(str(row.get("attempt_limit") or 0))
            if row["status"] == "DRAFT":
                feedback_toggle.configure(state="normal")
                save_feedback.configure(state="normal")
                attempt_limit_entry.configure(state="normal")
                save_attempt_limit.configure(state="normal")
                feedback_hint.configure(text="Черновик: настройку можно менять перед публикацией.")
            else:
                feedback_toggle.configure(state="disabled")
                save_feedback.configure(state="disabled")
                attempt_limit_entry.configure(state="disabled")
                save_attempt_limit.configure(state="disabled")
                feedback_hint.configure(text="Опубликованный тест: чтобы изменить настройку, сначала скройте его в черновик.")

        def parse_attempt_limit():
            try:
                raw_value = attempt_limit_value.get().strip() or "0"
                parsed = int(raw_value)
                if parsed < 0 or parsed > 1000:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Лимит попыток", "Укажите число от 0 до 1000 (0 = без ограничений).")
                return None
            return parsed

        def persist_draft_settings(show_success: bool):
            row = selected_quiz()
            if row is None:
                messagebox.showwarning("Настройки", "Сначала выберите тест в таблице.")
                return False
            if row["status"] != "DRAFT":
                messagebox.showwarning("Настройки", "Изменять настройки можно только у черновика.")
                return False
            parsed = parse_attempt_limit()
            if parsed is None:
                return False
            try:
                self.gateway.set_quiz_feedback(self.user.user_id, row["quiz_id"], int(feedback_var.get()))
                self.gateway.set_quiz_attempt_limit(
                    self.user.user_id,
                    row["quiz_id"],
                    parsed if parsed > 0 else None,
                )
                if show_success:
                    messagebox.showinfo("Настройки", "Настройки черновика сохранены.")
                return True
            except Exception as exc:
                self.report_error(exc)
                return False

        def apply_feedback_setting():
            if persist_draft_settings(show_success=True):
                self.show_admin("Публикация")

        save_feedback = ttk.Button(
            settings,
            text=self.icon_text("save", "Сохранить настройку для черновика"),
            style="Quiet.TButton",
            command=apply_feedback_setting,
        )
        save_feedback.pack(anchor="w", pady=(8, 0))

        def apply_attempt_limit_setting():
            if persist_draft_settings(show_success=True):
                self.show_admin("Публикация")

        save_attempt_limit = ttk.Button(
            settings,
            text=self.icon_text("save", "Сохранить лимит попыток"),
            style="Quiet.TButton",
            command=apply_attempt_limit_setting,
        )
        save_attempt_limit.pack(anchor="w", pady=(8, 0))

        def publish():
            if not tree.selection():
                return
            row = selected_quiz()
            if row and row["status"] == "DRAFT":
                if not persist_draft_settings(show_success=False):
                    return
            try:
                self.gateway.publish_quiz(self.user.user_id, int(tree.selection()[0]))
                messagebox.showinfo("Публикация", "Тест опубликован и доступен в каталоге.")
                self.show_admin("Публикация")
            except Exception as exc:
                self.report_error(exc)

        ttk.Button(state_actions, text=self.icon_text("publish", "Опубликовать выбранный тест"), style="Primary.TButton", command=publish).pack(side="left")
        restricted = [row for row in quizzes if row["access_mode"] == "RESTRICTED"]
        users = self.gateway.users()
        access_row = ttk.Frame(settings, style="Panel.TFrame")
        access_row.pack(fill="x", pady=(10, 0))
        access_quiz = ttk.Combobox(access_row, values=[f"{row['quiz_id']} | {row['title']}" for row in restricted], state="readonly", width=29)
        access_user = ttk.Combobox(access_row, values=[f"{row['user_id']} | {row['login']}" for row in users], state="readonly", width=24)
        access_quiz.pack(side="left", padx=(0, 7))
        access_user.pack(side="left", padx=(0, 7))
        if restricted:
            access_quiz.set(f"{restricted[0]['quiz_id']} | {restricted[0]['title']}")
        if users:
            access_user.set(f"{users[0]['user_id']} | {users[0]['login']}")

        def grant_access():
            if not access_quiz.get() or not access_user.get():
                messagebox.showwarning("Доступ", "Выберите закрытый тест и пользователя.")
                return
            try:
                self.gateway.grant_access(
                    self.user.user_id,
                    int(access_quiz.get().split("|", 1)[0]),
                    int(access_user.get().split("|", 1)[0]),
                )
                messagebox.showinfo("Доступ", "Доступ к закрытому тесту выдан.")
            except Exception as exc:
                self.report_error(exc)

        ttk.Button(access_row, text=self.icon_text("grant", "Выдать доступ"), style="Quiet.TButton", command=grant_access).pack(side="left", padx=(7, 0))

        def delete_quiz():
            if not tree.selection():
                messagebox.showwarning("Тест", "Выберите тест в таблице.")
                return
            if not messagebox.askyesno(
                "Удалить тест",
                "Удалить выбранный тест вместе с его вопросами?\n"
                "Все попытки по этому тесту будут удалены, статистика сбросится.",
            ):
                return
            try:
                self.gateway.delete_quiz(self.user.user_id, int(tree.selection()[0]))
                self.show_admin("Публикация")
            except Exception as exc:
                self.report_error(exc)

        def archive_quiz():
            if not tree.selection():
                messagebox.showwarning("Тест", "Выберите тест в таблице.")
                return
            if not messagebox.askyesno(
                "Скрыть тест",
                "Снять тест с публикации и вернуть его в черновик для редактирования?\n"
                "Результаты прохождений сохранятся.",
            ):
                return
            try:
                self.gateway.archive_quiz(self.user.user_id, int(tree.selection()[0]))
                self.show_admin("Публикация")
            except Exception as exc:
                self.report_error(exc)

        if self.user.role_code in ("ADMIN", "AUTHOR"):
            ttk.Button(state_actions, text=self.icon_text("hide", "Скрыть в черновик"), style="Quiet.TButton", command=archive_quiz).pack(side="left", padx=(9, 0))
            ttk.Button(state_actions, text=self.icon_text("delete", "Удалить тест"), style="Danger.TButton", command=delete_quiz).pack(side="left", padx=(9, 0))
        tree.bind("<<TreeviewSelect>>", refresh_feedback_controls)
        refresh_feedback_controls()

    def build_admin_statistics(self, notebook):
        tab = ttk.Frame(notebook, style="App.TFrame", padding=16)
        notebook.add(tab, text="Аналитика")
        quiz_outer, quiz_panel = self.panel(tab, padding=12)
        quiz_outer.pack(fill="x", pady=(0, 12))
        quiz_tree = ttk.Treeview(quiz_panel, columns=("topic", "quiz", "attempts", "average"), show="headings", height=5)
        for name, title, width in (("topic", "Тематика", 270), ("quiz", "Тест", 410), ("attempts", "Попыток", 110), ("average", "Средний %", 120)):
            quiz_tree.heading(name, text=title)
            quiz_tree.column(name, width=width)
        quiz_tree.pack(fill="x")
        stats = self.gateway.quiz_statistics(self.user)
        for row in stats:
            quiz_tree.insert("", "end", iid=str(row["quiz_id"]), values=(row["topic_title"], row["quiz_title"], row["attempts_count"], row["average_score"] or "-"))
        details_outer, details = self.panel(tab, padding=12)
        details_outer.pack(fill="both", expand=True)
        question_tree = ttk.Treeview(details, columns=("question", "answers", "percent"), show="headings")
        for name, title, width in (("question", "Вопрос", 700), ("answers", "Ответов", 110), ("percent", "Верно, %", 120)):
            question_tree.heading(name, text=title)
            question_tree.column(name, width=width)
        question_tree.pack(fill="both", expand=True)

        def show_question_stats(_event=None):
            for item in question_tree.get_children():
                question_tree.delete(item)
            if not quiz_tree.selection():
                return
            for row in self.gateway.question_statistics(int(quiz_tree.selection()[0])):
                question_tree.insert("", "end", values=(row["question_text"], row["answer_count"], row["correct_percent"]))

        quiz_tree.bind("<<TreeviewSelect>>", show_question_stats)

    def build_admin_progress(self, notebook):
        tab = ttk.Frame(notebook, style="App.TFrame", padding=16)
        notebook.add(tab, text="Прогресс")
        users_outer, users_panel = self.panel(tab, padding=16)
        users_outer.pack(side="left", fill="both", expand=True, padx=(0, 7))
        quizzes_outer, quizzes_panel = self.panel(tab, padding=16)
        quizzes_outer.pack(side="left", fill="both", expand=True, padx=(7, 0))

        ttk.Label(users_panel, text="Прогресс пользователей", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(users_panel, text="Выберите аккаунт для просмотра его попыток.", style="Muted.TLabel").pack(anchor="w", pady=(3, 12))
        users_tree = ttk.Treeview(users_panel, columns=("name", "login", "attempts"), show="headings")
        for name, title, width in (("name", "Пользователь", 220), ("login", "Логин", 125), ("attempts", "Попыток", 70)):
            users_tree.heading(name, text=title)
            users_tree.column(name, width=width)
        users_tree.pack(fill="both", expand=True)

        ttk.Label(quizzes_panel, text="Попытки по тестам", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(
            quizzes_panel,
            text="Сброс удаляет результаты и незавершенные попытки, но не меняет логин, пароль или роль.",
            style="Muted.TLabel",
            wraplength=470,
        ).pack(anchor="w", pady=(3, 12))
        quiz_tree = ttk.Treeview(quizzes_panel, columns=("topic", "quiz", "attempts"), show="headings")
        for name, title, width in (("topic", "Тематика", 155), ("quiz", "Тест", 220), ("attempts", "Попыток", 70)):
            quiz_tree.heading(name, text=title)
            quiz_tree.column(name, width=width)
        quiz_tree.pack(fill="both", expand=True)

        for row in self.gateway.user_progress_summary():
            users_tree.insert(
                "", "end", iid=str(row["user_id"]),
                values=(row["full_name"], row["login"], row["attempt_count"]),
            )

        def selected_user_id():
            if not users_tree.selection():
                messagebox.showwarning("Прогресс", "Выберите пользователя.")
                return None
            return int(users_tree.selection()[0])

        def show_attempts(_event=None):
            for item in quiz_tree.get_children():
                quiz_tree.delete(item)
            user_id = selected_user_id()
            if user_id is None:
                return
            for row in self.gateway.user_quiz_progress(user_id):
                quiz_tree.insert(
                    "", "end", iid=str(row["quiz_id"]),
                    values=(row["topic_title"], row["quiz_title"], row["attempt_count"]),
                )

        def reset_quiz_attempts():
            user_id = selected_user_id()
            if user_id is None:
                return
            if not quiz_tree.selection():
                messagebox.showwarning("Прогресс", "Выберите тест в правой таблице.")
                return
            quiz_id = int(quiz_tree.selection()[0])
            quiz_title = quiz_tree.item(quiz_tree.selection()[0], "values")[1]
            if not messagebox.askyesno(
                "Сбросить попытки",
                f"Удалить все попытки выбранного пользователя по тесту «{quiz_title}»?\nЭто действие нельзя отменить.",
            ):
                return
            try:
                self.gateway.reset_user_quiz_attempts(self.user.user_id, user_id, quiz_id)
                messagebox.showinfo("Прогресс", "Попытки по выбранному тесту удалены.")
                self.show_admin("Прогресс")
            except Exception as exc:
                self.report_error(exc)

        def reset_all_attempts():
            user_id = selected_user_id()
            if user_id is None:
                return
            name = users_tree.item(users_tree.selection()[0], "values")[0]
            if not messagebox.askyesno(
                "Обнулить прогресс",
                f"Удалить всю историю тестирования пользователя «{name}»?\nЛогин и роль сохранятся. Действие нельзя отменить.",
            ):
                return
            try:
                self.gateway.reset_user_progress(self.user.user_id, user_id)
                messagebox.showinfo("Прогресс", "Весь прогресс пользователя обнулен.")
                self.show_admin("Прогресс")
            except Exception as exc:
                self.report_error(exc)

        buttons = ttk.Frame(quizzes_panel, style="Panel.TFrame")
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text=self.icon_text("reset", "Сбросить выбранный тест"), style="Danger.TButton", command=reset_quiz_attempts).pack(side="left")
        ttk.Button(buttons, text=self.icon_text("reset", "Обнулить весь прогресс"), style="Danger.TButton", command=reset_all_attempts).pack(side="right")
        users_tree.bind("<<TreeviewSelect>>", show_attempts)
        if users_tree.get_children():
            users_tree.selection_set(users_tree.get_children()[0])
            show_attempts()

    def build_admin_users(self, notebook):
        tab = ttk.Frame(notebook, style="App.TFrame", padding=16)
        notebook.add(tab, text="Команда")
        creator_outer, creator = self.panel(tab, padding=16)
        creator_outer.pack(fill="x", pady=(0, 12))
        ttk.Label(creator, text="Добавить автора", style="CardTitle.TLabel").grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(
            creator,
            text="Автор входит по своему логину и может собирать, публиковать и анализировать тесты.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(4, 14))
        ttk.Label(creator, text="Имя автора", style="Muted.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Label(creator, text="Логин", style="Muted.TLabel").grid(row=2, column=1, sticky="w", padx=(12, 0))
        ttk.Label(creator, text="Временный пароль", style="Muted.TLabel").grid(row=2, column=2, sticky="w", padx=(12, 0))
        author_name = ttk.Entry(creator)
        author_login = ttk.Entry(creator)
        author_password = ttk.Entry(creator, show="*")
        author_name.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        author_login.grid(row=3, column=1, sticky="ew", padx=(12, 0), pady=(4, 0))
        author_password.grid(row=3, column=2, sticky="ew", padx=(12, 0), pady=(4, 0))
        creator.columnconfigure(0, weight=2)
        creator.columnconfigure(1, weight=1)
        creator.columnconfigure(2, weight=1)

        def create_author():
            if not author_name.get().strip() or not author_login.get().strip() or not author_password.get():
                messagebox.showwarning("Автор", "Укажите имя, логин и временный пароль автора.")
                return
            try:
                self.gateway.create_author(
                    self.user.user_id,
                    author_login.get().strip(),
                    author_password.get(),
                    author_name.get().strip(),
                )
                messagebox.showinfo("Автор", "Учетная запись автора создана. Данные для входа можно передать автору.")
                self.show_admin()
            except Exception as exc:
                self.report_error(exc)

        ttk.Button(creator, text=self.icon_text("author", "Создать автора"), style="Primary.TButton", command=create_author).grid(
            row=3, column=3, sticky="e", padx=(16, 0), pady=(4, 0)
        )

        outer, content = self.panel(tab, padding=15)
        outer.pack(fill="both", expand=True)
        ttk.Label(content, text="Пользователи и роли", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 10))
        tree = ttk.Treeview(content, columns=("login", "name", "role", "active"), show="headings")
        for name, title, width in (("login", "Логин", 180), ("name", "Имя", 360), ("role", "Роль", 170), ("active", "Активен", 90)):
            tree.heading(name, text=title)
            tree.column(name, width=width)
        tree.pack(fill="both", expand=True)
        user_active_flags = {}
        for row in self.gateway.users():
            role_name = ROLE_NAMES.get(row["role_code"], row["role_code"])
            is_active = int(row["is_active"] or 0)
            user_active_flags[int(row["user_id"])] = is_active
            active_name = "Да" if is_active else "Нет"
            tree.insert("", "end", iid=str(row["user_id"]), values=(row["login"], row["full_name"], role_name, active_name))

        def selected_user_id():
            if not tree.selection():
                messagebox.showwarning("Пользователи", "Выберите пользователя в таблице.")
                return None
            return int(tree.selection()[0])

        def selected_user_active():
            user_id = selected_user_id()
            if user_id is None:
                return None
            return user_active_flags.get(user_id, 0)

        def apply_role(role_code):
            user_id = selected_user_id()
            if user_id is None:
                return
            try:
                self.gateway.set_role(self.user.user_id, user_id, role_code)
                messagebox.showinfo("Роли", "Роль пользователя изменена.")
                self.show_admin("Команда")
            except Exception as exc:
                self.report_error(exc)

        def change_password():
            user_id = selected_user_id()
            if user_id is None:
                return
            new_password = password_entry.get()
            if len(new_password) < 6:
                messagebox.showwarning("Пароль", "Новый пароль должен содержать не менее 6 символов.")
                return
            try:
                self.gateway.set_user_password(self.user.user_id, user_id, new_password)
                messagebox.showinfo("Пароль", "Пароль пользователя обновлен.")
                password_entry.delete(0, "end")
            except Exception as exc:
                self.report_error(exc)

        def set_user_active(is_active: int):
            user_id = selected_user_id()
            if user_id is None:
                return
            current_state = selected_user_active()
            if current_state is None:
                return
            if current_state == is_active:
                state_label = "активен" if is_active == 1 else "уже отключен"
                messagebox.showwarning("Пользователь", f"Выбранный аккаунт {state_label}.")
                return
            values = tree.item(tree.selection()[0], "values")
            login = values[0]
            full_name = values[1]
            action_text = "включить" if is_active == 1 else "отключить"
            if not messagebox.askyesno(
                "Изменение активности",
                f"Вы действительно хотите {action_text} аккаунт «{full_name}» ({login})?",
            ):
                return
            try:
                self.gateway.set_user_active(self.user.user_id, user_id, is_active)
                messagebox.showinfo("Пользователи", "Статус активности пользователя обновлен.")
                self.show_admin("Команда")
            except Exception as exc:
                self.report_error(exc)

        def delete_user():
            user_id = selected_user_id()
            if user_id is None:
                return
            values = tree.item(tree.selection()[0], "values")
            login = values[0]
            full_name = values[1]
            if not messagebox.askyesno(
                "Удалить пользователя",
                f"Удалить пользователя «{full_name}» ({login})?\n"
                "Будут удалены его попытки, а также тесты, созданные этим пользователем.",
            ):
                return
            try:
                self.gateway.delete_user(self.user.user_id, user_id)
                messagebox.showinfo("Пользователи", "Пользователь удален.")
                self.show_admin("Команда")
            except Exception as exc:
                self.report_error(exc)

        actions = ttk.Frame(tab, style="App.TFrame")
        actions.pack(fill="x", pady=(12, 0))
        role_actions = ttk.Frame(actions, style="App.TFrame")
        role_actions.pack(side="left")
        ttk.Button(role_actions, text=self.icon_text("author", "Назначить автором"), style="Primary.TButton", command=lambda: apply_role("AUTHOR")).pack(side="left")
        ttk.Button(role_actions, text=self.icon_text("user", "Сделать участником"), style="Quiet.TButton", command=lambda: apply_role("USER")).pack(side="left", padx=(10, 0))

        security_actions = ttk.Frame(actions, style="App.TFrame")
        security_actions.pack(side="right")
        ttk.Label(security_actions, text="Новый пароль", style="Muted.TLabel").pack(side="left", padx=(0, 8))
        password_entry = ttk.Entry(security_actions, width=20, show="*")
        password_entry.pack(side="left")
        ttk.Button(security_actions, text=self.icon_text("save", "Сменить пароль"), style="Quiet.TButton", command=change_password).pack(side="left", padx=(8, 0))
        ttk.Button(
            security_actions,
            text=self.icon_text("disable", "Отключить"),
            style="Quiet.TButton",
            command=lambda: set_user_active(0),
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            security_actions,
            text=self.icon_text("enable", "Включить"),
            style="Quiet.TButton",
            command=lambda: set_user_active(1),
        ).pack(side="left", padx=(8, 0))
        ttk.Button(security_actions, text=self.icon_text("delete", "Удалить пользователя"), style="Danger.TButton", command=delete_user).pack(side="left", padx=(8, 0))

    def destroy(self):
        self.abandon_active_attempt()
        self.gateway.close()
        super().destroy()


def run_application():
    QuizApplication().mainloop()
