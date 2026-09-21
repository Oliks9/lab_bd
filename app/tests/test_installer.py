import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from quiz_client import installer, installation_ui


class InstallationTest(unittest.TestCase):
    def test_project_installation_is_fully_loaded(self):
        steps = installer.installation_steps()
        statements = [step for step in steps if step.sql]
        self.assertEqual(len(statements), 57)
        self.assertEqual(statements[0].file, "00_uninstall.sql")
        self.assertEqual(statements[-1].sql, "COMMIT")
        self.assertTrue(any("CREATE OR REPLACE PACKAGE BODY pkg_admin" in step.sql for step in steps))
        self.assertTrue(any("Администратор системы" in step.sql for step in steps))

    def test_nested_includes_quotes_and_plsql(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sub").mkdir()
            (root / "install.sql").write_text("SET DEFINE OFF\n@@sub/data.sql\nCOMMIT;", encoding="utf-8")
            (root / "sub" / "data.sql").write_text("PROMPT Data\nINSERT INTO t VALUES ('a;b''c');\nBEGIN\n NULL;\nEND;\n/", encoding="utf-8")
            steps = installer.installation_steps(root)
            self.assertEqual(steps[1].sql, "INSERT INTO t VALUES ('a;b''c')")
            self.assertEqual(steps[2].sql, "BEGIN\n NULL;\nEND;")
            self.assertEqual(steps[1].file, "sub/data.sql")

    def test_missing_invalid_and_escaping_includes_fail_before_connection(self):
        for text in ("@@missing.sql", "@@install.sql", "@@../outside.sql", "CONNECT other/password", "BEGIN\nNULL;", "SELECT 1 FROM dual"):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "install.sql").write_text(text, encoding="utf-8")
                with patch.object(installer, "sql_directory", return_value=root), patch.object(installer, "OracleGateway") as gateway:
                    with self.assertRaises((ValueError, OSError)):
                        installer.install_database("dsn", "schema", "secret", Mock())
                    gateway.assert_not_called()

    def test_frozen_resources_use_bundle_not_working_directory(self):
        with patch.object(installer.sys, "frozen", True, create=True), patch.object(installer.sys, "_MEIPASS", "bundle", create=True):
            self.assertEqual(installer.sql_directory(), Path("bundle") / "sql")

    def test_preflight_permissions_and_quota(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.__iter__.return_value = iter((p,) for p in ("CREATE SESSION", "CREATE TABLE", "CREATE SEQUENCE", "CREATE PROCEDURE", "CREATE TRIGGER"))
        cursor.fetchone.side_effect = [("SCHEMA", "SCHEMA"), ("USERS",), (0, 300 * 1024 * 1024)]
        installer.check_install_permissions(connection, "schema")
        connection.commit.assert_not_called()

    def test_wrong_schema_missing_privileges_or_quota_are_rejected(self):
        for kind in ("schema", "privileges", "quota"):
            with self.subTest(kind=kind):
                connection = MagicMock()
                cursor = connection.cursor.return_value.__enter__.return_value
                names = ("CREATE SESSION",) if kind == "privileges" else ("CREATE SESSION", "CREATE TABLE", "CREATE SEQUENCE", "CREATE PROCEDURE", "CREATE TRIGGER")
                cursor.__iter__.return_value = iter((p,) for p in names)
                cursor.fetchone.side_effect = [("OTHER" if kind == "schema" else "SCHEMA", "SCHEMA"), ("USERS",), None]
                with self.assertRaises(ValueError):
                    installer.check_install_permissions(connection, "schema")

    def test_execution_stops_at_first_error_with_location(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.execute.side_effect = RuntimeError("ORA error")
        steps = [installer.InstallStep("file.sql", 7, sql="bad"), installer.InstallStep("file.sql", 8, sql="never")]
        with self.assertRaisesRegex(RuntimeError, "file.sql:7"):
            installer.execute_installation(connection, steps, Mock())
        cursor.execute.assert_called_once_with("bad")
        connection.rollback.assert_called_once()
        connection.commit.assert_not_called()

    def test_denied_preflight_never_executes_install(self):
        with patch.object(installer, "OracleGateway") as gateway, patch.object(installer, "check_install_permissions", side_effect=ValueError("No rights")), patch.object(installer, "execute_installation") as execute:
            with self.assertRaises(ValueError):
                installer.install_database("dsn", "schema", "secret", Mock())
            execute.assert_not_called()
            gateway.return_value.close.assert_called_once()

    def test_confirmation_requires_both_steps_and_defaults_to_no(self):
        parent = Mock()
        with patch.object(installation_ui.messagebox, "askyesno", return_value=False) as ask, patch.object(installation_ui.simpledialog, "askstring") as typed:
            self.assertFalse(installation_ui.confirm_installation(parent, "localhost/db", "schema"))
            typed.assert_not_called()
            self.assertEqual(ask.call_args.kwargs["default"], "no")
        for value, expected in ((None, False), ("other", False), ("SCHEMA", True)):
            with patch.object(installation_ui.messagebox, "askyesno", return_value=True), patch.object(installation_ui.simpledialog, "askstring", return_value=value):
                self.assertEqual(installation_ui.confirm_installation(parent, "localhost/db", "schema"), expected)
