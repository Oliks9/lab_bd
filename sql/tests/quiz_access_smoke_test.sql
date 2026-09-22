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
    v_rows SYS_REFCURSOR;
    v_id NUMBER;
    v_login VARCHAR2(50);
    v_name VARCHAR2(200);
    v_role VARCHAR2(20);
    v_active NUMBER;
    v_source VARCHAR2(20);
    v_date TIMESTAMP;
    v_revoke NUMBER;

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

    PROCEDURE reject_access(p_actor NUMBER, p_operation VARCHAR2, p_target NUMBER, p_code NUMBER) IS
    BEGIN
        BEGIN
            IF p_operation = 'LIST' THEN
                pkg_admin.list_quiz_access(p_actor, v_quiz, v_rows);
                CLOSE v_rows;
            ELSIF p_operation = 'GRANT' THEN
                pkg_admin.grant_access(p_actor, v_quiz, p_target);
            ELSE
                pkg_admin.revoke_access(p_actor, v_quiz, p_target);
            END IF;
            RAISE_APPLICATION_ERROR(-20985, 'Forbidden access operation accepted');
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
    pkg_admin.grant_access(v_author, v_quiz, v_user);
    pkg_admin.list_quiz_access(v_author, v_quiz, v_rows);
    v_count := 0;
    LOOP
        FETCH v_rows INTO v_id, v_login, v_name, v_role, v_active, v_source, v_date, v_revoke;
        EXIT WHEN v_rows%NOTFOUND;
        IF v_id = v_user THEN
            check_ok(v_source = 'INVITATION' AND v_revoke = 1 AND v_date IS NOT NULL, 'Invitation row invalid');
            v_count := v_count + 1;
        ELSIF v_id = v_author OR v_id = v_admin THEN
            check_ok(v_revoke = 0, 'Inherent access can be revoked');
        END IF;
    END LOOP;
    CLOSE v_rows;
    check_ok(v_count = 1, 'List missed or duplicated invitation');
    reject_access(v_other, 'LIST', v_user, -20110);
    reject_access(v_user, 'LIST', v_user, -20110);
    reject_access(v_other, 'REVOKE', v_user, -20110);
    reject_access(v_other, 'GRANT', v_guest, -20110);
    reject_access(v_author, 'REVOKE', v_author, -20146);
    reject_access(v_author, 'REVOKE', v_admin, -20146);
    reject_access(v_author, 'GRANT', v_admin, -20146);
    reject_access(v_author, 'REVOKE', -1, -20147);
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
    reject_access(v_author, 'LIST', v_user, -20145);
    reject_access(v_author, 'REVOKE', v_user, -20145);
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
    pkg_admin.revoke_access(v_author, v_quiz, v_user);
    pkg_admin.revoke_access(v_author, v_quiz, v_user);
    check_ok(fn_can_access_quiz(v_user, v_quiz) = 0, 'Revoked user still has access');
    BEGIN
        pkg_testing.start_attempt(v_user, v_quiz, v_count);
        RAISE_APPLICATION_ERROR(-20985, 'Revoked user started attempt');
    EXCEPTION WHEN OTHERS THEN
        IF SQLCODE <> -20200 THEN RAISE; END IF;
    END;
    SELECT fn_attempt_percent(v_attempt) INTO v_score FROM dual;
    check_ok(v_score = 100, 'Revoke changed completed result');
    pkg_admin.grant_access(v_admin, v_quiz, v_user);
    pkg_testing.start_attempt(v_user, v_quiz, v_attempt);
    pkg_admin.revoke_access(v_admin, v_quiz, v_user);
    pkg_testing.submit_answer(v_attempt, v_question, NULL, 'yes');
    pkg_testing.finish_attempt(v_attempt);
    SELECT fn_attempt_percent(v_attempt) INTO v_score FROM dual;
    check_ok(v_score = 100, 'Existing attempt broken by revoke');
    SELECT COUNT(*) INTO v_count FROM attempts WHERE quiz_id = v_quiz;
    check_ok(v_count = 2, 'Revoke deleted attempt history');
    pkg_admin.grant_access(v_admin, v_quiz, v_user);
    pkg_admin.set_user_active(v_admin, v_user, 0);
    pkg_admin.revoke_access(v_author, v_quiz, v_user);
    SELECT COUNT(*) INTO v_count FROM quiz_access WHERE quiz_id = v_quiz AND user_id = v_user;
    check_ok(v_count = 0, 'Inactive user invitation not revoked');
    pkg_admin.archive_quiz(v_author, v_quiz);
    pkg_admin.set_user_active(v_admin, v_author, 0);
    reject_change(v_author, 'PUBLIC', -20100);
    reject_access(v_author, 'LIST', v_user, -20100);
    reject_access(v_author, 'REVOKE', v_user, -20100);
    ROLLBACK TO access_test;
    DBMS_OUTPUT.PUT_LINE('Quiz access smoke test passed: roles, mode, list, revoke, invitations, preserved attempts.');
EXCEPTION WHEN OTHERS THEN
    ROLLBACK TO access_test;
    RAISE;
END;
/
