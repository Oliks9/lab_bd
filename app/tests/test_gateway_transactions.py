import unittest
from unittest.mock import MagicMock, call

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

    def test_quiz_settings_commit_together(self):
        self.gateway.save_quiz_settings(7, 9, 0, 2, "RESTRICTED")
        self.assertEqual(self.cursor.callproc.call_args_list, [
            call("pkg_admin.set_quiz_feedback", [7, 9, 0]),
            call("pkg_admin.set_quiz_attempt_limit", [7, 9, 2]),
            call("pkg_admin.set_quiz_access_mode", [7, 9, "RESTRICTED"]),
        ])
        self.connection.commit.assert_called_once()
        self.connection.rollback.assert_not_called()

    def test_access_error_rolls_back_all_quiz_settings(self):
        self.cursor.callproc.side_effect = [None, None, RuntimeError("Invalid access mode")]
        with self.assertRaisesRegex(RuntimeError, "Invalid access mode"):
            self.gateway.save_quiz_settings(7, 9, 0, 2, "invalid")
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()

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
            lambda: self.gateway.grant_access(7, 9, 3),
            lambda: self.gateway.revoke_access(7, 9, 3),
        ]
        for operation in operations:
            with self.subTest(operation=operation):
                self.connection.reset_mock()
                self.cursor.callproc.side_effect = RuntimeError("Oracle validation error")
                with self.assertRaisesRegex(RuntimeError, "Oracle validation error"):
                    operation()
                self.connection.rollback.assert_called_once()
                self.connection.commit.assert_not_called()

    def test_invalid_question_creation_rolls_back_all_options(self):
        self.cursor.var.return_value.getvalue.return_value = 10
        self.cursor.callproc.side_effect = [None, None, RuntimeError("Only one correct option")]
        with self.assertRaisesRegex(RuntimeError, "Only one correct option"):
            self.gateway.create_question(7, 9, 2, "SINGLE_CHOICE", "EASY", "Question", "", "", 1,
                                         [("First", 1), ("Second", 1)])
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()

    def test_revoke_access_commits_once(self):
        self.gateway.revoke_access(7, 9, 3)
        self.cursor.callproc.assert_called_once_with("pkg_admin.revoke_access", [7, 9, 3])
        self.connection.commit.assert_called_once()
        self.connection.rollback.assert_not_called()

    def test_invalid_question_edit_rolls_back_replacement(self):
        self.cursor.callproc.side_effect = [None, None, RuntimeError("Only one correct option")]
        with self.assertRaisesRegex(RuntimeError, "Only one correct option"):
            self.gateway.update_question(7, 10, 2, "SINGLE_CHOICE", "EASY", "Edited", "", "", 1,
                                         [("First", 1), ("Second", 1)])
        self.connection.rollback.assert_called_once()
        self.connection.commit.assert_not_called()

    def test_final_validation_failure_rolls_back_creation_and_editing(self):
        self.cursor.var.return_value.getvalue.return_value = 10
        operations = [
            lambda: self.gateway.create_question(7, 9, 2, "MULTIPLE_CHOICE", "EASY", "Question", "", "", 1,
                                                 [("First", 1), ("Second", 0)]),
            lambda: self.gateway.update_question(7, 10, 2, "MULTIPLE_CHOICE", "EASY", "Edited", "", "", 1,
                                                 [("First", 1), ("Second", 0)]),
        ]
        for operation in operations:
            self.connection.reset_mock()
            self.cursor.callproc.side_effect = [None, None, None, RuntimeError("At least two correct options")]
            with self.assertRaisesRegex(RuntimeError, "At least two correct options"):
                operation()
            self.cursor.callproc.assert_called_with("pkg_admin.validate_question", [7, 10])
            self.connection.rollback.assert_called_once()
            self.connection.commit.assert_not_called()

    def test_valid_question_is_checked_by_oracle_before_commit(self):
        self.cursor.var.return_value.getvalue.return_value = 10
        operations = [
            lambda: self.gateway.create_question(7, 9, 2, "MULTIPLE_CHOICE", "EASY", "Question", "", "", 1,
                                                 [("First", 1), ("Second", 1)]),
            lambda: self.gateway.update_question(7, 10, 2, "MULTIPLE_CHOICE", "EASY", "Edited", "", "", 1,
                                                 [("First", 1), ("Second", 1)]),
        ]
        for operation in operations:
            self.connection.reset_mock()
            self.cursor.callproc.side_effect = None
            operation()
            self.cursor.callproc.assert_called_with("pkg_admin.validate_question", [7, 10])
            self.connection.commit.assert_called_once()
            self.connection.rollback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
