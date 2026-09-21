import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from quiz_client import config


class ConnectionSettingsTest(unittest.TestCase):
    def test_sid_and_service_roundtrip(self):
        for mode in ("SID", "SERVICE_NAME"):
            dsn = config.build_connection_dsn("10.22.10.64", "1521", "orcl", mode)
            self.assertEqual(config.parse_connection_dsn(dsn), config.OracleAddress("10.22.10.64", 1521, "orcl", mode))
            self.assertIn("10.22.10.64:1521", config.connection_label(dsn))

    def test_easy_connect_defaults_and_ipv6(self):
        for value in ("localhost/FREEPDB1", "//localhost:1521/FREEPDB1", "localhost:1521/FREEPDB1"):
            self.assertEqual(config.parse_connection_dsn(value), config.OracleAddress())
        dsn = config.build_connection_dsn("[::1]", "1521", "orcl", "SID")
        self.assertEqual(config.parse_connection_dsn(dsn).host, "::1")
        self.assertEqual(config.parse_connection_dsn("[::1]:1521/orcl").database, "orcl")

    def test_invalid_values_rejected(self):
        for host, port, database, mode in (("", "1521", "db", "SID"), ("bad host", "1521", "db", "SID"),
                                           ("server", "0", "db", "SID"), ("server", "65536", "db", "SID"),
                                           ("server", "abc", "db", "SID"), ("server", "1521", "", "SID"),
                                           ("server", "1521", "db)(SID=other", "SID"), ("server", "1521", "db", "OTHER")):
            with self.subTest(host=host, port=port, database=database, mode=mode), self.assertRaises(ValueError):
                config.build_connection_dsn(host, port, database, mode)

    def test_advanced_dsn_not_silently_rewritten(self):
        for dsn in ("my_tns_alias", "tcps://server/db?wallet_location=wallet", "server:1521/db?retry_count=3",
                    "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=bad host)(PORT=1521))(CONNECT_DATA=(SID=db)))"):
            self.assertIsNone(config.parse_connection_dsn(dsn))
        dsn = "(DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = server)(PORT = 1521))(CONNECT_DATA = (SID = db)))"
        self.assertEqual(config.parse_connection_dsn(dsn).host, "server")

    def test_legacy_settings_and_password_not_saved(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(config, "settings_path", return_value=Path(directory) / "connection.json"):
            settings = config.ConnectionSettings("//server:1521/db", "my_schema")
            config.save_settings(settings)
            self.assertEqual(config.load_settings(), settings)
            data = json.loads(config.settings_path().read_text(encoding="utf-8"))
            self.assertEqual(set(data), {"dsn", "schema_user"})
            for value in ("[]", '{"dsn": null, "schema_user": 3}', "bad json"):
                config.settings_path().write_text(value, encoding="utf-8")
                self.assertEqual(config.load_settings(), config.ConnectionSettings())
