CREATE OR REPLACE VIEW v_quiz_catalog AS
SELECT
    q.quiz_id,
    q.topic_id,
    t.title AS topic_title,
    q.title AS quiz_title,
    q.description,
    q.timer_mode,
    q.duration_minutes,
    q.show_feedback,
    q.access_mode,
    q.status,
    u.full_name AS author_name,
    COUNT(qu.question_id) AS question_count,
    NVL(SUM(qu.points), 0) AS max_points
FROM quizzes q
JOIN topics t ON t.topic_id = q.topic_id
JOIN app_users u ON u.user_id = q.author_id
LEFT JOIN questions qu ON qu.quiz_id = q.quiz_id
GROUP BY
    q.quiz_id, q.topic_id, t.title, q.title, q.description, q.timer_mode, q.duration_minutes,
    q.show_feedback, q.access_mode, q.status, u.full_name;

CREATE OR REPLACE VIEW v_attempt_history AS
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
JOIN topics t ON t.topic_id = q.topic_id;

CREATE OR REPLACE VIEW v_attempt_details AS
SELECT
    aq.attempt_id,
    aq.display_order,
    q.question_id,
    q.question_text,
    q.type_code,
    q.explanation,
    q.points,
    ua.text_answer,
    ua.is_correct,
    ua.awarded_points,
    CASE
        WHEN q.type_code IN ('SINGLE_CHOICE', 'MULTIPLE_CHOICE', 'BOOLEAN') THEN
            (SELECT LISTAGG(qo.option_text, '; ') WITHIN GROUP (ORDER BY qo.seq_no)
               FROM answer_choices ac
               JOIN question_options qo ON qo.option_id = ac.option_id
              WHERE ac.answer_id = ua.answer_id)
        ELSE ua.text_answer
    END AS given_answer,
    CASE
        WHEN q.type_code IN ('SINGLE_CHOICE', 'MULTIPLE_CHOICE', 'BOOLEAN') THEN
            (SELECT LISTAGG(qo.option_text, '; ') WITHIN GROUP (ORDER BY qo.seq_no)
               FROM question_options qo
              WHERE qo.question_id = q.question_id
                AND qo.is_correct = 1)
        ELSE q.expected_answer
    END AS correct_answer
FROM attempt_questions aq
JOIN questions q ON q.question_id = aq.question_id
LEFT JOIN user_answers ua
  ON ua.attempt_id = aq.attempt_id
 AND ua.question_id = aq.question_id;

CREATE OR REPLACE VIEW v_question_statistics AS
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
GROUP BY q.quiz_id, q.question_id, q.question_text;

CREATE OR REPLACE VIEW v_leaderboard AS
SELECT
    user_id,
    full_name,
    COUNT(*) AS attempts_finished,
    ROUND(AVG(score_percent), 2) AS average_score,
    MAX(score_percent) AS best_score
FROM v_attempt_history
WHERE status IN ('FINISHED', 'EXPIRED')
GROUP BY user_id, full_name;
