SET SERVEROUTPUT ON
DECLARE
    v_admin_id NUMBER;
    v_name VARCHAR2(200);
    v_role VARCHAR2(20);
    v_quiz_id NUMBER;
    v_attempt_id NUMBER;
    v_question_id NUMBER;
    v_option_ids VARCHAR2(1000);
    v_score NUMBER;
BEGIN
    SAVEPOINT before_testing_smoke_test;
    pr_login('admin', 'Admin123!', v_admin_id, v_name, v_role);
    SELECT quiz_id INTO v_quiz_id FROM quizzes WHERE title = 'Oracle: основы серверной логики';
    pkg_testing.start_attempt(v_admin_id, v_quiz_id, v_attempt_id);

    SELECT q.question_id, TO_CHAR(qo.option_id)
      INTO v_question_id, v_option_ids
      FROM questions q
      JOIN question_options qo ON qo.question_id = q.question_id AND qo.is_correct = 1
     WHERE q.quiz_id = v_quiz_id
       AND q.seq_no = 1;
    pkg_testing.submit_answer(v_attempt_id, v_question_id, v_option_ids, NULL);

    SELECT q.question_id, LISTAGG(TO_CHAR(qo.option_id), ',') WITHIN GROUP (ORDER BY qo.seq_no)
      INTO v_question_id, v_option_ids
      FROM questions q
      JOIN question_options qo ON qo.question_id = q.question_id AND qo.is_correct = 1
     WHERE q.quiz_id = v_quiz_id
       AND q.seq_no = 2
     GROUP BY q.question_id;
    pkg_testing.submit_answer(v_attempt_id, v_question_id, v_option_ids, NULL);

    SELECT question_id INTO v_question_id FROM questions WHERE quiz_id = v_quiz_id AND seq_no = 3;
    pkg_testing.submit_answer(v_attempt_id, v_question_id, NULL, 'COMMIT');

    SELECT question_id INTO v_question_id FROM questions WHERE quiz_id = v_quiz_id AND seq_no = 4;
    pkg_testing.submit_answer(v_attempt_id, v_question_id, NULL, '2');

    SELECT q.question_id, TO_CHAR(qo.option_id)
      INTO v_question_id, v_option_ids
      FROM questions q
      JOIN question_options qo ON qo.question_id = q.question_id AND qo.is_correct = 1
     WHERE q.quiz_id = v_quiz_id
       AND q.seq_no = 5;
    pkg_testing.submit_answer(v_attempt_id, v_question_id, v_option_ids, NULL);

    SELECT q.question_id, LISTAGG(TO_CHAR(qo.option_id), ',') WITHIN GROUP (ORDER BY qo.seq_no)
      INTO v_question_id, v_option_ids
      FROM questions q
      JOIN question_options qo ON qo.question_id = q.question_id
     WHERE q.quiz_id = v_quiz_id
       AND q.seq_no = 6
     GROUP BY q.question_id;
    pkg_testing.submit_answer(v_attempt_id, v_question_id, v_option_ids, NULL);

    pkg_testing.finish_attempt(v_attempt_id);
    SELECT score_percent INTO v_score FROM attempts WHERE attempt_id = v_attempt_id;

    IF v_score <> 100 THEN
        RAISE_APPLICATION_ERROR(-20997, 'Testing smoke test expected 100%, got ' || v_score || '%.');
    END IF;

    DBMS_OUTPUT.PUT_LINE('Testing smoke test successful. Six answer types scored: ' || v_score || '%');
    ROLLBACK TO before_testing_smoke_test;
END;
/
