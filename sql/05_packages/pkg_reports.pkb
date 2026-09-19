CREATE OR REPLACE PACKAGE BODY pkg_reports AS
    PROCEDURE catalog(p_user_id IN NUMBER, p_topic_id IN NUMBER, p_rows OUT SYS_REFCURSOR) IS
    BEGIN
        OPEN p_rows FOR
            WITH ranked_questions AS (
                SELECT qu.*, ROW_NUMBER() OVER (PARTITION BY quiz_id ORDER BY seq_no) AS question_order
                  FROM questions qu
            )
            SELECT
                q.quiz_id,
                q.topic_id,
                t.title AS topic_title,
                q.title AS quiz_title,
                q.description,
                q.timer_mode,
                q.duration_minutes,
                q.attempt_limit,
                q.show_feedback,
                q.access_mode,
                q.status,
                u.full_name AS author_name,
                CASE WHEN q.selection_category_id IS NOT NULL THEN q.question_limit
                     ELSE COUNT(qu.question_id) END AS question_count,
                CASE WHEN q.selection_category_id IS NULL THEN NVL(SUM(qu.points), 0) END AS max_points,
                q.selection_category_id,
                c.title AS selection_category_title,
                d.difficulty_name AS selection_difficulty_name,
                COUNT(qu.question_id) AS pool_count
            FROM quizzes q
            JOIN topics t ON t.topic_id = q.topic_id
            JOIN app_users u ON u.user_id = q.author_id
            LEFT JOIN categories c ON c.category_id = q.selection_category_id
            LEFT JOIN difficulty_levels d ON d.difficulty_code = q.selection_difficulty_code
            LEFT JOIN ranked_questions qu ON qu.quiz_id = q.quiz_id
                AND (q.selection_category_id IS NULL OR qu.category_id = q.selection_category_id)
                AND (q.selection_difficulty_code IS NULL OR qu.difficulty_code = q.selection_difficulty_code)
                AND (q.selection_category_id IS NOT NULL OR q.question_limit IS NULL OR qu.question_order <= q.question_limit)
            WHERE fn_can_access_quiz(p_user_id, q.quiz_id) = 1
              AND (p_topic_id IS NULL OR q.topic_id = p_topic_id)
            GROUP BY
                q.quiz_id, q.topic_id, t.title, q.title, q.description, q.timer_mode, q.duration_minutes, q.attempt_limit,
                q.show_feedback, q.access_mode, q.status, u.full_name,
                q.selection_category_id, q.question_limit, c.title, d.difficulty_name
            ORDER BY t.title, q.title;
    END catalog;

    PROCEDURE history(p_user_id IN NUMBER, p_rows OUT SYS_REFCURSOR) IS
    BEGIN
        OPEN p_rows FOR
            SELECT
                a.attempt_id,
                a.user_id,
                au.login,
                au.full_name,
                a.quiz_id,
                q.title AS quiz_title,
                t.title AS topic_title,
                a.started_at,
                a.deadline_at,
                a.finished_at,
                a.status,
                a.awarded_points,
                a.max_points,
                a.score_percent,
                (SELECT COUNT(*) FROM attempt_questions aq WHERE aq.attempt_id = a.attempt_id) AS question_count,
                (SELECT COUNT(*) FROM user_answers ua WHERE ua.attempt_id = a.attempt_id AND ua.is_correct = 1) AS correct_count
            FROM attempts a
            JOIN app_users au ON au.user_id = a.user_id
            JOIN quizzes q ON q.quiz_id = a.quiz_id
            JOIN topics t ON t.topic_id = q.topic_id
            WHERE a.user_id = p_user_id
            ORDER BY a.started_at DESC;
    END history;

    PROCEDURE attempt_result(p_attempt_id IN NUMBER, p_rows OUT SYS_REFCURSOR) IS
    BEGIN
        OPEN p_rows FOR
            WITH history AS (
                SELECT
                    a.attempt_id,
                    a.user_id,
                    au.login,
                    au.full_name,
                    a.quiz_id,
                    q.title AS quiz_title,
                    t.title AS topic_title,
                    a.started_at,
                    a.deadline_at,
                    a.finished_at,
                    a.status,
                    a.awarded_points,
                    a.max_points,
                    a.score_percent,
                    (SELECT COUNT(*) FROM attempt_questions aq WHERE aq.attempt_id = a.attempt_id) AS question_count,
                    (SELECT COUNT(*) FROM user_answers ua WHERE ua.attempt_id = a.attempt_id AND ua.is_correct = 1) AS correct_count
                FROM attempts a
                JOIN app_users au ON au.user_id = a.user_id
                JOIN quizzes q ON q.quiz_id = a.quiz_id
                JOIN topics t ON t.topic_id = q.topic_id
            ), user_scores AS (
                SELECT quiz_id, user_id, COUNT(*) AS attempt_count, SUM(score_percent) AS total_score
                  FROM attempts
                 WHERE status IN ('FINISHED', 'EXPIRED')
                   AND score_percent IS NOT NULL
                   AND max_points > 0
                 GROUP BY quiz_id, user_id
            ), quiz_scores AS (
                SELECT quiz_id, COUNT(*) AS user_count,
                       SUM(attempt_count) AS attempt_count, SUM(total_score) AS total_score
                  FROM user_scores
                 GROUP BY quiz_id
            ), baselines AS (
                SELECT a.attempt_id, a.user_id, a.quiz_id, a.status, a.score_percent, a.max_points,
                       NVL(q.attempt_count, 0) - NVL(u.attempt_count, 0) AS peer_attempt_count,
                       NVL(q.user_count, 0) - CASE WHEN u.user_id IS NOT NULL THEN 1 ELSE 0 END AS peer_user_count,
                       CASE WHEN a.status IN ('FINISHED', 'EXPIRED')
                                 AND a.score_percent IS NOT NULL AND a.max_points > 0 THEN
                           ROUND((q.total_score - NVL(u.total_score, 0))
                               / NULLIF(q.attempt_count - NVL(u.attempt_count, 0), 0), 2)
                       END AS peer_average_percent
                  FROM attempts a
                  LEFT JOIN quiz_scores q ON q.quiz_id = a.quiz_id
                  LEFT JOIN user_scores u ON u.quiz_id = a.quiz_id AND u.user_id = a.user_id
            ), differences AS (
                SELECT b.*, ROUND(score_percent - peer_average_percent, 2) AS difference_pp
                  FROM baselines b
            )
            SELECT h.*, c.peer_average_percent, c.difference_pp,
                   c.peer_attempt_count, c.peer_user_count,
                   CASE
                       WHEN c.status = 'IN_PROGRESS' THEN 'IN_PROGRESS'
                       WHEN c.score_percent IS NULL OR c.max_points IS NULL OR c.max_points <= 0 THEN 'NO_SCORE'
                       WHEN c.peer_attempt_count = 0 THEN 'NO_PEERS'
                       WHEN c.difference_pp > 0 THEN 'ABOVE'
                       WHEN c.difference_pp < 0 THEN 'BELOW'
                       ELSE 'EQUAL'
                   END AS comparison_code
              FROM history h JOIN differences c ON c.attempt_id = h.attempt_id
             WHERE h.attempt_id = p_attempt_id;
    END attempt_result;

    PROCEDURE attempt_details(p_attempt_id IN NUMBER, p_rows OUT SYS_REFCURSOR) IS
    BEGIN
        OPEN p_rows FOR
            SELECT
                aq.attempt_id,
                aq.display_order,
                q.question_id,
                q.question_text,
                q.type_code,
                CASE WHEN quiz.show_feedback = 1 AND a.status IN ('FINISHED', 'EXPIRED')
                     THEN q.explanation END AS explanation,
                q.points,
                ua.text_answer,
                ua.is_correct,
                ua.awarded_points,
                CASE
                    WHEN q.type_code = 'ORDERING' THEN
                        (SELECT LISTAGG(qo.option_text, ' -> ') WITHIN GROUP (ORDER BY x.item_order)
                           FROM (
                                SELECT TO_NUMBER(REGEXP_SUBSTR(ua.text_answer, '[^,]+', 1, LEVEL)) AS option_id,
                                       LEVEL AS item_order
                                  FROM dual
                                CONNECT BY REGEXP_SUBSTR(ua.text_answer, '[^,]+', 1, LEVEL) IS NOT NULL
                           ) x
                           JOIN question_options qo
                             ON qo.question_id = q.question_id
                            AND qo.option_id = x.option_id)
                    WHEN q.type_code IN ('SINGLE_CHOICE', 'MULTIPLE_CHOICE', 'BOOLEAN') THEN
                        (SELECT LISTAGG(qo.option_text, '; ') WITHIN GROUP (ORDER BY qo.seq_no)
                           FROM answer_choices ac
                           JOIN question_options qo ON qo.option_id = ac.option_id
                          WHERE ac.answer_id = ua.answer_id)
                    ELSE ua.text_answer
                END AS given_answer,
                CASE
                    WHEN quiz.show_feedback = 0 OR a.status = 'IN_PROGRESS' THEN NULL
                    WHEN q.type_code = 'ORDERING' THEN
                        (SELECT LISTAGG(qo.option_text, ' -> ') WITHIN GROUP (ORDER BY qo.seq_no)
                           FROM question_options qo
                          WHERE qo.question_id = q.question_id)
                    WHEN q.type_code IN ('SINGLE_CHOICE', 'MULTIPLE_CHOICE', 'BOOLEAN') THEN
                        (SELECT LISTAGG(qo.option_text, '; ') WITHIN GROUP (ORDER BY qo.seq_no)
                           FROM question_options qo
                          WHERE qo.question_id = q.question_id AND qo.is_correct = 1)
                    ELSE q.expected_answer
                END AS correct_answer
            FROM attempt_questions aq
            JOIN questions q ON q.question_id = aq.question_id
            JOIN quizzes quiz ON quiz.quiz_id = q.quiz_id
            JOIN attempts a ON a.attempt_id = aq.attempt_id
            LEFT JOIN user_answers ua
              ON ua.attempt_id = aq.attempt_id AND ua.question_id = aq.question_id
            WHERE aq.attempt_id = p_attempt_id
            ORDER BY aq.display_order;
    END attempt_details;

    PROCEDURE quiz_statistics(p_actor_id IN NUMBER, p_rows OUT SYS_REFCURSOR) IS
    BEGIN
        OPEN p_rows FOR
            SELECT t.title AS topic_title, q.title AS quiz_title, q.quiz_id,
                   COUNT(a.attempt_id) AS attempts_count, ROUND(AVG(a.score_percent), 2) AS average_score
              FROM quizzes q
              JOIN topics t ON t.topic_id = q.topic_id
              LEFT JOIN attempts a ON a.quiz_id = q.quiz_id AND a.status IN ('FINISHED', 'EXPIRED')
             WHERE EXISTS (
                   SELECT 1 FROM app_users u WHERE u.user_id = p_actor_id
                     AND u.is_active = 1 AND u.role_code IN ('ADMIN', 'AUTHOR')
                     AND (u.role_code = 'ADMIN' OR q.author_id = u.user_id)
             )
             GROUP BY t.title, q.title, q.quiz_id
             ORDER BY t.title, q.title;
    END quiz_statistics;

    PROCEDURE question_statistics(p_quiz_id IN NUMBER, p_rows OUT SYS_REFCURSOR) IS
    BEGIN
        OPEN p_rows FOR
            SELECT
                q.quiz_id,
                q.question_id,
                q.question_text,
                COUNT(ua.answer_id) AS answer_count,
                SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) AS correct_count,
                CASE
                    WHEN COUNT(ua.answer_id) = 0 THEN 0
                    ELSE ROUND(SUM(CASE WHEN ua.is_correct = 1 THEN 1 ELSE 0 END) / COUNT(ua.answer_id) * 100, 2)
                END AS correct_percent
            FROM questions q
            LEFT JOIN user_answers ua ON ua.question_id = q.question_id
            WHERE q.quiz_id = p_quiz_id
            GROUP BY q.quiz_id, q.question_id, q.question_text
            ORDER BY q.question_id;
    END question_statistics;

    PROCEDURE leaderboard(p_rows OUT SYS_REFCURSOR) IS
    BEGIN
        OPEN p_rows FOR
            SELECT u.user_id, u.full_name, COUNT(*) AS attempts_finished,
                   ROUND(AVG(a.score_percent), 2) AS average_score, MAX(a.score_percent) AS best_score
              FROM attempts a JOIN app_users u ON u.user_id = a.user_id
             WHERE a.status IN ('FINISHED', 'EXPIRED')
             GROUP BY u.user_id, u.full_name
             ORDER BY average_score DESC NULLS LAST, best_score DESC NULLS LAST;
    END leaderboard;

END pkg_reports;
/
