from dataclasses import dataclass

try:
    import oracledb
except ImportError:
    oracledb = None


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
            raise DatabaseUnavailable("Модуль oracledb не установлен. Используйте собранное приложение или установите requirements.txt.")
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

    def authenticate(self, login: str, password: str) -> SessionUser:
        with self.connection.cursor() as cursor:
            user_id = cursor.var(int)
            full_name = cursor.var(str, size=200)
            role = cursor.var(str, size=20)
            cursor.callproc("pr_login", [login, password, user_id, full_name, role])
        return SessionUser(int(user_id.getvalue()), full_name.getvalue(), role.getvalue())

    def register(self, login: str, password: str, full_name: str) -> int:
        with self.connection.cursor() as cursor:
            user_id = cursor.var(int)
            cursor.callproc("pr_register_user", [login, password, full_name, user_id])
        self.connection.commit()
        return int(user_id.getvalue())

    def topics(self):
        return self._rows("SELECT topic_id, title FROM topics ORDER BY title")

    def catalog(self, user_id: int, topic_id=None):
        return self._rows(
            """
            SELECT quiz_id, topic_title, quiz_title, description, timer_mode, duration_minutes,
                   question_count, max_points, author_name, access_mode, status, attempt_limit
              FROM v_quiz_catalog
             WHERE fn_can_access_quiz(:user_id, quiz_id) = 1
               AND (:topic_id IS NULL OR topic_id = :topic_id)
             ORDER BY topic_title, quiz_title
            """,
            {"user_id": user_id, "topic_id": topic_id},
        )

    def start_attempt(self, user_id: int, quiz_id: int) -> int:
        with self.connection.cursor() as cursor:
            attempt_id = cursor.var(int)
            cursor.callproc("pkg_testing.start_attempt", [user_id, quiz_id, attempt_id])
        self.connection.commit()
        return int(attempt_id.getvalue())

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
            SELECT a.attempt_id, a.deadline_at, q.title AS quiz_title, q.show_feedback,
                   a.timer_mode, a.question_duration_minutes, a.active_question_order,
                   NVL(
                       GREATEST(
                           0,
                           ROUND(
                               (CAST(SYS_EXTRACT_UTC(a.deadline_at) AS DATE)
                               - CAST(SYS_EXTRACT_UTC(SYSTIMESTAMP) AS DATE)) * 86400
                           )
                       ),
                       0
                   ) AS remaining_seconds,
                   CASE
                       WHEN a.timer_mode = 'QUESTION'
                            AND a.question_started_at IS NOT NULL
                            AND a.question_duration_minutes IS NOT NULL THEN
                           GREATEST(
                               0,
                               ROUND(
                                   (
                                       CAST(SYS_EXTRACT_UTC(a.question_started_at + NUMTODSINTERVAL(a.question_duration_minutes, 'MINUTE')) AS DATE)
                                       - CAST(SYS_EXTRACT_UTC(SYSTIMESTAMP) AS DATE)
                                   ) * 86400
                               )
                           )
                       ELSE NULL
                   END AS question_remaining_seconds
              FROM attempts a JOIN quizzes q ON q.quiz_id = a.quiz_id
             WHERE a.attempt_id = :id
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

    def attempt_result(self, attempt_id: int):
        return self._rows("SELECT * FROM v_attempt_history WHERE attempt_id = :id", {"id": attempt_id})[0]

    def attempt_details(self, attempt_id: int):
        return self._rows(
            "SELECT * FROM v_attempt_details WHERE attempt_id = :id ORDER BY display_order",
            {"id": attempt_id},
        )

    def history(self, user_id: int):
        return self._rows(
            """
            SELECT attempt_id, topic_title, quiz_title, started_at, status,
                   score_percent, correct_count, question_count
              FROM v_attempt_history
             WHERE user_id = :id
             ORDER BY started_at DESC
            """,
            {"id": user_id},
        )

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
                   q.timer_mode, q.duration_minutes, q.show_feedback, q.attempt_limit
              FROM quizzes q JOIN topics t ON t.topic_id = q.topic_id
             WHERE :role = 'ADMIN' OR q.author_id = :actor_id
             ORDER BY q.created_at DESC
            """,
            {"role": actor.role_code, "actor_id": actor.user_id},
        )

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
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_admin.publish_quiz", [actor_id, quiz_id])
        self.connection.commit()

    def set_quiz_feedback(self, actor_id: int, quiz_id: int, show_feedback: int) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_admin.set_quiz_feedback", [actor_id, quiz_id, show_feedback])
        self.connection.commit()

    def set_quiz_attempt_limit(self, actor_id: int, quiz_id: int, attempt_limit: int | None) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_admin.set_quiz_attempt_limit", [actor_id, quiz_id, attempt_limit])
        self.connection.commit()

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
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_admin.delete_question", [admin_id, question_id])
        self.connection.commit()

    def delete_quiz(self, admin_id: int, quiz_id: int) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_admin.delete_quiz", [admin_id, quiz_id])
        self.connection.commit()

    def archive_quiz(self, admin_id: int, quiz_id: int) -> None:
        with self.connection.cursor() as cursor:
            cursor.callproc("pkg_admin.archive_quiz", [admin_id, quiz_id])
        self.connection.commit()

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

    def create_author(self, admin_id: int, login: str, password: str, full_name: str) -> int:
        with self.connection.cursor() as cursor:
            user_id = cursor.var(int)
            cursor.callproc("pkg_admin.create_author", [admin_id, login, password, full_name, user_id])
        self.connection.commit()
        return int(user_id.getvalue())

    def quiz_statistics(self, actor: SessionUser):
        return self._rows(
            """
            SELECT c.topic_title, c.quiz_title, c.quiz_id,
                   COUNT(h.attempt_id) AS attempts_count,
                   ROUND(AVG(h.score_percent), 2) AS average_score
              FROM v_quiz_catalog c
              JOIN quizzes q ON q.quiz_id = c.quiz_id
              LEFT JOIN v_attempt_history h
                ON h.quiz_id = c.quiz_id
               AND h.status IN ('FINISHED', 'EXPIRED')
             WHERE :role = 'ADMIN' OR q.author_id = :actor_id
             GROUP BY c.topic_title, c.quiz_title, c.quiz_id
             ORDER BY c.topic_title, c.quiz_title
            """,
            {"role": actor.role_code, "actor_id": actor.user_id},
        )

    def question_statistics(self, quiz_id: int):
        return self._rows(
            """
            SELECT question_text, answer_count, correct_percent
              FROM v_question_statistics
             WHERE quiz_id = :quiz_id
             ORDER BY question_id
            """,
            {"quiz_id": quiz_id},
        )

    def leaderboard(self):
        return self._rows(
            """
            SELECT full_name, attempts_finished, average_score, best_score
              FROM v_leaderboard
             ORDER BY average_score DESC NULLS LAST, best_score DESC NULLS LAST
            """
        )
