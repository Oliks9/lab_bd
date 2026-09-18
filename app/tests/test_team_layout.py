import tkinter as tk
import unittest
from itertools import combinations
from tkinter import ttk
from unittest.mock import Mock, patch

from quiz_client import ui
from quiz_client.config import ConnectionSettings
from quiz_client.database import SessionUser
from quiz_client.layout import reveal_widget


class TeamLayoutTest(unittest.TestCase):
    actions = (
        "Назначить автором", "Сделать участником", "Сменить пароль",
        "Отключить", "Включить", "Удалить пользователя",
    )

    def setUp(self):
        with patch.object(ui, "load_settings", return_value=ConnectionSettings()):
            self.app = ui.QuizApplication()
        self.original_scaling = self.app.tk.call("tk", "scaling")
        self.app.geometry("1060x700+10000+10000")
        self.app.user = SessionUser(7, "Администратор системы", "ADMIN")
        self.gateway = Mock()
        self.gateway.users.return_value = [
            dict(user_id=i, login=f"user{i}", full_name=f"Участник {i}", role_code="USER", is_active=i % 2)
            for i in range(1, 81)
        ]
        self.app.gateway = self.gateway
        self.errors = []
        self.app.report_callback_exception = lambda *args: self.errors.append(args)
        self.app.report_error = lambda exc: self.errors.append(exc)
        self.app.show_admin = Mock()
        self.info_patch = patch.object(ui.messagebox, "showinfo")
        self.info_patch.start()
        self.build_team()

    def tearDown(self):
        self.info_patch.stop()
        for callback in self.app.tk.splitlist(self.app.tk.call("after", "info")):
            self.app.after_cancel(callback)
        self.app.tk.call("tk", "scaling", self.original_scaling)
        self.app.destroy()
        ui.messagebox.showinfo = self.app._messagebox_original_info
        ui.messagebox.showwarning = self.app._messagebox_original_warning

    def build_team(self):
        self.app.clear_page()
        self.app.heading("Студия тестов", "Администратор: материалы, вопросы, публикация и результаты в одном рабочем пространстве.")
        self.notebook = ttk.Notebook(self.app.page)
        self.notebook.pack(fill="both", expand=True)
        self.app.build_admin_users(self.notebook)
        self.pump()
        self.tree = next(w for w in self.widgets() if isinstance(w, ttk.Treeview))

    def pump(self):
        self.app.update()
        self.app.update_idletasks()
        self.assertFalse(self.errors)

    def widgets(self, parent=None):
        for child in (parent or self.notebook).winfo_children():
            yield child
            yield from self.widgets(child)

    def button(self, text, parent=None):
        return next(w for w in self.widgets(parent) if isinstance(w, ttk.Button) and w.cget("text") == text)

    def dialog(self):
        return next(w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel))

    def select(self, user_id="1"):
        self.tree.selection_set(user_id)
        self.pump()

    def assert_unclipped(self, widget):
        self.assertTrue(widget.winfo_ismapped(), str(widget))
        self.assertGreaterEqual(widget.winfo_width(), widget.winfo_reqwidth())
        self.assertGreaterEqual(widget.winfo_height(), widget.winfo_reqheight())
        parent = widget.master
        while parent:
            self.assertGreaterEqual(widget.winfo_rootx(), parent.winfo_rootx())
            self.assertGreaterEqual(widget.winfo_rooty(), parent.winfo_rooty())
            self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(), parent.winfo_rootx() + parent.winfo_width())
            self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), parent.winfo_rooty() + parent.winfo_height())
            parent = parent.master

    def test_actions_fit_window_sizes_and_scales(self):
        for scale in (4 / 3, 5 / 3, 2, 8 / 3):
            self.app.tk.call("tk", "scaling", scale)
            self.build_team()
            self.select()
            for size in ("1060x700", "1920x1080", "1240x820", "1060x700"):
                with self.subTest(scale=scale, size=size):
                    self.app.geometry(size + "+10000+10000")
                    self.pump()
                    buttons = [self.button(text) for text in (*self.actions, "Добавить автора")]
                    for button in buttons:
                        reveal_widget(button)
                        self.pump()
                        self.assert_unclipped(button)
                    for first, second in combinations(buttons, 2):
                        self.assertTrue(
                            first.winfo_rootx() + first.winfo_width() <= second.winfo_rootx()
                            or second.winfo_rootx() + second.winfo_width() <= first.winfo_rootx()
                            or first.winfo_rooty() + first.winfo_height() <= second.winfo_rooty()
                            or second.winfo_rooty() + second.winfo_height() <= first.winfo_rooty()
                        )
                    reveal_widget(self.tree)
                    self.pump()
                    bounds = self.tree.bbox("1")
                    self.assertTrue(bounds, "At least one user row must remain visible")
                    self.assertLessEqual(bounds[1] + bounds[3], self.tree.winfo_height())

    def test_selection_empty_state_and_scrollbars(self):
        for text in self.actions:
            self.assertTrue(self.button(text).instate(["disabled"]))
        self.select()
        for text in self.actions:
            self.assertFalse(self.button(text).instate(["disabled"]))
        self.assertEqual(str(self.tree.cget("selectmode")), "browse")
        self.assertLess(self.tree.yview()[1], 1)
        self.tree.yview_moveto(1)
        self.pump()
        self.assertTrue(self.tree.bbox("80"))
        self.tree.column("name", width=1400, minwidth=1400)
        self.pump()
        self.assertLess(self.tree.xview()[1], 1)
        self.tree.xview_moveto(1)
        self.pump()
        self.assertGreater(self.tree.xview()[0], 0)
        for scrollbar in (w for w in self.widgets() if isinstance(w, ttk.Scrollbar)):
            self.assertTrue(scrollbar.winfo_ismapped())
        self.gateway.users.return_value = []
        self.build_team()
        for text in self.actions:
            self.assertTrue(self.button(text).instate(["disabled"]))
        self.assertFalse(self.button("Добавить автора").instate(["disabled"]))

    def test_create_author_validation_and_preserved_tab(self):
        self.button("Добавить автора").invoke()
        self.pump()
        dialog = self.dialog()
        self.button("Создать автора", dialog).invoke()
        self.gateway.create_author.assert_not_called()
        entries = [w for w in self.widgets(dialog) if isinstance(w, ttk.Entry)]
        for entry, value in zip(entries, (" Автор ", " author_new ", "Temporary123!")):
            entry.insert(0, value)
        self.assertEqual(str(entries[2].cget("show")), "*")
        self.gateway.create_author.side_effect = RuntimeError("Логин уже занят")
        self.button("Создать автора", dialog).invoke()
        self.pump()
        self.assertTrue(dialog.winfo_exists())
        self.assertTrue(any(isinstance(w, ttk.Label) and w.cget("text") == "Логин уже занят" for w in self.widgets(dialog)))
        self.gateway.create_author.side_effect = None
        self.button("Создать автора", dialog).invoke()
        self.pump()
        self.gateway.create_author.assert_called_with(7, "author_new", "Temporary123!", "Автор")
        self.app.show_admin.assert_called_once_with("Команда")
        self.assertFalse(dialog.winfo_exists())
        self.assertIsNone(self.app.grab_current())

    def test_password_validation_error_and_captured_user(self):
        self.select()
        self.button("Сменить пароль").invoke()
        self.pump()
        dialog = self.dialog()
        self.assertIn("user1", dialog.title())
        entry = next(w for w in self.widgets(dialog) if isinstance(w, ttk.Entry))
        self.assertEqual(str(entry.cget("show")), "*")
        entry.insert(0, "123")
        self.button("Сохранить пароль", dialog).invoke()
        self.gateway.set_user_password.assert_not_called()
        self.pump()
        self.assertTrue(dialog.winfo_exists())
        entry.delete(0, "end")
        entry.insert(0, "NewSecret123!")
        self.gateway.set_user_password.side_effect = RuntimeError("Нет доступа")
        self.button("Сохранить пароль", dialog).invoke()
        self.pump()
        self.assertTrue(dialog.winfo_exists())
        self.gateway.set_user_password.side_effect = None
        self.tree.selection_set("2")
        self.button("Сохранить пароль", dialog).invoke()
        self.pump()
        self.gateway.set_user_password.assert_called_with(7, 1, "NewSecret123!")
        self.assertFalse(dialog.winfo_exists())
        self.app.show_admin.assert_not_called()

    def test_dialog_keyboard_and_layout_at_high_dpi(self):
        self.app.tk.call("tk", "scaling", 8 / 3)
        self.build_team()
        self.button("Добавить автора").invoke()
        self.pump()
        dialog = self.dialog()
        for widget in self.widgets(dialog):
            if isinstance(widget, (ttk.Entry, ttk.Button)):
                self.assert_unclipped(widget)
        dialog.focus_force()
        self.pump()
        dialog.event_generate("<Escape>")
        self.pump()
        self.assertFalse(dialog.winfo_exists())
        self.gateway.create_author.assert_not_called()
        self.select()
        self.button("Сменить пароль").invoke()
        self.pump()
        dialog = self.dialog()
        entry = next(w for w in self.widgets(dialog) if isinstance(w, ttk.Entry))
        entry.insert(0, "Keyboard123!")
        entry.focus_force()
        self.pump()
        entry.event_generate("<Return>")
        self.pump()
        self.gateway.set_user_password.assert_called_once_with(7, 1, "Keyboard123!")
        self.assertFalse(dialog.winfo_exists())

    def test_role_activation_and_delete_callbacks(self):
        self.select()
        self.button("Назначить автором").invoke()
        self.gateway.set_role.assert_called_with(7, 1, "AUTHOR")
        self.button("Сделать участником").invoke()
        self.gateway.set_role.assert_called_with(7, 1, "USER")
        with patch.object(ui.messagebox, "askyesno", return_value=False):
            self.button("Отключить").invoke()
            self.button("Удалить пользователя").invoke()
        self.gateway.set_user_active.assert_not_called()
        self.gateway.delete_user.assert_not_called()
        with patch.object(ui.messagebox, "askyesno", return_value=True):
            self.button("Отключить").invoke()
            self.gateway.set_user_active.assert_called_with(7, 1, 0)
            self.select("2")
            self.button("Включить").invoke()
            self.gateway.set_user_active.assert_called_with(7, 2, 1)
            self.button("Удалить пользователя").invoke()
            self.gateway.delete_user.assert_called_once_with(7, 2)
        self.assertEqual(self.app.show_admin.call_count, 5)
        self.assertTrue(all(call.args == ("Команда",) for call in self.app.show_admin.call_args_list))


if __name__ == "__main__":
    unittest.main()
