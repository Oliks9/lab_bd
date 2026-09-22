import unittest
from unittest.mock import MagicMock, patch

from quiz_client.database import OracleGateway, SessionUser


class ReportsGatewayTest(unittest.TestCase):
    def setUp(self):
        self.gateway = OracleGateway()
        self.connection = MagicMock()
        self.gateway.connection = self.connection
        self.command_context = MagicMock()
        self.result_context = MagicMock()
        self.connection.cursor.side_effect = [self.command_context, self.result_context]
        self.command = self.command_context.__enter__.return_value
        self.result = self.result_context.__enter__.return_value
        self.result.description = [("QUIZ_ID",), ("QUIZ_TITLE",)]
        self.result.fetchall.return_value = [(5, "Sample")]

    def test_cursor_is_converted_to_client_rows_without_committing(self):
        self.assertEqual(self.gateway.catalog(7, 9), [{"quiz_id": 5, "quiz_title": "Sample"}])
        self.command.callproc.assert_called_once_with("pkg_reports.catalog", [7, 9, self.result])
        self.command_context.__exit__.assert_called_once()
        self.result_context.__exit__.assert_called_once()
        self.connection.commit.assert_not_called()
        self.connection.rollback.assert_not_called()

    def test_empty_report(self):
        self.result.fetchall.return_value = []
        self.assertEqual(self.gateway.catalog(7), [])
        self.command.callproc.assert_called_once_with("pkg_reports.catalog", [7, None, self.result])

    def test_access_list_uses_protected_admin_cursor(self):
        self.result.description = [("USER_ID",), ("CAN_REVOKE",)]
        self.result.fetchall.return_value = [(3, 1)]
        self.assertEqual(self.gateway.quiz_access(7, 9), [{"user_id": 3, "can_revoke": 1}])
        self.command.callproc.assert_called_once_with("pkg_admin.list_quiz_access", [7, 9, self.result])
        self.connection.commit.assert_not_called()
        self.command_context.__exit__.assert_called_once()
        self.result_context.__exit__.assert_called_once()

    def test_access_list_failure_closes_cursors(self):
        self.command.callproc.side_effect = RuntimeError("Forbidden")
        with self.assertRaisesRegex(RuntimeError, "Forbidden"):
            self.gateway.quiz_access(7, 9)
        self.command_context.__exit__.assert_called_once()
        self.result_context.__exit__.assert_called_once()

    def test_database_error_closes_both_cursors(self):
        self.command.callproc.side_effect = RuntimeError("Oracle report failed")
        with self.assertRaisesRegex(RuntimeError, "Oracle report failed"):
            self.gateway.catalog(7)
        self.command_context.__exit__.assert_called_once()
        self.result_context.__exit__.assert_called_once()
        self.connection.commit.assert_not_called()

    def test_fetch_error_closes_both_cursors(self):
        self.result.fetchall.side_effect = RuntimeError("Fetch failed")
        with self.assertRaisesRegex(RuntimeError, "Fetch failed"):
            self.gateway.catalog(7)
        self.command_context.__exit__.assert_called_once()
        self.result_context.__exit__.assert_called_once()

    def test_all_report_routes_call_oracle(self):
        actor = SessionUser(7, "Author", "AUTHOR")
        cases = [
            (lambda: self.gateway.history(7), "history", [7]),
            (lambda: self.gateway.attempt_details(9), "attempt_details", [9]),
            (lambda: self.gateway.quiz_statistics(actor), "quiz_statistics", [7]),
            (lambda: self.gateway.question_statistics(5), "question_statistics", [5]),
        ]
        for call, name, arguments in cases:
            with self.subTest(name=name), patch.object(self.gateway, "_report_rows", return_value=[{}]) as report:
                self.assertEqual(call(), [{}])
                report.assert_called_once_with(name, arguments)
        with patch.object(self.gateway, "_report_rows", return_value=[{}]) as report:
            self.assertEqual(self.gateway.attempt_result(9), {})
            report.assert_called_once_with("attempt_result", [9])
        with patch.object(self.gateway, "_report_rows", return_value=[{}]) as report:
            self.assertEqual(self.gateway.leaderboard(), [{}])
            report.assert_called_once_with("leaderboard")


if __name__ == "__main__":
    unittest.main()
