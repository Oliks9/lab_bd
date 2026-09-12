"""Tk selection controls with an in-memory gateway; no Oracle data is modified."""
import unittest
from copy import deepcopy
from tkinter import ttk
from unittest.mock import patch

from quiz_client import ui
from quiz_client.config import ConnectionSettings
from quiz_client.database import SessionUser


class SelectionGateway:
    def __init__(self):
        self.rows = [dict(quiz_id=1, topic_id=1, title="Test", status="DRAFT",
                         question_limit=None, selection_category_id=None, selection_difficulty_code=None)]
        self.saved = []
        self.categories = [dict(category_id=10, title="Category")]

    def dictionaries(self):
        return [], [dict(difficulty_name="Easy", difficulty_code="EASY")]

    def admin_quizzes(self, _actor):
        return deepcopy(self.rows)

    def admin_categories(self, _topic):
        return self.categories

    def selection_pool_count(self, *_args):
        return 5

    def set_quiz_selection(self, *args):
        self.saved.append(args)
        _, _, count, category, difficulty = args
        self.rows[0].update(question_limit=count, selection_category_id=category, selection_difficulty_code=difficulty)

    def close(self):
        pass


class SelectionUITest(unittest.TestCase):
    def setUp(self):
        with patch.object(ui, "load_settings", return_value=ConnectionSettings()):
            self.app = ui.QuizApplication()
        self.app.geometry("1060x700+10000+10000")
        self.app.clear_page()
        self.app.user = SessionUser(7, "Author", "AUTHOR")
        self.app.gateway = SelectionGateway()
        self.errors = []
        self.app.report_error = lambda exc: self.errors.append(str(exc))
        self.app.heading("Студия тестов", "Настройки тестов")
        self.notebook = ttk.Notebook(self.app.page)
        self.notebook.pack(fill="both", expand=True)
        self.app.build_admin_selection(self.notebook)
        self.pump()

    def tearDown(self):
        for callback in self.app.tk.splitlist(self.app.tk.call("after", "info")):
            self.app.after_cancel(callback)
        self.app.destroy()

    def pump(self):
        self.app.update()
        self.app.update_idletasks()

    def widgets(self, parent=None):
        for child in (parent or self.notebook).winfo_children():
            yield child
            yield from self.widgets(child)

    def by_text(self, text):
        return next(w for w in self.widgets() if "text" in w.keys() and w.cget("text") == text)

    def test_filtered_save_and_all_reset(self):
        self.by_text("Случайные N по категории и сложности").invoke()
        entry = next(w for w in self.widgets() if type(w) is ttk.Entry)
        entry.delete(0, "end")
        entry.insert(0, "3")
        self.by_text("Сохранить подбор").invoke()
        self.pump()
        self.assertEqual(self.app.gateway.saved[-1], (7, 1, 3, 10, "EASY"))
        self.assertEqual(entry.get(), "3")
        self.by_text("Все вопросы по порядку").invoke()
        self.by_text("Сохранить подбор").invoke()
        self.assertEqual(self.app.gateway.saved[-1], (7, 1, None, None, None))
        self.assertFalse(self.errors)

    def test_invalid_input_and_published_readonly(self):
        self.by_text("Случайные N по категории и сложности").invoke()
        entry = next(w for w in self.widgets() if type(w) is ttk.Entry)
        entry.delete(0, "end")
        entry.insert(0, "abc")
        self.by_text("Сохранить подбор").invoke()
        self.assertTrue(self.errors)
        self.assertFalse(self.app.gateway.saved)
        self.app.gateway.rows[0]["status"] = "PUBLISHED"
        self.by_text("Обновить данные").invoke()
        self.assertTrue(self.by_text("Сохранить подбор").instate(["disabled"]))

    def test_refresh_and_empty_list(self):
        self.app.gateway.categories.append(dict(category_id=11, title="New category"))
        self.by_text("Обновить данные").invoke()
        combos = [w for w in self.widgets() if isinstance(w, ttk.Combobox)]
        self.assertIn("New category", combos[1]["values"])
        self.app.gateway.rows.clear()
        self.by_text("Обновить данные").invoke()
        self.assertTrue(self.by_text("Сохранить подбор").instate(["disabled"]))
        self.assertFalse(self.errors)

    def test_controls_fit_minimum_window(self):
        for w in self.widgets():
            if isinstance(w, (ttk.Button, ttk.Entry, ttk.Combobox, ttk.Radiobutton, ttk.Label)):
                self.assertTrue(w.winfo_ismapped(), str(w))
                self.assertLessEqual(w.winfo_rooty() + w.winfo_height(), self.app.winfo_rooty() + 700)
                self.assertLessEqual(w.winfo_rootx() + w.winfo_width(), self.app.winfo_rootx() + 1060)


if __name__ == "__main__":
    unittest.main()
