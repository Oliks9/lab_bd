from dataclasses import dataclass

ORACLEDB_IMPORT_ERROR = None

try:
    import oracledb
except ImportError as exc:
    oracledb = None
    ORACLEDB_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"


@dataclass
class SessionUser:
    user_id: int
    full_name: str
    role_code: str


class DatabaseUnavailable(RuntimeError):
    pass


class OracleGateway:
    def __init__(self):
        self.connection = None

    def connect(self, dsn: str, schema_user: str, schema_password: str) -> None:
        if oracledb is None:
            raise DatabaseUnavailable(
                "Не удалось загрузить драйвер Oracle (oracledb). "
                "Причиной может быть отсутствие пакета, его зависимости или DLL.\n\n"
                f"Подробности: {ORACLEDB_IMPORT_ERROR}\n\n"
                "Для EXE выполните диагностику --self-check и пересоберите приложение "
                "через build/build_exe.ps1. Установка пакетов в Python сама по себе "
                "не изменяет уже собранный EXE."
            )
        self.connection = oracledb.connect(user=schema_user, password=schema_password, dsn=dsn)

    def close(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None

    def _rows(self, sql: str, params=None):
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params or {})
            columns = [column[0].lower() for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _report_rows(self, name: str, params=()):
        with self.connection.cursor() as cursor, self.connection.cursor() as result:
            cursor.callproc(f"pkg_reports.{name}", [*params, result])
            columns = [column[0].lower() for column in result.description]
            return [dict(zip(columns, row)) for row in result.fetchall()]

    def authenticate(self, login: str, password: str) -> SessionUser:
        with self.connection.cursor() as cursor:
            user_id = cursor.var(int)
            full_name = cursor.var(str, size=200)
            role = cursor.var(str, size=20)
            cursor.callproc("pr_login", [login, password, user_id, full_name, role])
            resolved_user_id = int(user_id.getvalue())
        self.connection.commit()
        return SessionUser(resolved_user_id, full_name.getvalue(), role.getvalue())

    def register(self, login: str, password: str, full_name: str) -> int:
        with self.connection.cursor() as cursor:
            user_id = cursor.var(int)
            cursor.callproc("pr_register_user", [login, password, full_name, user_id])
        self.connection.commit()
        return int(user_id.getvalue())

    def topics(self):
        return self._rows("SELECT topic_id, title FROM topics ORDER BY title")

    def catalog(self, user_id: int, topic_id=None):
        return self._report_rows("catalog", [user_id, topic_id])

    def start_attempt(self, user_id: int, quiz_id: int) -> int:
        try:
            with self.connection.cursor() as cursor:
                attempt_id = cursor.var(int)
                cursor.callproc("pkg_testing.start_attempt", [user_id, quiz_id, attempt_id])
            self.connection.commit()
            return int(attempt_id.getvalue())
        except Exception:
            self.connection.rollback()
            raise

    def attempt_questions(self, attempt_id: int):
        return self._rows(
            """
            SELECT aq.display_order, q.question_id, q.question_text, q.type_code,
                   qt.type_name, q.points, c.title AS category_title,
                   d.difficulty_name
              FROM attempt_questions aq
              JOIN questions q ON q.question_id = aq.question_id
              JOIN question_types qt ON qt.type_code = q.type_code
              JOIN categories c ON c.category_id = q.category_id
              JOIN difficulty_levels d ON d.difficulty_code = q.difficulty_code
             WHERE aq.attempt_id = :attempt_id
             ORDER BY aq.display_order
            """,
            {"attempt_id": attempt_id},
        )

    def question_options(self, question_id: int):
        return self._rows(
            "SELECT option_id, option_text FROM question_options WHERE question_id = :id ORDER BY seq_no",
            {"id": question_id},
        )

    def attempt_header(self, attempt_id: int):
        return self._rows(
            """
            WITH clocks AS (
                SELECT a.*,
                       a.deadline_at - SYSTIMESTAMP AS quiz_left,
                       a.question_started_at + NUMTODSINTERVAL(a.question_duration_minutes, 'MINUTE')
                           - SYSTIMESTAMP AS question_left
                  FROM attempts a WHERE a.attempt_id = :id
            )
            SELECT a.attempt_id, a.status, a.deadline_at, q.title AS quiz_title, q.show_feedback,
                   a.timer_mode, a.question_duration_minutes, a.active_question_order,
                   NVL(GREATEST(0, CEIL(
                       EXTRACT(DAY FROM a.quiz_left) * 86400
                       + EXTRACT(HOUR FROM a.quiz_left) * 3600
                       + EXTRACT(MINUTE FROM a.quiz_left) * 60
                       + EXTRACT(SECOND FROM a.quiz_left)
                   )), 0) AS remaining_seconds,
                   CASE
                       WHEN a.timer_mode = 'QUESTION'
                            AND a.question_started_at IS NOT NULL
                            AND a.question_duration_minutes IS NOT NULL THEN
                           GREATEST(0, CEIL(
                               EXTRACT(DAY FROM a.question_left) * 86400
                               + EXTRACT(HOUR FROM a.question_left) * 3600
                               + EXTRACT(MINUTE FROM a.question_left) * 60
                               + EXTRACT(SECOND FROM a.question_left)
                           ))
                       ELSE NULL
                   END AS question_remaining_seconds
              FROM clocks a JOIN quizzes q ON q.quiz_id = a.quiz_id
            """,
            {"id": attempt_id},
        )[0]

    def submit_answer(self, attempt_id: int, question_id: int, selected_ids: str, text_answer: str) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_testing.submit_answer", [attempt_id, question_id, selected_ids, text_answer])
        self.connection.commit()

    def expire_question(self, attempt_id: int) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_testing.expire_question", [attempt_id])
        self.connection.commit()

    def finish_attempt(self, attempt_id: int) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_testing.finish_attempt", [attempt_id])
        self.connection.commit()

    def abandon_attempt(self, attempt_id: int) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_testing.abandon_attempt", [attempt_id])
        self.connection.commit()

    def abandon_user_attempts(self, user_id: int) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_testing.abandon_user_attempts", [user_id])
        self.connection.commit()

    def attempt_result(self, attempt_id: int):
        return self._report_rows("attempt_result", [attempt_id])[0]

    def attempt_details(self, attempt_id: int):
        return self._report_rows("attempt_details", [attempt_id])

    def history(self, user_id: int):
        return self._report_rows("history", [user_id])

    def admin_topics(self):
        return self._rows(
            """
            SELECT t.topic_id, t.title, t.description,
                   (SELECT COUNT(*) FROM categories c WHERE c.topic_id = t.topic_id) AS category_count,
                   (SELECT COUNT(*) FROM quizzes q WHERE q.topic_id = t.topic_id) AS quiz_count
              FROM topics t
             ORDER BY t.title
            """
        )

    def admin_categories(self, topic_id=None):
        return self._rows(
            """
            SELECT c.category_id, c.topic_id, c.title, t.title AS topic_title,
                   (SELECT COUNT(*) FROM questions q WHERE q.category_id = c.category_id) AS question_count
              FROM categories c JOIN topics t ON t.topic_id = c.topic_id
             WHERE (:topic_id IS NULL OR c.topic_id = :topic_id)
             ORDER BY t.title, c.title
            """,
            {"topic_id": topic_id},
        )

    def admin_quizzes(self, actor: SessionUser):
        return self._rows(
            """
            SELECT q.quiz_id, q.topic_id, t.title AS topic_title, q.title, q.status, q.access_mode,
                   q.timer_mode, q.duration_minutes, q.show_feedback, q.attempt_limit,
                   q.question_limit, q.selection_category_id, q.selection_difficulty_code
              FROM quizzes q JOIN topics t ON t.topic_id = q.topic_id
             WHERE EXISTS (
                 SELECT 1 FROM app_users u WHERE u.user_id = :actor_id
                   AND u.is_active = 1 AND u.role_code IN ('ADMIN', 'AUTHOR')
                   AND (u.role_code = 'ADMIN' OR q.author_id = u.user_id)
             )
             ORDER BY q.created_at DESC
            """,
            {"actor_id": actor.user_id},
        )

    def selection_pool_count(self, actor_id: int, quiz_id: int, category_id=None, difficulty_code=None):
        rows = self._rows(
            """
            SELECT fn_quiz_pool_count(q.quiz_id, :category_id, :difficulty_code) AS pool_count
              FROM quizzes q JOIN app_users u ON u.user_id = :actor_id
             WHERE q.quiz_id = :quiz_id AND u.is_active = 1
               AND (u.role_code = 'ADMIN' OR (u.role_code = 'AUTHOR' AND q.author_id = u.user_id))
            """,
            {"actor_id": actor_id, "quiz_id": quiz_id, "category_id": category_id, "difficulty_code": difficulty_code},
        )
        if not rows:
            raise ValueError("Тест недоступен для редактирования.")
        return rows[0]["pool_count"]

    def set_quiz_selection(self, actor_id: int, quiz_id: int, question_limit, category_id, difficulty_code):
        try:
            with self.connection.cursor() as cursor:
                cursor.callproc("pkg_admin.set_quiz_selection", [actor_id, quiz_id, question_limit, category_id, difficulty_code])
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def admin_questions(self, quiz_id: int):
        return self._rows(
            """
            SELECT q.question_id, q.seq_no, q.category_id, q.question_text, q.type_code,
                   q.difficulty_code, q.expected_answer, q.explanation, q.points
              FROM questions q
             WHERE q.quiz_id = :quiz_id
             ORDER BY q.seq_no
            """,
            {"quiz_id": quiz_id},
        )

    def admin_question_options(self, question_id: int):
        return self._rows(
            """
            SELECT option_id, seq_no, option_text, is_correct
              FROM question_options
             WHERE question_id = :question_id
             ORDER BY seq_no
            """,
            {"question_id": question_id},
        )

    def dictionaries(self):
        return (
            self._rows("SELECT type_code, type_name, answer_mode FROM question_types ORDER BY type_name"),
            self._rows("SELECT difficulty_code, difficulty_name FROM difficulty_levels ORDER BY level_order"),
        )

    def create_topic(self, actor_id: int, title: str, description: str) -> int:
        with self.connection.cursor() as cursor:
            value = cursor.var(int)
            cursor.callproc("pkg_admin.create_topic", [actor_id, title, description, value])
        self.connection.commit()
        return int(value.getvalue())

    def create_category(self, actor_id: int, topic_id: int, title: str) -> int:
        with self.connection.cursor() as cursor:
            value = cursor.var(int)
            cursor.callproc("pkg_admin.create_category", [actor_id, topic_id, title, value])
        self.connection.commit()
        return int(value.getvalue())

    def create_quiz(
        self,
        actor_id: int,
        topic_id: int,
        title: str,
        description: str,
        timer_mode: str,
        duration: int,
        attempt_limit: int | None,
        show_feedback: int,
        access_mode: str,
    ) -> int:
        with self.connection.cursor() as cursor:
            value = cursor.var(int)
            cursor.callproc(
                "pkg_admin.create_quiz",
                [actor_id, topic_id, title, description, timer_mode, duration, attempt_limit, show_feedback, access_mode, value],
            )
        self.connection.commit()
        return int(value.getvalue())

    def create_question(self, actor_id: int, quiz_id: int, category_id: int, type_code: str, difficulty_code: str, text: str, expected: str, explanation: str, points: float, options):
        try:
            with self.connection.cursor() as cursor:
                question_id = cursor.var(int)
                cursor.callproc(
                    "pkg_admin.add_question",
                    [actor_id, quiz_id, category_id, type_code, difficulty_code, text, expected or None, explanation or None, points, question_id],
                )
                created_id = int(question_id.getvalue())
                for option_text, is_correct in options:
                    option_id = cursor.var(int)
                    cursor.callproc("pkg_admin.add_option", [actor_id, created_id, option_text, is_correct, option_id])
            self.connection.commit()
            return created_id
        except Exception:
            self.connection.rollback()
            raise

    def update_question(self, actor_id: int, question_id: int, category_id: int, type_code: str, difficulty_code: str, text: str, expected: str, explanation: str, points: float, options):
        try:
            with self.connection.cursor() as cursor:
                cursor.callproc(
                    "pkg_admin.update_question",
                    [actor_id, question_id, category_id, type_code, difficulty_code, text, expected or None, explanation or None, points],
                )
                for option_text, is_correct in options:
                    option_id = cursor.var(int)
                    cursor.callproc("pkg_admin.add_option", [actor_id, question_id, option_text, is_correct, option_id])
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def publish_quiz(self, actor_id: int, quiz_id: int) -> None:
        self._commit_procedure("pkg_admin.publish_quiz", [actor_id, quiz_id])

    def _commit_procedure(self, name, params):
        try:
            with self.connection.cursor() as cursor:
                cursor.callproc(name, params)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def set_quiz_feedback(self, actor_id: int, quiz_id: int, show_feedback: int) -> None:
        self._commit_procedure("pkg_admin.set_quiz_feedback", [actor_id, quiz_id, show_feedback])

    def set_quiz_attempt_limit(self, actor_id: int, quiz_id: int, attempt_limit: int | None) -> None:
        self._commit_procedure("pkg_admin.set_quiz_attempt_limit", [actor_id, quiz_id, attempt_limit])

    def grant_access(self, actor_id: int, quiz_id: int, user_id: int) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_admin.grant_access", [actor_id, quiz_id, user_id])
        self.connection.commit()

    def delete_category(self, admin_id: int, category_id: int) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_admin.delete_category", [admin_id, category_id])
        self.connection.commit()

    def delete_topic(self, admin_id: int, topic_id: int) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_admin.delete_topic", [admin_id, topic_id])
        self.connection.commit()

    def delete_question(self, admin_id: int, question_id: int) -> None:
        self._commit_procedure("pkg_admin.delete_question", [admin_id, question_id])

    def delete_quiz(self, admin_id: int, quiz_id: int) -> None:
        self._commit_procedure("pkg_admin.delete_quiz", [admin_id, quiz_id])

    def archive_quiz(self, admin_id: int, quiz_id: int) -> None:
        self._commit_procedure("pkg_admin.archive_quiz", [admin_id, quiz_id])

    def reset_user_quiz_attempts(self, admin_id: int, user_id: int, quiz_id: int) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_admin.reset_user_quiz_attempts", [admin_id, user_id, quiz_id])
        self.connection.commit()

    def reset_user_progress(self, admin_id: int, user_id: int) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_admin.reset_user_progress", [admin_id, user_id])
        self.connection.commit()

    def users(self):
        return self._rows(
            "SELECT user_id, login, full_name, role_code, is_active, created_at FROM app_users ORDER BY created_at DESC"
        )

    def user_progress_summary(self):
        return self._rows(
            """
            SELECT u.user_id, u.login, u.full_name, u.role_code,
                   COUNT(a.attempt_id) AS attempt_count,
                   MAX(a.started_at) AS last_attempt
              FROM app_users u
              LEFT JOIN attempts a ON a.user_id = u.user_id
             GROUP BY u.user_id, u.login, u.full_name, u.role_code
             ORDER BY u.full_name
            """
        )

    def user_quiz_progress(self, user_id: int):
        return self._rows(
            """
            SELECT q.quiz_id, t.title AS topic_title, q.title AS quiz_title,
                   COUNT(a.attempt_id) AS attempt_count,
                   MAX(a.started_at) AS last_attempt
              FROM attempts a
              JOIN quizzes q ON q.quiz_id = a.quiz_id
              JOIN topics t ON t.topic_id = q.topic_id
             WHERE a.user_id = :user_id
             GROUP BY q.quiz_id, t.title, q.title
             ORDER BY MAX(a.started_at) DESC
            """,
            {"user_id": user_id},
        )

    def set_role(self, admin_id: int, user_id: int, role_code: str) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_admin.set_user_role", [admin_id, user_id, role_code])
        self.connection.commit()

    def set_user_password(self, admin_id: int, user_id: int, new_password: str) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_admin.set_user_password", [admin_id, user_id, new_password])
        self.connection.commit()

    def set_user_active(self, admin_id: int, user_id: int, is_active: int) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_admin.set_user_active", [admin_id, user_id, is_active])
        self.connection.commit()

    def delete_user(self, admin_id: int, user_id: int) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_admin.delete_user", [admin_id, user_id])
        self.connection.commit()

    def create_author(self, admin_id: int, login: str, password: str, full_name: str) -> int:
        with self.connection.cursor() as cursor:
            user_id = cursor.var(int)
            cursor.callproc("pkg_admin.create_author", [admin_id, login, password, full_name, user_id])
        self.connection.commit()
        return int(user_id.getvalue())

    def quiz_statistics(self, actor: SessionUser):
        return self._report_rows("quiz_statistics", [actor.user_id])

    def question_statistics(self, quiz_id: int):
        return self._report_rows("question_statistics", [quiz_id])

    def leaderboard(self):
        return self._report_rows("leaderboard")
