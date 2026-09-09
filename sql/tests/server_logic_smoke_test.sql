SET SERVEROUTPUT ON
DECLARE
    v_admin NUMBER;
    v_user NUMBER;
    v_login VARCHAR2(50) := 'srv_' || LOWER(RAWTOHEX(SYS_GUID()));
    v_topic NUMBER;
    v_category NUMBER;
    v_quiz NUMBER;
    v_first NUMBER;
    v_second NUMBER;
    v_attempt NUMBER;
    v_other NUMBER;
    v_order NUMBER;
    v_count NUMBER;
    v_login_id NUMBER;
    v_name VARCHAR2(200);
    v_role VARCHAR2(20);
    v_status VARCHAR2(20);

    PROCEDURE check_condition(p_ok BOOLEAN, p_message VARCHAR2) IS
    BEGIN
        IF p_ok IS NULL OR NOT p_ok THEN
            RAISE_APPLICATION_ERROR(-20980, p_message);
        END IF;
    END;
BEGIN
    SAVEPOINT server_logic_test;
    SELECT user_id INTO v_admin FROM app_users
     WHERE role_code = 'ADMIN' AND is_active = 1 AND ROWNUM = 1;
    pr_register_user(v_login, 'Server123!', 'Server checks', v_user);
    pkg_admin.create_topic(v_admin, v_login, NULL, v_topic);
    pkg_admin.create_category(v_admin, v_topic, 'Numbers', v_category);
    pkg_admin.create_quiz(v_admin, v_topic, 'Server logic', NULL, 'QUESTION', 1, NULL, 1, 'PUBLIC', v_quiz);
    pkg_admin.add_question(v_admin, v_quiz, v_category, 'NUMBER', 'EASY', 'One?', '1', 'First explanation', 1, v_first);
    pkg_admin.add_question(v_admin, v_quiz, v_category, 'NUMBER', 'EASY', 'Two?', '2', 'Second explanation', 1, v_second);
    BEGIN
        pkg_admin.set_quiz_attempt_limit(v_admin, v_quiz, 1.5);
        RAISE_APPLICATION_ERROR(-20980, 'Fractional attempt limit accepted.');
    EXCEPTION WHEN OTHERS THEN
        IF SQLCODE <> -20130 THEN RAISE; END IF;
    END;
    pkg_admin.publish_quiz(v_admin, v_quiz);
    pkg_testing.start_attempt(v_user, v_quiz, v_attempt);
    BEGIN
        pkg_testing.start_attempt(v_user, v_quiz, v_other);
        RAISE_APPLICATION_ERROR(-20980, 'Second active attempt accepted.');
    EXCEPTION WHEN OTHERS THEN
        IF SQLCODE <> -20213 THEN RAISE; END IF;
    END;
    SELECT COUNT(*) INTO v_count FROM v_attempt_details
     WHERE attempt_id = v_attempt AND (correct_answer IS NOT NULL OR explanation IS NOT NULL);
    check_condition(v_count = 0, 'Feedback exposed during an active attempt.');
    BEGIN
        pkg_testing.expire_question(v_attempt);
        RAISE_APPLICATION_ERROR(-20980, 'Question advanced before its deadline.');
    EXCEPTION WHEN OTHERS THEN
        IF SQLCODE <> -20212 THEN RAISE; END IF;
    END;
    SELECT active_question_order INTO v_order FROM attempts WHERE attempt_id = v_attempt;
    check_condition(v_order = 1, 'Early timeout changed the active question.');

    -- Simulate elapsed server time without waiting or changing the system clock.
    UPDATE attempts SET question_started_at = SYSTIMESTAMP - INTERVAL '2' MINUTE
     WHERE attempt_id = v_attempt;
    BEGIN
        pkg_testing.submit_answer(v_attempt, v_first, NULL, '1');
        RAISE_APPLICATION_ERROR(-20980, 'Late answer accepted.');
    EXCEPTION WHEN OTHERS THEN
        IF SQLCODE <> -20203 THEN RAISE; END IF;
    END;
    pkg_testing.expire_question(v_attempt);
    SELECT active_question_order INTO v_order FROM attempts WHERE attempt_id = v_attempt;
    check_condition(v_order = 2, 'Expired question did not advance.');
    pkg_testing.submit_answer(v_attempt, v_second, NULL, '2');
    SELECT status, score_percent INTO v_status, v_count FROM attempts WHERE attempt_id = v_attempt;
    check_condition(v_status = 'FINISHED' AND v_count = 50, 'Last answer did not finalize and score the attempt.');
    SELECT COUNT(*) INTO v_count FROM v_attempt_details
     WHERE attempt_id = v_attempt AND correct_answer IS NOT NULL AND explanation IS NOT NULL;
    check_condition(v_count = 2, 'Enabled feedback missing after completion.');
    pkg_testing.abandon_attempt(v_attempt);
    SELECT status INTO v_status FROM attempts WHERE attempt_id = v_attempt;
    check_condition(v_status = 'FINISHED', 'Abandon changed a previously finished result.');

    pkg_admin.archive_quiz(v_admin, v_quiz);
    pkg_admin.set_quiz_feedback(v_admin, v_quiz, 0);
    SELECT COUNT(*) INTO v_count FROM v_attempt_details
     WHERE attempt_id = v_attempt AND (correct_answer IS NOT NULL OR explanation IS NOT NULL);
    check_condition(v_count = 0, 'Disabled feedback still exposed by Oracle.');
    pkg_admin.set_quiz_attempt_limit(v_admin, v_quiz, 1);
    pkg_admin.publish_quiz(v_admin, v_quiz);
    BEGIN
        pkg_testing.start_attempt(v_user, v_quiz, v_other);
        RAISE_APPLICATION_ERROR(-20980, 'Attempt limit ignored.');
    EXCEPTION WHEN OTHERS THEN
        IF SQLCODE <> -20211 THEN RAISE; END IF;
    END;
    pkg_admin.archive_quiz(v_admin, v_quiz);
    pkg_admin.set_quiz_attempt_limit(v_admin, v_quiz, NULL);
    pkg_admin.publish_quiz(v_admin, v_quiz);
    pkg_testing.start_attempt(v_user, v_quiz, v_attempt);
    pr_login(v_login, 'Server123!', v_login_id, v_name, v_role);
    SELECT status INTO v_status FROM attempts WHERE attempt_id = v_attempt;
    check_condition(v_status = 'EXPIRED', 'Direct pr_login did not abandon old attempts.');

    pkg_testing.start_attempt(v_user, v_quiz, v_attempt);
    pkg_testing.submit_answer(v_attempt, v_first, NULL, '1');
    UPDATE attempts SET question_started_at = SYSTIMESTAMP - INTERVAL '2' MINUTE
     WHERE attempt_id = v_attempt;
    pkg_testing.expire_question(v_attempt);
    SELECT status, score_percent INTO v_status, v_count FROM attempts WHERE attempt_id = v_attempt;
    check_condition(v_status = 'EXPIRED' AND v_count = 50, 'Last timeout did not finalize the attempt.');

    DBMS_OUTPUT.PUT_LINE('Server logic checks successful: timers, feedback, limits, login cleanup and finalization.');
    ROLLBACK TO server_logic_test;
EXCEPTION WHEN OTHERS THEN
    ROLLBACK TO server_logic_test;
    RAISE;
END;
/
