SET SERVEROUTPUT ON
ALTER SESSION SET TIME_ZONE = '+03:00';

DECLARE
    v_admin_id NUMBER;
    v_user_id NUMBER;
    v_topic_id NUMBER;
    v_category_id NUMBER;
    v_login VARCHAR2(50);
    v_quiz_id NUMBER;
    v_attempt_id NUMBER;
    v_question_id NUMBER;
    v_other_question_id NUMBER;
    v_status VARCHAR2(20);
BEGIN
    SAVEPOINT before_timezone_smoke_test;

    v_login := 'smoke_tz_' || LOWER(RAWTOHEX(SYS_GUID()));
    pr_register_user(v_login, 'Smoke123!', 'Smoke Timezone', v_user_id);
    SELECT user_id INTO v_admin_id FROM app_users WHERE role_code = 'ADMIN' AND is_active = 1 AND ROWNUM = 1;
    pkg_admin.create_topic(v_admin_id, v_login, NULL, v_topic_id);
    pkg_admin.create_category(v_admin_id, v_topic_id, 'Timezone', v_category_id);
    pkg_admin.create_quiz(v_admin_id, v_topic_id, 'Timezone test', NULL, 'QUIZ', 10, NULL, 1, 'PUBLIC', v_quiz_id);
    pkg_admin.add_question(v_admin_id, v_quiz_id, v_category_id, 'NUMBER', 'EASY', 'One?', '1', NULL, 1, v_question_id);
    pkg_admin.add_question(v_admin_id, v_quiz_id, v_category_id, 'NUMBER', 'EASY', 'Two?', '2', NULL, 1, v_other_question_id);
    pkg_admin.publish_quiz(v_admin_id, v_quiz_id);
    pkg_testing.start_attempt(v_user_id, v_quiz_id, v_attempt_id);

    pkg_testing.submit_answer(v_attempt_id, v_question_id, NULL, '1');
    SELECT status INTO v_status FROM attempts WHERE attempt_id = v_attempt_id;
    IF v_status <> 'IN_PROGRESS' THEN
        RAISE_APPLICATION_ERROR(-20995, 'Timezone test prematurely completed the active attempt.');
    END IF;

    DBMS_OUTPUT.PUT_LINE('Timezone smoke test successful. Answer accepted in +03:00 session.');
    ROLLBACK TO before_timezone_smoke_test;
EXCEPTION WHEN OTHERS THEN
    ROLLBACK TO before_timezone_smoke_test;
    RAISE;
END;
/

ALTER SESSION SET TIME_ZONE = '+00:00';
