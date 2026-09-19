SET SERVEROUTPUT ON
DECLARE
    v_suffix VARCHAR2(32) := LOWER(RAWTOHEX(SYS_GUID()));
    v_admin NUMBER;
    v_author NUMBER;
    v_other NUMBER;
    v_user NUMBER;
    v_topic NUMBER;
    v_category NUMBER;
    v_quiz NUMBER;
    v_question NUMBER;
    v_attempt NUMBER;
    v_rows SYS_REFCURSOR;
    v_result pkg_reports.result_row;
    v_title VARCHAR2(200);
    v_quiz_title VARCHAR2(200);
    v_id NUMBER;
    v_count NUMBER;
    v_average NUMBER;

    PROCEDURE check_ok(p_ok BOOLEAN, p_message VARCHAR2) IS
    BEGIN
        IF p_ok IS NULL OR NOT p_ok THEN
            RAISE_APPLICATION_ERROR(-20983, p_message);
        END IF;
    END;

    FUNCTION catalog_count(p_user NUMBER, p_topic NUMBER) RETURN NUMBER IS
        v_cursor SYS_REFCURSOR;
        v_row pkg_reports.catalog_row;
        v_total NUMBER := 0;
    BEGIN
        pkg_reports.catalog(p_user, p_topic, v_cursor);
        LOOP
            FETCH v_cursor INTO v_row;
            EXIT WHEN v_cursor%NOTFOUND;
            IF v_row.quiz_id = v_quiz THEN v_total := v_total + 1; END IF;
        END LOOP;
        CLOSE v_cursor;
        RETURN v_total;
    EXCEPTION WHEN OTHERS THEN
        IF v_cursor%ISOPEN THEN CLOSE v_cursor; END IF;
        RAISE;
    END;

    PROCEDURE check_statistics(p_actor NUMBER, p_expected NUMBER) IS
        v_total NUMBER := 0;
    BEGIN
        pkg_reports.quiz_statistics(p_actor, v_rows);
        LOOP
            FETCH v_rows INTO v_title, v_quiz_title, v_id, v_count, v_average;
            EXIT WHEN v_rows%NOTFOUND;
            IF v_id = v_quiz THEN
                v_total := v_total + 1;
                check_ok(v_count = 1 AND v_average = 100, 'Wrong quiz statistics');
            END IF;
        END LOOP;
        CLOSE v_rows;
        check_ok(v_total = p_expected, 'Quiz statistics role/owner filter failed');
    END;
BEGIN
    SAVEPOINT reports_test;
    SELECT user_id INTO v_admin FROM app_users WHERE role_code = 'ADMIN' AND is_active = 1 AND ROWNUM = 1;
    pkg_admin.create_author(v_admin, 'rep_a_' || v_suffix, 'Reports123!', 'Report author', v_author);
    pkg_admin.create_author(v_admin, 'rep_b_' || v_suffix, 'Reports123!', 'Other author', v_other);
    pr_register_user('rep_u_' || v_suffix, 'Reports123!', 'Report user', v_user);
    pkg_admin.create_topic(v_author, 'Reports ' || v_suffix, NULL, v_topic);
    pkg_admin.create_category(v_author, v_topic, 'Category', v_category);
    pkg_admin.create_quiz(v_author, v_topic, 'Reports quiz', NULL, 'QUIZ', 10, NULL, 1, 'RESTRICTED', v_quiz);
    pkg_admin.add_question(v_author, v_quiz, v_category, 'TEXT', 'EASY', 'Yes?', 'yes', 'Explanation', 2, v_question);
    check_ok(catalog_count(v_author, v_topic) = 0, 'Draft visible in catalog');
    pkg_admin.publish_quiz(v_author, v_quiz);
    check_ok(catalog_count(v_author, NULL) = 1, 'Owner cannot see published quiz');
    check_ok(catalog_count(v_admin, v_topic) = 1, 'Admin cannot see published quiz');
    check_ok(catalog_count(v_user, v_topic) = 0, 'Restricted quiz exposed');
    pkg_admin.grant_access(v_author, v_quiz, v_user);
    check_ok(catalog_count(v_user, v_topic) = 1, 'Granted quiz not visible');
    check_ok(catalog_count(v_user, -1) = 0, 'Topic filter ignored');
    check_ok(catalog_count(-1, NULL) = 0, 'Unknown user sees catalog');
    pkg_testing.start_attempt(v_user, v_quiz, v_attempt);
    pkg_testing.submit_answer(v_attempt, v_question, NULL, 'yes');
    pkg_reports.attempt_result(v_attempt, v_rows);
    FETCH v_rows INTO v_result;
    check_ok(v_rows%FOUND, 'Result cursor empty');
    CLOSE v_rows;
    check_ok(v_result.score_percent = 100 AND v_result.question_count = 1
        AND v_result.correct_count = 1 AND v_result.comparison_code = 'NO_PEERS', 'Incorrect attempt result');
    check_statistics(v_admin, 1);
    check_statistics(v_author, 1);
    check_statistics(v_other, 0);
    check_statistics(v_user, 0);
    check_statistics(-1, 0);
    pkg_admin.set_user_active(v_admin, v_user, 0);
    check_ok(catalog_count(v_user, NULL) = 0, 'Inactive user sees catalog');
    pkg_admin.set_user_active(v_admin, v_author, 0);
    check_statistics(v_author, 0);
    ROLLBACK TO reports_test;
    DBMS_OUTPUT.PUT_LINE('Reports smoke test passed: catalog access, filters, results and statistics permissions.');
EXCEPTION WHEN OTHERS THEN
    IF v_rows%ISOPEN THEN CLOSE v_rows; END IF;
    ROLLBACK TO reports_test;
    RAISE;
END;
/
