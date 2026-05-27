SET SERVEROUTPUT ON
ALTER SESSION SET TIME_ZONE = '+03:00';

DECLARE
    v_admin_id NUMBER;
    v_name VARCHAR2(200);
    v_role VARCHAR2(20);
    v_login VARCHAR2(50);
    v_quiz_id NUMBER;
    v_attempt_id NUMBER;
    v_question_id NUMBER;
    v_option_id NUMBER;
    v_status VARCHAR2(20);
BEGIN
    SAVEPOINT before_timezone_smoke_test;

    v_login := 'smoke_tz_' || TO_CHAR(TRUNC(DBMS_RANDOM.VALUE(1000, 9999)));
    pr_register_user(v_login, 'Smoke123!', 'Smoke Timezone', v_admin_id);
    SELECT quiz_id
      INTO v_quiz_id
      FROM quizzes
     WHERE status = 'PUBLISHED'
       AND access_mode = 'PUBLIC'
       AND ROWNUM = 1;
    pkg_testing.start_attempt(v_admin_id, v_quiz_id, v_attempt_id);

    SELECT q.question_id, qo.option_id
      INTO v_question_id, v_option_id
      FROM questions q
      JOIN question_options qo ON qo.question_id = q.question_id AND qo.is_correct = 1
     WHERE q.quiz_id = v_quiz_id
       AND q.seq_no = 1;

    pkg_testing.submit_answer(v_attempt_id, v_question_id, TO_CHAR(v_option_id), NULL);
    SELECT status INTO v_status FROM attempts WHERE attempt_id = v_attempt_id;
    IF v_status <> 'IN_PROGRESS' THEN
        RAISE_APPLICATION_ERROR(-20995, 'Timezone test prematurely completed the active attempt.');
    END IF;

    DBMS_OUTPUT.PUT_LINE('Timezone smoke test successful. Answer accepted in +03:00 session.');
    ROLLBACK TO before_timezone_smoke_test;
END;
/

ALTER SESSION SET TIME_ZONE = '+00:00';
