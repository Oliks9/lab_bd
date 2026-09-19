SET SERVEROUTPUT ON
DECLARE
    v_suffix VARCHAR2(32) := LOWER(RAWTOHEX(SYS_GUID()));
    v_admin NUMBER;
    v_author NUMBER;
    v_other_author NUMBER;
    v_user NUMBER;
    v_topic NUMBER;
    v_other_topic NUMBER;
    v_category NUMBER;
    v_other_category NUMBER;
    v_foreign_category NUMBER;
    v_quiz NUMBER;
    v_other_quiz NUMBER;
    v_question NUMBER;
    v_excluded NUMBER;
    v_attempt NUMBER;
    v_count NUMBER;
    v_value NUMBER;
    v_max NUMBER;
    v_ids VARCHAR2(4000);
    v_again VARCHAR2(4000);
    v_status VARCHAR2(20);
    v_rows SYS_REFCURSOR;
    v_catalog pkg_reports.catalog_row;
    v_found BOOLEAN := FALSE;

    PROCEDURE check_ok(p_ok BOOLEAN, p_message VARCHAR2) IS
    BEGIN
        IF p_ok IS NULL OR NOT p_ok THEN
            RAISE_APPLICATION_ERROR(-20982, p_message);
        END IF;
    END;

    PROCEDURE expect_setting_error(p_actor NUMBER, p_n NUMBER, p_category NUMBER,
                                   p_level VARCHAR2, p_code NUMBER) IS
    BEGIN
        BEGIN
            pkg_admin.set_quiz_selection(p_actor, v_quiz, p_n, p_category, p_level);
            RAISE_APPLICATION_ERROR(-20982, 'Selection setting should fail');
        EXCEPTION WHEN OTHERS THEN
            IF SQLCODE <> p_code THEN RAISE; END IF;
        END;
    END;
BEGIN
    SAVEPOINT selection_test;
    SELECT user_id INTO v_admin FROM app_users WHERE role_code = 'ADMIN' AND is_active = 1 AND ROWNUM = 1;
    pkg_admin.create_author(v_admin, 'sel_a_' || v_suffix, 'Select123!', 'Selection author', v_author);
    pkg_admin.create_author(v_admin, 'sel_b_' || v_suffix, 'Select123!', 'Other author', v_other_author);
    pr_register_user('sel_u_' || v_suffix, 'Select123!', 'Selection user', v_user);
    pkg_admin.create_topic(v_author, 'Selection ' || v_suffix, NULL, v_topic);
    pkg_admin.create_topic(v_admin, 'Other selection ' || v_suffix, NULL, v_other_topic);
    pkg_admin.create_category(v_author, v_topic, 'Target', v_category);
    pkg_admin.create_category(v_author, v_topic, 'Other', v_other_category);
    pkg_admin.create_category(v_admin, v_other_topic, 'Foreign', v_foreign_category);
    pkg_admin.create_quiz(v_author, v_topic, 'Selection quiz', NULL, 'QUIZ', 10, NULL, 1, 'PUBLIC', v_quiz);
    pkg_admin.create_quiz(v_author, v_topic, 'Other quiz', NULL, 'QUIZ', 10, NULL, 1, 'PUBLIC', v_other_quiz);
    FOR i IN 1..5 LOOP
        pkg_admin.add_question(v_author, v_quiz, v_category, 'TEXT', 'EASY', 'Target ' || i, 'yes', 'Explanation', i, v_question);
    END LOOP;
    pkg_admin.add_question(v_author, v_quiz, v_category, 'TEXT', 'HARD', 'Wrong level', 'yes', NULL, 50, v_excluded);
    pkg_admin.add_question(v_author, v_quiz, v_other_category, 'TEXT', 'EASY', 'Wrong category', 'yes', NULL, 50, v_excluded);
    pkg_admin.add_question(v_author, v_other_quiz, v_category, 'TEXT', 'EASY', 'Wrong quiz', 'yes', NULL, 50, v_excluded);
    check_ok(fn_quiz_pool_count(v_quiz, v_category, 'EASY') = 5, 'Pool must use quiz, category and difficulty');
    expect_setting_error(v_user, 2, v_category, 'EASY', -20101);
    expect_setting_error(v_other_author, 2, v_category, 'EASY', -20102);
    expect_setting_error(v_author, 0, v_category, 'EASY', -20138);
    expect_setting_error(v_author, 1.5, v_category, 'EASY', -20138);
    expect_setting_error(v_author, 1001, v_category, 'EASY', -20138);
    expect_setting_error(v_author, NULL, v_category, 'EASY', -20138);
    expect_setting_error(v_author, 2, NULL, 'EASY', -20138);
    expect_setting_error(v_author, 2, v_foreign_category, 'EASY', -20139);
    expect_setting_error(v_author, 2, v_category, 'UNKNOWN', -20138);
    pkg_admin.set_quiz_selection(v_author, v_quiz, 6, v_category, 'EASY');
    BEGIN
        pkg_admin.publish_quiz(v_author, v_quiz);
        RAISE_APPLICATION_ERROR(-20982, 'Underfilled quiz must not publish');
    EXCEPTION WHEN OTHERS THEN IF SQLCODE <> -20140 THEN RAISE; END IF; END;
    UPDATE quizzes SET status = 'PUBLISHED' WHERE quiz_id = v_quiz;
    BEGIN
        pkg_testing.start_attempt(v_user, v_quiz, v_attempt);
        RAISE_APPLICATION_ERROR(-20982, 'Underfilled quiz must not start');
    EXCEPTION WHEN OTHERS THEN IF SQLCODE <> -20214 THEN RAISE; END IF; END;
    SELECT COUNT(*) INTO v_count FROM attempts WHERE quiz_id = v_quiz;
    check_ok(v_count = 0, 'Rejected start must not consume an attempt');
    pkg_admin.archive_quiz(v_author, v_quiz);
    pkg_admin.set_quiz_selection(v_admin, v_quiz, 3, v_category, 'EASY');
    pkg_admin.publish_quiz(v_author, v_quiz);
    expect_setting_error(v_author, 2, v_category, 'EASY', -20102);
    pkg_reports.catalog(v_user, NULL, v_rows);
    LOOP
        FETCH v_rows INTO v_catalog;
        EXIT WHEN v_rows%NOTFOUND;
        IF v_catalog.quiz_id = v_quiz THEN
            v_count := v_catalog.question_count;
            v_max := v_catalog.max_points;
            v_value := v_catalog.pool_count;
            v_found := TRUE;
            EXIT;
        END IF;
    END LOOP;
    CLOSE v_rows;
    check_ok(v_found, 'Selected quiz missing from catalog');
    check_ok(v_count = 3 AND v_max IS NULL AND v_value = 5, 'Catalog must report selected count and variable points');
    FOR run IN 1..8 LOOP
        pkg_testing.start_attempt(v_user, v_quiz, v_attempt);
        SELECT COUNT(*), COUNT(DISTINCT aq.question_id), SUM(q.points)
          INTO v_count, v_value, v_max FROM attempt_questions aq JOIN questions q ON q.question_id = aq.question_id
         WHERE aq.attempt_id = v_attempt AND q.quiz_id = v_quiz AND q.category_id = v_category AND q.difficulty_code = 'EASY';
        check_ok(v_count = 3 AND v_value = 3, 'Must select exactly N unique matching questions');
        SELECT COUNT(*), MAX(display_order) INTO v_count, v_value FROM attempt_questions WHERE attempt_id = v_attempt;
        check_ok(v_count = 3 AND v_value = 3, 'Display order must be contiguous');
        SELECT LISTAGG(question_id, ',') WITHIN GROUP (ORDER BY display_order) INTO v_ids FROM attempt_questions WHERE attempt_id = v_attempt;
        FOR q IN (SELECT question_id FROM attempt_questions WHERE attempt_id = v_attempt ORDER BY display_order) LOOP
            pkg_testing.submit_answer(v_attempt, q.question_id, NULL, 'yes');
        END LOOP;
        SELECT LISTAGG(question_id, ',') WITHIN GROUP (ORDER BY display_order) INTO v_again FROM attempt_questions WHERE attempt_id = v_attempt;
        check_ok(v_ids = v_again, 'Attempt selection must remain stable');
        SELECT status, score_percent, max_points INTO v_status, v_value, v_count FROM attempts WHERE attempt_id = v_attempt;
        check_ok(v_status = 'FINISHED' AND v_value = 100 AND v_count = v_max, 'Score must use only the selected questions');
    END LOOP;
    pkg_admin.archive_quiz(v_author, v_quiz);
    UPDATE quizzes SET timer_mode = 'QUESTION' WHERE quiz_id = v_quiz;
    pkg_admin.set_quiz_selection(v_author, v_quiz, 1, v_category, 'EASY');
    pkg_admin.publish_quiz(v_author, v_quiz);
    pkg_testing.start_attempt(v_user, v_quiz, v_attempt);
    UPDATE attempts SET question_started_at = SYSTIMESTAMP - INTERVAL '20' MINUTE WHERE attempt_id = v_attempt;
    pkg_testing.expire_question(v_attempt);
    SELECT status INTO v_status FROM attempts WHERE attempt_id = v_attempt;
    check_ok(v_status = 'EXPIRED', 'Question timer must expire a one-question selection');
    pkg_admin.archive_quiz(v_author, v_quiz);
    pkg_admin.set_quiz_selection(v_author, v_quiz, 5, v_category, 'EASY');
    pkg_admin.publish_quiz(v_author, v_quiz);
    BEGIN
        pkg_admin.delete_question(v_author, v_question);
        RAISE_APPLICATION_ERROR(-20982, 'Deletion must not underfill published selection');
    EXCEPTION WHEN OTHERS THEN IF SQLCODE <> -20140 THEN RAISE; END IF; END;
    pkg_admin.archive_quiz(v_author, v_quiz);
    pkg_admin.set_quiz_selection(v_author, v_quiz, NULL, NULL, NULL);
    UPDATE quizzes SET timer_mode = 'QUIZ' WHERE quiz_id = v_quiz;
    pkg_admin.publish_quiz(v_author, v_quiz);
    pkg_testing.start_attempt(v_user, v_quiz, v_attempt);
    SELECT COUNT(*) INTO v_count FROM attempt_questions aq JOIN questions q ON aq.question_id = q.question_id
     WHERE aq.attempt_id = v_attempt AND aq.display_order = q.seq_no;
    check_ok(v_count = 7, 'All mode must preserve the original order');
    pkg_testing.abandon_attempt(v_attempt);
    UPDATE quizzes SET question_limit = 2 WHERE quiz_id = v_quiz;
    pkg_testing.start_attempt(v_user, v_quiz, v_attempt);
    SELECT COUNT(*) INTO v_count FROM attempt_questions WHERE attempt_id = v_attempt;
    check_ok(v_count = 2, 'Legacy question_limit must remain compatible');
    pkg_testing.abandon_attempt(v_attempt);
    pkg_admin.create_category(v_author, v_topic, 'Empty selection', v_category);
    pkg_admin.archive_quiz(v_author, v_quiz);
    pkg_admin.set_quiz_selection(v_author, v_quiz, 1, v_category, 'EASY');
    BEGIN
        pkg_admin.delete_category(v_admin, v_category);
        RAISE_APPLICATION_ERROR(-20982, 'Cannot delete a category used in selection');
    EXCEPTION WHEN OTHERS THEN IF SQLCODE <> -20141 THEN RAISE; END IF; END;
    ROLLBACK TO selection_test;
    DBMS_OUTPUT.PUT_LINE('Question selection smoke test passed.');
EXCEPTION WHEN OTHERS THEN
    ROLLBACK TO selection_test;
    RAISE;
END;
/
