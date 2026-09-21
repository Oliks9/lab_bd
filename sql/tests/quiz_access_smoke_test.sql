SET SERVEROUTPUT ON
DECLARE
    v_suffix VARCHAR2(32) := LOWER(RAWTOHEX(SYS_GUID()));
    v_admin NUMBER;
    v_author NUMBER;
    v_other NUMBER;
    v_user NUMBER;
    v_guest NUMBER;
    v_topic NUMBER;
    v_category NUMBER;
    v_quiz NUMBER;
    v_question NUMBER;
    v_attempt NUMBER;
    v_count NUMBER;
    v_score NUMBER;
    v_mode VARCHAR2(15);

    PROCEDURE check_ok(p_ok BOOLEAN, p_message VARCHAR2) IS
    BEGIN
        IF p_ok IS NULL OR NOT p_ok THEN
            RAISE_APPLICATION_ERROR(-20985, p_message);
        END IF;
    END;

    PROCEDURE reject_change(p_actor NUMBER, p_mode VARCHAR2, p_code NUMBER) IS
    BEGIN
        BEGIN
            pkg_admin.set_quiz_access_mode(p_actor, v_quiz, p_mode);
            RAISE_APPLICATION_ERROR(-20985, 'Invalid access change accepted');
        EXCEPTION WHEN OTHERS THEN
            IF SQLCODE <> p_code THEN RAISE; END IF;
        END;
    END;
BEGIN
    SAVEPOINT access_test;
    SELECT user_id INTO v_admin FROM app_users WHERE role_code = 'ADMIN' AND is_active = 1 AND ROWNUM = 1;
    pkg_admin.create_author(v_admin, 'acc_a_' || v_suffix, 'Access123!', 'Author', v_author);
    pkg_admin.create_author(v_admin, 'acc_b_' || v_suffix, 'Access123!', 'Other', v_other);
    pr_register_user('acc_u_' || v_suffix, 'Access123!', 'Invited', v_user);
    pr_register_user('acc_g_' || v_suffix, 'Access123!', 'Guest', v_guest);
    pkg_admin.create_topic(v_author, 'Access ' || v_suffix, NULL, v_topic);
    pkg_admin.create_category(v_author, v_topic, 'Category', v_category);
    pkg_admin.create_quiz(v_author, v_topic, 'Access quiz', NULL, 'QUIZ', 10, NULL, 1, 'PUBLIC', v_quiz);
    pkg_admin.add_question(v_author, v_quiz, v_category, 'TEXT', 'EASY', 'Yes?', 'yes', 'Explanation', 2, v_question);
    reject_change(v_other, 'RESTRICTED', -20102);
    reject_change(v_user, 'RESTRICTED', -20101);
    reject_change(v_author, 'INVALID', -20144);
    reject_change(v_author, NULL, -20144);
    pkg_admin.set_quiz_access_mode(v_author, v_quiz, ' restricted ');
    SELECT access_mode INTO v_mode FROM quizzes WHERE quiz_id = v_quiz;
    check_ok(v_mode = 'RESTRICTED', 'Mode not normalized');
    pkg_admin.grant_access(v_author, v_quiz, v_user);
    pkg_admin.publish_quiz(v_author, v_quiz);
    check_ok(fn_can_access_quiz(v_user, v_quiz) = 1, 'Invited user denied');
    check_ok(fn_can_access_quiz(v_guest, v_quiz) = 0, 'Private quiz exposed');
    reject_change(v_author, 'PUBLIC', -20102);
    pkg_testing.start_attempt(v_user, v_quiz, v_attempt);
    pkg_testing.submit_answer(v_attempt, v_question, NULL, 'yes');
    pkg_testing.finish_attempt(v_attempt);
    pkg_admin.archive_quiz(v_author, v_quiz);
    pkg_admin.set_quiz_access_mode(v_admin, v_quiz, 'PUBLIC');
    pkg_admin.publish_quiz(v_author, v_quiz);
    check_ok(fn_can_access_quiz(v_guest, v_quiz) = 1, 'Public quiz inaccessible');
    pkg_admin.archive_quiz(v_author, v_quiz);
    pkg_admin.set_quiz_access_mode(v_author, v_quiz, 'RESTRICTED');
    pkg_admin.publish_quiz(v_author, v_quiz);
    check_ok(fn_can_access_quiz(v_user, v_quiz) = 1, 'Invitation lost');
    check_ok(fn_can_access_quiz(v_guest, v_quiz) = 0, 'Private mode not restored');
    SELECT COUNT(*) INTO v_count FROM quiz_access WHERE quiz_id = v_quiz AND user_id = v_user;
    check_ok(v_count = 1, 'Invitation changed');
    SELECT COUNT(*) INTO v_count FROM attempts WHERE quiz_id = v_quiz;
    check_ok(v_count = 1, 'Attempt deleted or duplicated');
    SELECT fn_attempt_percent(v_attempt) INTO v_score FROM dual;
    check_ok(v_score = 100, 'Score changed');
    pkg_admin.archive_quiz(v_author, v_quiz);
    pkg_admin.set_user_active(v_admin, v_author, 0);
    reject_change(v_author, 'PUBLIC', -20100);
    ROLLBACK TO access_test;
    DBMS_OUTPUT.PUT_LINE('Quiz access smoke test passed: roles, draft, mode, invitations, results.');
EXCEPTION WHEN OTHERS THEN
    ROLLBACK TO access_test;
    RAISE;
END;
/
