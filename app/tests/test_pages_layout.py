import tkinter as tk
import unittest
from copy import deepcopy
from tkinter import ttk
from unittest.mock import Mock, patch

from quiz_client import ui
from quiz_client.config import ConnectionSettings
from quiz_client.database import SessionUser
from quiz_client.layout import ScrollArea, reveal_widget


class PagesLayoutTest(unittest.TestCase):
    def setUp(self):
        self.settings_patch = patch.object(ui, "load_settings", return_value=ConnectionSettings())
        self.settings_patch.start()
        self.app = ui.QuizApplication()
        self.scale = self.app.tk.call("tk", "scaling")
        self.app.geometry("1060x700+10000+10000")
        self.app.user = SessionUser(7, "Администратор системы", "ADMIN")
        self.errors = []
        self.app.report_callback_exception = lambda *args: self.errors.append(args)
        self.app.report_error = lambda exc: self.errors.append(exc)
        self.gateway = Mock()
        self.app.gateway = self.gateway
        self.types = ("SINGLE_CHOICE", "MULTIPLE_CHOICE", "TEXT", "NUMBER", "BOOLEAN", "ORDERING")
        self.quiz = dict(quiz_id=1, topic_id=1, title="Учебный тест", topic_title="Oracle", status="DRAFT",
                         access_mode="RESTRICTED", timer_mode="QUIZ", attempt_limit=2, show_feedback=1,
                         question_limit=None, selection_category_id=None, selection_difficulty_code=None)
        self.question = dict(question_id=10, seq_no=1, category_id=1, category_title="Категория",
                             question_text="Длинный вопрос. " * 20, type_code="SINGLE_CHOICE", points=1,
                             difficulty_name="Легкий", difficulty_code="EASY", explanation="Объяснение", expected_answer="1")
        self.result = dict(attempt_id=1, topic_title="Oracle", quiz_title="Учебный тест", status="FINISHED",
                           score_percent=50, awarded_points=3, max_points=6, correct_count=3, question_count=6,
                           comparison_code="BELOW", peer_average_percent=75, difference_pp=-25,
                           peer_user_count=2, peer_attempt_count=12, started_at="2026-09-18")
        self.gateway.admin_topics.return_value = [dict(topic_id=1, title="Oracle", category_count=1, quiz_count=1)]
        self.gateway.admin_categories.return_value = [dict(category_id=1, title="Категория", question_count=6)]
        self.gateway.admin_quizzes.side_effect = lambda _actor: [deepcopy(self.quiz)]
        self.gateway.dictionaries.return_value = (
            [dict(type_code=code, type_name=code, answer_mode="TEXT" if code in ("TEXT", "NUMBER") else "OPTIONS") for code in self.types],
            [dict(difficulty_code="EASY", difficulty_name="Легкий")],
        )
        self.gateway.admin_questions.return_value = [self.question]
        self.gateway.admin_question_options.return_value = [dict(option_text="Ответ", seq_no=1, is_correct=1)]
        self.gateway.selection_pool_count.return_value = 6
        self.gateway.users.return_value = [dict(user_id=1, login="student", full_name="Участник", role_code="USER", is_active=1)]
        self.gateway.quiz_access.return_value = []
        self.gateway.quiz_statistics.return_value = [dict(quiz_id=1, topic_title="Oracle", quiz_title="Учебный тест", attempts_count=12, average_score=50)]
        self.gateway.question_statistics.return_value = [dict(question_text="Вопрос", answer_count=12, correct_percent=50)]
        self.gateway.user_progress_summary.return_value = [dict(user_id=1, login="student", full_name="Участник", attempt_count=12)]
        self.gateway.user_quiz_progress.return_value = [dict(quiz_id=1, topic_title="Oracle", quiz_title="Учебный тест", attempt_count=12)]
        self.gateway.history.return_value = [self.result]
        self.gateway.attempt_result.return_value = self.result
        self.gateway.attempt_header.return_value = dict(show_feedback=1, timer_mode="QUIZ", status="IN_PROGRESS",
                                                       quiz_title="Учебный тест", remaining_seconds=1200)
        self.gateway.attempt_details.return_value = [dict(display_order=1, is_correct=1, question_text="Вопрос",
                                                         given_answer="1", correct_answer="1", explanation="Подробное пояснение " * 60)]
        self.gateway.question_options.return_value = [dict(option_id=i, option_text=f"Вариант {i}: " + "подробный текст " * 15) for i in range(1, 13)]

    def tearDown(self):
        self.settings_patch.stop()
        for callback in self.app.tk.splitlist(self.app.tk.call("after", "info")):
            self.app.after_cancel(callback)
        self.app.tk.call("tk", "scaling", self.scale)
        self.app.destroy()
        ui.messagebox.showinfo = self.app._messagebox_original_info
        ui.messagebox.showwarning = self.app._messagebox_original_warning

    def pump(self):
        self.app.update()
        self.app.update_idletasks()
        self.assertFalse(self.errors)

    def widgets(self, parent):
        for child in parent.winfo_children():
            yield child
            yield from self.widgets(child)

    def active(self, widget):
        while widget is not self.app:
            if not widget.winfo_manager():
                return False
            widget = widget.master
        return True

    def assert_reachable(self, widget):
        reveal_widget(widget)
        self.pump()
        self.assertTrue(widget.winfo_ismapped(), str(widget))
        parent = widget.master
        while parent:
            for axis, dimension in (("x", "width"), ("y", "height")):
                start = getattr(widget, f"winfo_root{axis}")()
                parent_start = getattr(parent, f"winfo_root{axis}")()
                size = getattr(widget, f"winfo_{dimension}")()
                parent_size = getattr(parent, f"winfo_{dimension}")()
                if size <= parent_size:
                    self.assertGreaterEqual(start, parent_start, str(widget))
                    self.assertLessEqual(start + size, parent_start + parent_size, str(widget))
            parent = parent.master

    def check_controls(self, parent):
        controls = [w for w in self.widgets(parent)
                    if isinstance(w, (ttk.Button, ttk.Entry, ttk.Combobox, ttk.Checkbutton, ttk.Radiobutton)) and self.active(w)]
        self.assertTrue(controls)
        for widget in controls:
            self.assert_reachable(widget)

    def test_connection_login_and_registration(self):
        for scale in (4 / 3, 2, 8 / 3):
            self.app.tk.call("tk", "scaling", scale)
            for page in (self.app.show_connection, self.app.show_login_page, self.app.show_register_page):
                with self.subTest(scale=scale, page=page.__name__):
                    page()
                    self.pump()
                    self.check_controls(self.app.page)

    def test_all_admin_sections(self):
        for scale in (4 / 3, 5 / 3, 2, 8 / 3):
            self.app.tk.call("tk", "scaling", scale)
            self.app.show_admin()
            self.pump()
            notebook = next(w for w in self.widgets(self.app.page) if isinstance(w, ttk.Notebook))
            section = next(w for w in self.widgets(self.app.page) if isinstance(w, ttk.Combobox) and len(w.cget("values")) == 8)
            self.assertEqual(len(section.cget("values")), 8)
            for size in ("1060x700", "1240x820", "1920x1080"):
                self.app.geometry(size + "+10000+10000")
                for index, tab in enumerate(notebook.tabs()):
                    with self.subTest(scale=scale, size=size, tab=notebook.tab(tab, "text")):
                        section.current(index)
                        section.event_generate("<<ComboboxSelected>>")
                        self.pump()
                        self.assertEqual(notebook.select(), tab)
                        area = self.app.nametowidget(tab)
                        if index == 5:
                            trees = [w for w in self.widgets(area) if isinstance(w, ttk.Treeview)]
                            trees[0].selection_set("1")
                            self.pump()
                            self.assertTrue(trees[1].get_children())
                            continue
                        self.check_controls(area)

    def test_results_and_history(self):
        for scale in (4 / 3, 8 / 3):
            self.app.tk.call("tk", "scaling", scale)
            for page in (lambda: self.app.show_result(1), self.app.show_history):
                page()
                self.pump()
                tree = next(w for w in self.widgets(self.app.page) if isinstance(w, ttk.Treeview))
                reveal_widget(tree)
                self.pump()
                self.assertTrue(tree.winfo_ismapped())
                self.check_controls(self.app.page)

    def test_question_editor_types_and_changed_button_caption(self):
        self.app.tk.call("tk", "scaling", 8 / 3)
        self.app.show_admin("Вопросы")
        self.pump()
        notebook = next(w for w in self.widgets(self.app.page) if isinstance(w, ttk.Notebook))
        area = self.app.nametowidget(notebook.select())
        type_combo = next(w for w in self.widgets(area) if isinstance(w, ttk.Combobox)
                          and w.cget("values") and str(w.cget("values")[0]).startswith("SINGLE_CHOICE"))
        for index in range(6):
            type_combo.current(index)
            type_combo.event_generate("<<ComboboxSelected>>")
            self.pump()
            self.check_controls(area)
        tree = next(w for w in self.widgets(area) if isinstance(w, ttk.Treeview))
        tree.selection_set("10")
        self.pump()
        save = next(w for w in self.widgets(area) if isinstance(w, ttk.Button) and w.cget("text") == "Сохранить изменения")
        self.assert_reachable(save)
        self.assertGreaterEqual(save.winfo_width(), save.winfo_reqwidth())
        clear = next(w for w in self.widgets(area) if isinstance(w, ttk.Button) and w.cget("text") == "Очистить форму")
        clear.invoke()
        self.pump()
        self.assertEqual(save.cget("text"), "Добавить вопрос")
        self.assert_reachable(save)

    def test_all_question_types_and_long_options(self):
        self.app.tk.call("tk", "scaling", 8 / 3)
        for code in self.types:
            with self.subTest(type=code):
                self.app.active_attempt_id = 1
                self.app.active_questions = [dict(self.question, type_code=code), self.question]
                self.app.active_index = 0
                self.app.show_question()
                self.pump()
                self.check_controls(self.app.page)
                area = self.app.page.master.master
                self.assertLess(area.canvas.yview()[1] - area.canvas.yview()[0], 1)
                if code == "NUMBER":
                    entry = next(w for w in self.widgets(self.app.page) if isinstance(w, ttk.Entry))
                    entry.insert(0, "12")
                    with patch.object(self.app, "show_question"):
                        button = next(w for w in self.widgets(self.app.page) if isinstance(w, ttk.Button) and w.cget("text") == "Сохранить ответ и дальше")
                        button.invoke()
                    self.gateway.submit_answer.assert_called_with(1, 10, "", "12")

    def test_focus_and_mousewheel_reveal_registration(self):
        reveal_widget(".combobox.popdown.f.l")
        self.app.tk.call("tk", "scaling", 8 / 3)
        self.app.show_register_page()
        self.pump()
        area = self.app.page.master.master
        button = next(w for w in self.widgets(self.app.page) if isinstance(w, ttk.Button) and w.cget("text") == "Создать учетную запись")
        area.canvas.yview_moveto(0)
        button.focus_force()
        self.pump()
        self.assertGreater(area.canvas.yview()[0], 0)
        self.assert_reachable(button)
        area.canvas.yview_moveto(0)
        label = next(w for w in self.widgets(self.app.page) if isinstance(w, ttk.Label))
        label.event_generate("<MouseWheel>", delta=-120)
        self.pump()
        self.assertGreater(area.canvas.yview()[0], 0)


if __name__ == "__main__":
    unittest.main()
