import builtins
import importlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quiz_client import database, diagnostics


class RuntimeDiagnosticsTest(unittest.TestCase):
    def setUp(self):
        for name in ("oracledb", "cryptography", "tkinter", "installation_sql"):
            patcher = patch.object(diagnostics, f"check_{name}", return_value={"version": "test"})
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)
        self.output = patch.object(diagnostics.sys, "stdout", new=io.StringIO())
        self.output.start()
        self.addCleanup(self.output.stop)

    def test_successful_report_is_written_and_marks_frozen_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dependency report.json"
            with patch.object(diagnostics.sys, "frozen", True, create=True):
                self.assertEqual(diagnostics.run_self_check(path), 0)
            report = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(report["ok"])
        self.assertTrue(report["frozen"])
        self.assertIn(report["architecture_bits"], (32, 64))
        self.assertEqual(set(report["checks"]), {"oracledb", "cryptography", "tkinter", "installation_sql"})
        self.assertTrue(all(check["ok"] for check in report["checks"].values()))

    def test_failed_import_keeps_details_and_runs_remaining_checks(self):
        self.oracledb.side_effect = ImportError("DLL load failed while importing base_impl")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "failed.json"
            self.assertEqual(diagnostics.run_self_check(path), 1)
            report = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(report["ok"])
        failure = report["checks"]["oracledb"]
        self.assertFalse(failure["ok"])
        self.assertEqual(failure["error"], "ImportError: DLL load failed while importing base_impl")
        self.assertIn("Traceback", failure["traceback"])
        self.cryptography.assert_called_once()
        self.tkinter.assert_called_once()

    def test_crypto_failure_is_not_masked_by_successful_driver_import(self):
        self.cryptography.side_effect = ModuleNotFoundError("No module named '_cffi_backend'")
        report = diagnostics.collect_runtime_report()
        self.assertFalse(report["ok"])
        self.assertTrue(report["checks"]["oracledb"]["ok"])
        self.assertIn("_cffi_backend", report["checks"]["cryptography"]["error"])

    def test_report_is_written_without_console_streams(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "windowed.json"
            with patch.object(diagnostics.sys, "stdout", None), patch.object(diagnostics.sys, "stderr", None):
                self.assertEqual(diagnostics.run_self_check(path), 0)
            self.assertTrue(path.is_file())

    def test_unwritable_report_returns_distinct_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing-parent" / "report.json"
            with patch.object(diagnostics.sys, "stderr", new=io.StringIO()) as output:
                self.assertEqual(diagnostics.run_self_check(path), 2)
                self.assertIn("Cannot write dependency report", output.getvalue())


class DriverImportErrorTest(unittest.TestCase):
    def test_gateway_keeps_original_nested_import_error(self):
        original_import = builtins.__import__

        def failed_driver_import(name, *args, **kwargs):
            if name == "oracledb":
                raise ImportError("DLL load failed while importing thin_impl")
            return original_import(name, *args, **kwargs)

        try:
            with patch("builtins.__import__", side_effect=failed_driver_import):
                importlib.reload(database)
            self.assertIsNone(database.oracledb)
            self.assertEqual(database.ORACLEDB_IMPORT_ERROR, "ImportError: DLL load failed while importing thin_impl")
            with self.assertRaisesRegex(database.DatabaseUnavailable, "DLL load failed while importing thin_impl"):
                database.OracleGateway().connect("unused", "unused", "unused")
        finally:
            importlib.reload(database)


if __name__ == "__main__":
    unittest.main()
