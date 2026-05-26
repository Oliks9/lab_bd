CREATE OR REPLACE FUNCTION fn_attempt_percent (
    p_attempt_id IN NUMBER
) RETURN NUMBER
IS
    v_awarded NUMBER;
    v_max NUMBER;
BEGIN
    SELECT NVL(SUM(ua.awarded_points), 0),
           NVL(SUM(q.points), 0)
      INTO v_awarded, v_max
      FROM attempt_questions aq
      JOIN questions q ON q.question_id = aq.question_id
      LEFT JOIN user_answers ua
        ON ua.attempt_id = aq.attempt_id
       AND ua.question_id = aq.question_id
     WHERE aq.attempt_id = p_attempt_id;

    RETURN CASE WHEN v_max = 0 THEN 0 ELSE ROUND(v_awarded / v_max * 100, 2) END;
END;
/
