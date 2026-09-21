import tempfile
import threading
import time
import unittest
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

import test_pages_layout as fixtures
from quiz_client import installation_ui


class InstallationDialogTest(unittest.TestCase):
    setUp = fixtures.PagesLayoutTest.setUp
    tearDown = fixtures.PagesLayoutTest.tearDown
    widgets = fixtures.PagesLayoutTest.widgets

    def run_dialog(self, failure):
        release = threading.Event()
        with tempfile.TemporaryDirectory() as directory:
            def install(dsn, user, password, report):
                release.wait(5)
                report("test output", 1, 2)
                if failure:
                    raise RuntimeError("Failure containing " + password)
                report("complete", 2, 2)

            with patch.object(installation_ui, "confirm_installation", return_value=True), patch.object(installation_ui, "install_database", side_effect=install), patch.object(installation_ui, "settings_path", return_value=Path(directory) / "connection.json"):
                installation_ui.open_installation(self.app, "dsn", "schema", "secret_password")
                self.assertTrue(self.app.installation_busy)
                self.app.destroy()
                self.assertTrue(self.app.winfo_exists())
                close = next(w for w in self.widgets(self.app) if isinstance(w, ttk.Button) and str(w.cget("text")) == "Закрыть")
                self.assertTrue(close.instate(["disabled"]))
                release.set()
                deadline = time.monotonic() + 8
                while self.app.installation_busy and time.monotonic() < deadline:
                    self.app.update()
                    time.sleep(0.02)
                self.assertFalse(self.app.installation_busy)
                self.assertFalse(close.instate(["disabled"]))
                self.assertFalse(self.errors)
                log = next((Path(directory) / "install_logs").glob("*.log")).read_text(encoding="utf-8")
                self.assertIn("test output", log)
                self.assertNotIn("secret_password", log)
                if failure:
                    self.assertIn("[скрыто]", log)
                close.invoke()

    def test_background_success_and_close_guard(self):
        self.run_dialog(False)

    def test_background_failure_and_secret_redaction(self):
        self.run_dialog(True)
