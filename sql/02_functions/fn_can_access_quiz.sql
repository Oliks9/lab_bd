CREATE OR REPLACE FUNCTION fn_can_access_quiz (
    p_user_id IN NUMBER,
    p_quiz_id IN NUMBER
) RETURN NUMBER
IS
    v_count NUMBER;
BEGIN
    SELECT COUNT(*)
      INTO v_count
      FROM quizzes q
      JOIN app_users u ON u.user_id = p_user_id AND u.is_active = 1
     WHERE q.quiz_id = p_quiz_id
       AND q.status = 'PUBLISHED'
       AND (
            q.access_mode = 'PUBLIC'
            OR q.author_id = p_user_id
            OR u.role_code = 'ADMIN'
            OR EXISTS (
                SELECT 1
                  FROM quiz_access qa
                 WHERE qa.quiz_id = q.quiz_id
                   AND qa.user_id = p_user_id
            )
       );

    RETURN CASE WHEN v_count > 0 THEN 1 ELSE 0 END;
END;
/
