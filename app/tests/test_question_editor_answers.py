import tkinter as tk
import unittest
from tkinter import ttk
from unittest.mock import patch

import test_pages_layout as fixtures
from quiz_client import ui


class QuestionEditorAnswersTest(unittest.TestCase):
    tearDown = fixtures.PagesLayoutTest.tearDown
    pump = fixtures.PagesLayoutTest.pump
    widgets = fixtures.PagesLayoutTest.widgets

    def setUp(self):
        fixtures.PagesLayoutTest.setUp(self)
        self.app.clear_page()
        notebook = ttk.Notebook(self.app.page)
        notebook.pack(fill="both", expand=True)
        self.app.build_admin_question_editor(notebook)
        self.pump()
        widgets = list(self.widgets(notebook))
        self.type_box = next(w for w in widgets if isinstance(w, ttk.Combobox)
                             and any(str(v).startswith("SINGLE_CHOICE |") for v in w.cget("values")))
        self.options = next(w for w in widgets if isinstance(w, tk.Text))
        self.single = self.field("Правильный вариант (выберите один)", ttk.Combobox)
        self.multiple = self.field("Номера правильных вариантов через запятую (например, 1,3)", ttk.Entry)
        self.question_text = self.field("Текст вопроса", ttk.Entry)
        self.save = next(w for w in widgets if isinstance(w, ttk.Button) and w.cget("text") == "Добавить вопрос")
        self.tree = next(w for w in widgets if isinstance(w, ttk.Treeview))
        self.select_type("SINGLE_CHOICE")
        self.question_text.insert(0, "Choose one")
        self.set_options("First\nSecond\nThird")

    def field(self, label_text, widget_type):
        label = next(w for w in self.widgets(self.app.page) if isinstance(w, ttk.Label) and w.cget("text") == label_text)
        siblings = list(label.master.winfo_children())
        return next(w for w in siblings[siblings.index(label) + 1:] if isinstance(w, widget_type))

    def select_type(self, code):
        self.type_box.set(next(v for v in self.type_box.cget("values") if v.startswith(code + " |")))
        self.type_box.event_generate("<<ComboboxSelected>>")
        self.pump()

    def set_options(self, text):
        self.options.delete("1.0", "end")
        self.options.insert("1.0", text)
        self.pump()

    def submit(self):
        with patch.object(self.app, "show_admin"), patch.object(ui.messagebox, "showwarning") as warning:
            self.save.invoke()
        self.pump()
        return warning

    def test_single_choice_only_saves_one_correct_option(self):
        self.assertEqual(str(self.single.cget("state")), "readonly")
        self.assertTrue(self.single.master.winfo_manager())
        self.assertFalse(self.multiple.master.winfo_manager())
        self.multiple.insert(0, "1,2,3")
        self.single.current(1)
        self.submit().assert_not_called()
        self.assertEqual(self.gateway.create_question.call_args.args[-1],
                         [("First", 0), ("Second", 1), ("Third", 0)])

    def test_missing_or_invalid_single_selection_is_rejected(self):
        for selected in ("", "1,2"):
            with self.subTest(selected=selected):
                self.single.set(selected)
                self.submit().assert_called_once()
                self.gateway.create_question.assert_not_called()

    def test_changing_or_removing_selected_option_requires_reselection(self):
        self.single.current(1)
        self.set_options("First\nThird")
        self.assertEqual(self.single.get(), "")
        self.submit().assert_called_once()
        self.gateway.create_question.assert_not_called()

    def test_multiple_choice_and_invalid_numbers(self):
        self.select_type("MULTIPLE_CHOICE")
        self.assertTrue(self.multiple.master.winfo_manager())
        self.assertFalse(self.single.master.winfo_manager())
        for text in ("", "0", "4", "1,4", "1,no", "1,", "-1", "1.5"):
            with self.subTest(text=text):
                self.multiple.delete(0, "end")
                self.multiple.insert(0, text)
                self.submit().assert_called_once()
                self.gateway.create_question.assert_not_called()
        self.multiple.delete(0, "end")
        self.multiple.insert(0, "1,3")
        self.submit().assert_not_called()
        self.assertEqual(self.gateway.create_question.call_args.args[-1],
                         [("First", 1), ("Second", 0), ("Third", 1)])

    def test_at_least_two_options_required(self):
        for code in ("SINGLE_CHOICE", "MULTIPLE_CHOICE"):
            self.select_type(code)
            self.set_options("Only")
            self.single.current(0)
            self.multiple.delete(0, "end")
            self.multiple.insert(0, "1")
            self.submit().assert_called_once()
            self.gateway.create_question.assert_not_called()

    def test_editing_loads_one_answer_and_does_not_guess_for_legacy_invalid_data(self):
        self.gateway.admin_question_options.return_value = [
            dict(option_text="First", seq_no=1, is_correct=0),
            dict(option_text="Second", seq_no=2, is_correct=1),
        ]
        self.tree.selection_set("10")
        self.tree.event_generate("<<TreeviewSelect>>")
        self.pump()
        self.assertEqual(self.single.current(), 1)
        self.submit().assert_not_called()
        self.assertEqual(self.gateway.update_question.call_args.args[-1], [("First", 0), ("Second", 1)])
        self.gateway.update_question.reset_mock()
        self.gateway.admin_question_options.return_value[0]["is_correct"] = 1
        self.tree.event_generate("<<TreeviewSelect>>")
        self.pump()
        self.assertEqual(self.single.get(), "")
        self.submit().assert_called_once()
        self.gateway.update_question.assert_not_called()


if __name__ == "__main__":
    unittest.main()
