"""Catalog layout regressions, independent of Oracle and the Windows desktop size."""
import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import patch

from quiz_client import ui
from quiz_client.config import ConnectionSettings
from quiz_client.database import SessionUser


class CatalogGateway:
    def __init__(self):
        self.rows = [dict(quiz_id=1, topic_title="Oracle", quiz_title="Oracle: основы серверной логики",
                         description="Демонстрационный тест с разными форматами ответа.",
                         question_count=6, duration_minutes=20, max_points=8,
                         author_name="Администратор системы", timer_mode="QUIZ", attempt_limit=None,
                         status="PUBLISHED", access_mode="PUBLIC", selection_category_id=None)]
        self.started = []

    def topics(self):
        return [dict(topic_id=1, title="Oracle"), dict(topic_id=2, title="Empty")]

    def catalog(self, _user_id, topic_id=None):
        return [] if topic_id == 2 else self.rows

    def start_attempt(self, user_id, quiz_id):
        self.started.append((user_id, quiz_id))
        return 99

    def close(self):
        pass


class CatalogLayoutTest(unittest.TestCase):
    def setUp(self):
        with patch.object(ui, "load_settings", return_value=ConnectionSettings()):
            self.app = ui.QuizApplication()
        self.original_scaling = self.app.tk.call("tk", "scaling")
        self.app.geometry("1060x700+10000+10000")
        self.app.gateway = CatalogGateway()
        self.app.user = SessionUser(7, "Администратор системы", "ADMIN")
        self.errors = []
        self.app.report_callback_exception = lambda *args: self.errors.append(args)
        self.app.report_error = lambda exc: self.errors.append(exc)

    def tearDown(self):
        for callback in self.app.tk.splitlist(self.app.tk.call("after", "info")):
            self.app.after_cancel(callback)
        self.app.tk.call("tk", "scaling", self.original_scaling)
        self.app.destroy()

    def pump(self):
        self.app.update()
        self.app.update_idletasks()
        self.assertFalse(self.errors)

    def widgets(self, parent=None):
        for child in (parent or self.app.page).winfo_children():
            yield child
            yield from self.widgets(child)

    def start_button(self):
        return next(w for w in self.widgets() if isinstance(w, ttk.Button)
                    and w.cget("text") == "Начать выбранный тест")

    def assert_unclipped(self, widget):
        self.assertTrue(widget.winfo_ismapped())
        self.assertGreaterEqual(widget.winfo_height(), widget.winfo_reqheight())
        self.assertGreaterEqual(widget.winfo_width(), widget.winfo_reqwidth())
        parent = widget.master
        while parent:
            self.assertGreaterEqual(widget.winfo_rooty(), parent.winfo_rooty())
            self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), parent.winfo_rooty() + parent.winfo_height())
            self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(), parent.winfo_rootx() + parent.winfo_width())
            parent = parent.master

    def test_start_button_at_window_sizes_and_scales(self):
        for scale in (4 / 3, 5 / 3, 2, 8 / 3):
            for size in ("1060x700", "1240x820", "1920x1080"):
                with self.subTest(scale=scale, size=size):
                    self.app.tk.call("tk", "scaling", scale)
                    self.app.geometry(size + "+10000+10000")
                    self.app.show_catalog()
                    self.pump()
                    self.assert_unclipped(self.start_button())
                    tree = next(w for w in self.widgets() if isinstance(w, ttk.Treeview))
                    bounds = tree.bbox("1")
                    self.assertTrue(bounds, "At least one catalog row must remain visible")
                    self.assertLessEqual(bounds[1] + bounds[3], tree.winfo_height())

    def test_long_text_is_scrollable_and_start_stays_visible(self):
        self.app.gateway.rows[0].update(quiz_title="Длинное название " * 12, description="Описание вопросника. " * 50,
                                       timer_mode="QUESTION", max_points=None, selection_category_id=1,
                                       selection_category_title="Категория", selection_difficulty_name="Средняя")
        self.app.show_catalog()
        self.pump()
        self.assert_unclipped(self.start_button())
        canvas = next(w for w in self.widgets() if isinstance(w, tk.Canvas))
        self.assertLess(canvas.yview()[1], 1)
        canvas.event_generate("<MouseWheel>", delta=-120)
        self.pump()
        self.assertGreater(canvas.yview()[0], 0)
        canvas.yview_moveto(1)
        self.pump()
        self.assertAlmostEqual(canvas.yview()[1], 1)
        self.assert_unclipped(self.start_button())

    def test_filter_empty_state_and_start_callback(self):
        self.app.show_catalog()
        self.pump()
        calls = []
        self.app.start_quiz_screen = calls.append
        self.start_button().invoke()
        self.assertEqual(self.app.gateway.started, [(7, 1)])
        self.assertEqual(calls, [99])
        combo = next(w for w in self.widgets() if isinstance(w, ttk.Combobox))
        combo.set("Empty")
        combo.event_generate("<<ComboboxSelected>>")
        self.pump()
        self.assertTrue(self.start_button().instate(["disabled"]))
        combo.set("Все тематики")
        combo.event_generate("<<ComboboxSelected>>")
        self.pump()
        self.assertFalse(self.start_button().instate(["disabled"]))
        self.assert_unclipped(self.start_button())
        canvas = next(w for w in self.widgets() if isinstance(w, tk.Canvas))
        self.assertAlmostEqual(canvas.yview()[0], 0)


if __name__ == "__main__":
    unittest.main()
