import unittest
from unittest.mock import MagicMock

from quiz_client.database import OracleGateway


class GatewayTransactionTest(unittest.TestCase):
    def setUp(self):
        self.gateway = OracleGateway()
        self.connection = MagicMock()
        self.gateway.connection = self.connection
        self.cursor = self.connection.cursor.return_value.__enter__.return_value

    def test_selection_parameters_and_commit(self):
        self.gateway.set_quiz_selection(7, 9, 3, 10, "EASY")
        self.cursor.callproc.assert_called_once_with("pkg_admin.set_quiz_selection", [7, 9, 3, 10, "EASY"])
        self.connection.commit.assert_called_once()
        self.connection.rollback.assert_not_called()

    def test_failed_mutations_release_locks(self):
        operations = [
            lambda: self.gateway.set_quiz_selection(7, 9, 3, 10, "EASY"),
            lambda: self.gateway.start_attempt(7, 9),
            lambda: self.gateway.publish_quiz(7, 9),
            lambda: self.gateway.delete_question(7, 9),
            lambda: self.gateway.delete_quiz(7, 9),
            lambda: self.gateway.archive_quiz(7, 9),
            lambda: self.gateway.set_quiz_feedback(7, 9, 1),
            lambda: self.gateway.set_quiz_attempt_limit(7, 9, 1),
        ]
        for operation in operations:
            with self.subTest(operation=operation):
                self.connection.reset_mock()
                self.cursor.callproc.side_effect = RuntimeError("Oracle validation error")
                with self.assertRaisesRegex(RuntimeError, "Oracle validation error"):
                    operation()
                self.connection.rollback.assert_called_once()
                self.connection.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
