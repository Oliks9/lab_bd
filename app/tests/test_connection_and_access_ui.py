import unittest
from tkinter import ttk
from unittest.mock import Mock, patch

import test_pages_layout as fixtures
from quiz_client import ui
from quiz_client.config import ConnectionSettings, build_connection_dsn


class ConnectionAndAccessTest(unittest.TestCase):
    setUp = fixtures.PagesLayoutTest.setUp
    tearDown = fixtures.PagesLayoutTest.tearDown
    widgets = fixtures.PagesLayoutTest.widgets
    pump = fixtures.PagesLayoutTest.pump

    def field(self, caption):
        label = next(w for w in self.widgets(self.app) if isinstance(w, ttk.Label) and str(w.cget("text")) == caption)
        siblings = label.master.winfo_children()
        return siblings[siblings.index(label) + 1]

    def button(self, text):
        return next(w for w in self.widgets(self.app) if isinstance(w, ttk.Button) and str(w.cget("text")) == text)

    def fill(self, widget, value):
        widget.delete(0, "end")
        widget.insert(0, value)

    def test_sid_connection_fields_and_saved_settings(self):
        dsn = build_connection_dsn("10.22.10.64", "1521", "orcl", "SID")
        with patch.object(ui, "load_settings", return_value=ConnectionSettings(dsn, "KA2105_01")), patch.object(ui, "save_settings") as saved:
            self.app.show_connection()
            self.pump()
            self.assertEqual(self.field("Сервер (IP-адрес или имя)").get(), "10.22.10.64")
            self.assertEqual(self.field("Тип подключения").get(), "SID")
            self.assertEqual(self.field("SID базы данных").get(), "orcl")
            self.fill(self.field("Пароль схемы Oracle"), "test_password")
            self.app.show_login_page = Mock()
            self.button("Подключиться").invoke()
            self.gateway.connect.assert_called_once_with(dsn, "KA2105_01", "test_password")
            saved.assert_called_once_with(ConnectionSettings(dsn, "KA2105_01"))
            self.app.show_login_page.assert_called_once()

    def test_invalid_port_prevents_connection(self):
        self.app.show_connection()
        self.fill(self.field("Порт"), "70000")
        self.fill(self.field("Пароль схемы Oracle"), "password")
        self.button("Подключиться").invoke()
        self.gateway.connect.assert_not_called()
        self.assertEqual(len(self.errors), 1)

    def test_install_button_uses_entered_credentials(self):
        self.app.show_connection()
        self.fill(self.field("Пароль схемы Oracle"), "password")
        with patch.object(ui, "open_installation") as install:
            self.button("Установить базу приложения (install.sql)").invoke()
            install.assert_called_once_with(self.app, build_connection_dsn("localhost", "1521", "FREEPDB1", "SERVICE_NAME"), "quiz_app", "password")
        self.gateway.connect.assert_not_called()

    def test_install_without_password_is_not_started(self):
        self.app.show_connection()
        with patch.object(ui, "open_installation") as install:
            self.button("Установить базу приложения (install.sql)").invoke()
            install.assert_not_called()
        self.assertEqual(len(self.errors), 1)

    def test_advanced_connection_is_preserved(self):
        dsn = "my_tns_alias"
        with patch.object(ui, "load_settings", return_value=ConnectionSettings(dsn, "schema")), patch.object(ui, "save_settings"):
            self.app.show_connection()
            self.assertEqual(self.field("Готовая строка подключения (DSN)").get(), dsn)
            self.fill(self.field("Пароль схемы Oracle"), "password")
            self.app.show_login_page = Mock()
            self.button("Подключиться").invoke()
            self.gateway.connect.assert_called_once_with(dsn, "schema", "password")

    def publication(self):
        self.app.clear_page(scrollable=True)
        notebook = ttk.Notebook(self.app.page)
        notebook.pack(fill="both", expand=True)
        self.app.build_admin_publication(notebook)
        tree = next(w for w in self.widgets(notebook) if isinstance(w, ttk.Treeview))
        tree.selection_set("1")
        self.pump()
        self.app.show_admin = Mock()
        return self.field("Доступ к тесту")

    def test_draft_access_saved_with_other_settings(self):
        access = self.publication()
        self.assertEqual(access.get(), ui.ACCESS_NAMES["RESTRICTED"])
        access.set(ui.ACCESS_NAMES["PUBLIC"])
        with patch.object(ui.messagebox, "showinfo"):
            self.button("Сохранить настройки").invoke()
        self.gateway.save_quiz_settings.assert_called_once_with(7, 1, 1, 2, "PUBLIC")
        self.app.show_admin.assert_called_once_with("Публикация")

    def test_publish_saves_selected_access_first(self):
        access = self.publication()
        access.set(ui.ACCESS_NAMES["PUBLIC"])
        with patch.object(ui.messagebox, "showinfo"):
            self.button("Опубликовать выбранный тест").invoke()
        self.gateway.save_quiz_settings.assert_called_once_with(7, 1, 1, 2, "PUBLIC")
        self.gateway.publish_quiz.assert_called_once_with(7, 1)
        methods = [call[0] for call in self.gateway.mock_calls]
        self.assertLess(methods.index("save_quiz_settings"), methods.index("publish_quiz"))

    def test_published_access_disabled(self):
        self.quiz["status"] = "PUBLISHED"
        access = self.publication()
        self.assertTrue(access.instate(["disabled"]))
        self.assertTrue(self.button("Сохранить настройки").instate(["disabled"]))

    def test_save_failure_does_not_publish(self):
        self.publication()
        self.gateway.save_quiz_settings.side_effect = RuntimeError("Server rejected settings")
        self.button("Опубликовать выбранный тест").invoke()
        self.gateway.publish_quiz.assert_not_called()
        self.app.show_admin.assert_not_called()
        self.assertEqual(len(self.errors), 1)
