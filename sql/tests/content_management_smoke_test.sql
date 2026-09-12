SET SERVEROUTPUT ON
DECLARE
    v_suffix VARCHAR2(32) := LOWER(RAWTOHEX(SYS_GUID()));
    v_admin_id NUMBER;
    v_author_id NUMBER;
    v_topic_id NUMBER;
    v_category_id NUMBER;
    v_quiz_id NUMBER;
    v_demo_quiz_id NUMBER;
    v_question_id NUMBER;
    v_option_id NUMBER;
    v_attempt_id NUMBER;
    v_failed_attempt_id NUMBER;
    v_name VARCHAR2(200);
    v_role VARCHAR2(20);
    v_count NUMBER;
BEGIN
    SAVEPOINT before_content_management_test;

    SELECT user_id INTO v_admin_id FROM app_users WHERE role_code = 'ADMIN' AND is_active = 1 AND ROWNUM = 1;
    pkg_admin.create_author(v_admin_id, 'smoke_editor_' || v_suffix, 'Editor123!', 'Smoke Editor', v_author_id);
    pkg_admin.set_user_active(v_admin_id, v_author_id, 0);
    BEGIN
        pkg_admin.create_topic(v_author_id, 'Blocked topic', 'Should fail for inactive author', v_topic_id);
        RAISE_APPLICATION_ERROR(-20983, 'Inactive author was able to create content.');
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLCODE != -20100 THEN
                RAISE;
            END IF;
    END;
    pkg_admin.set_user_active(v_admin_id, v_author_id, 1);
    pkg_admin.create_topic(v_author_id, 'Smoke content ' || v_suffix, 'Temporary author material', v_topic_id);
    pkg_admin.create_category(v_author_id, v_topic_id, 'Author category', v_category_id);

    SELECT COUNT(*) INTO v_count
      FROM categories
     WHERE category_id = v_category_id
       AND topic_id = v_topic_id;
    IF v_count <> 1 THEN
        RAISE_APPLICATION_ERROR(-20993, 'AUTHOR could not create a category.');
    END IF;

    pkg_admin.create_quiz(v_author_id, v_topic_id, 'Temporary draft', NULL, 'QUIZ', 10, NULL, 1, 'PUBLIC', v_quiz_id);
    pkg_admin.set_quiz_feedback(v_author_id, v_quiz_id, 0);
    SELECT show_feedback INTO v_count FROM quizzes WHERE quiz_id = v_quiz_id;
    IF v_count <> 0 THEN
        RAISE_APPLICATION_ERROR(-20994, 'Could not update show_feedback for draft quiz.');
    END IF;
    pkg_admin.set_quiz_feedback(v_author_id, v_quiz_id, 1);
    pkg_admin.set_quiz_attempt_limit(v_author_id, v_quiz_id, 1);
    SELECT attempt_limit INTO v_count FROM quizzes WHERE quiz_id = v_quiz_id;
    IF v_count <> 1 THEN
        RAISE_APPLICATION_ERROR(-20985, 'Could not update attempt_limit for draft quiz.');
    END IF;
    pkg_admin.add_question(
        v_author_id, v_quiz_id, v_category_id, 'TEXT', 'EASY',
        'Temporary question', 'answer', NULL, 1, v_question_id
    );
    pkg_admin.update_question(
        v_author_id, v_question_id, v_category_id, 'SINGLE_CHOICE', 'MEDIUM',
        'Edited question', NULL, 'Edited explanation', 2
    );
    pkg_admin.add_option(v_author_id, v_question_id, 'Correct', 1, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, 'Wrong', 0, v_option_id);
    SELECT COUNT(*) INTO v_count
      FROM questions q
      JOIN question_options qo ON qo.question_id = q.question_id
     WHERE q.question_id = v_question_id
       AND q.question_text = 'Edited question';
    IF v_count <> 2 THEN
        RAISE_APPLICATION_ERROR(-20990, 'AUTHOR could not edit a draft question and replace its options.');
    END IF;
    pkg_admin.publish_quiz(v_author_id, v_quiz_id);
    pkg_testing.start_attempt(v_author_id, v_quiz_id, v_attempt_id);
    pkg_testing.finish_attempt(v_attempt_id);
    BEGIN
        pkg_testing.start_attempt(v_author_id, v_quiz_id, v_failed_attempt_id);
        RAISE_APPLICATION_ERROR(-20986, 'Attempt limit did not block second try.');
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLCODE != -20211 THEN
                RAISE;
            END IF;
    END;

    pkg_admin.delete_question(v_author_id, v_question_id);
    SELECT max_points INTO v_count FROM attempts WHERE attempt_id = v_attempt_id;
    IF v_count <> 0 THEN
        RAISE_APPLICATION_ERROR(-20989, 'Deleting question did not recalculate existing attempt totals.');
    END IF;

    pkg_admin.delete_quiz(v_author_id, v_quiz_id);
    SELECT COUNT(*) INTO v_count FROM quizzes WHERE quiz_id = v_quiz_id;
    IF v_count <> 0 THEN
        RAISE_APPLICATION_ERROR(-20988, 'AUTHOR could not delete own quiz.');
    END IF;
    SELECT COUNT(*) INTO v_count FROM attempts WHERE quiz_id = v_quiz_id;
    IF v_count <> 0 THEN
        RAISE_APPLICATION_ERROR(-20987, 'Deleting quiz did not reset quiz statistics (attempts).');
    END IF;

    pkg_admin.delete_category(v_admin_id, v_category_id);
    pkg_admin.delete_topic(v_admin_id, v_topic_id);

    pkg_admin.create_topic(v_author_id, 'Smoke reset ' || v_suffix, NULL, v_topic_id);
    pkg_admin.create_category(v_author_id, v_topic_id, 'Reset', v_category_id);
    pkg_admin.create_quiz(v_author_id, v_topic_id, 'Reset test', NULL, 'QUIZ', 10, NULL, 1, 'PUBLIC', v_demo_quiz_id);
    pkg_admin.add_question(v_author_id, v_demo_quiz_id, v_category_id, 'TEXT', 'EASY', 'Reset question', 'yes', NULL, 1, v_question_id);
    pkg_admin.publish_quiz(v_author_id, v_demo_quiz_id);
    pkg_testing.start_attempt(v_author_id, v_demo_quiz_id, v_attempt_id);
    pkg_testing.abandon_user_attempts(v_author_id);
    SELECT COUNT(*) INTO v_count
      FROM attempts
     WHERE attempt_id = v_attempt_id
       AND status = 'EXPIRED';
    IF v_count <> 1 THEN
        RAISE_APPLICATION_ERROR(-20984, 'Abandoning active attempts did not mark attempt as EXPIRED.');
    END IF;
    pkg_admin.reset_user_quiz_attempts(v_admin_id, v_author_id, v_demo_quiz_id);
    SELECT COUNT(*) INTO v_count FROM attempts WHERE user_id = v_author_id AND quiz_id = v_demo_quiz_id;
    IF v_count <> 0 THEN
        RAISE_APPLICATION_ERROR(-20992, 'ADMIN could not reset attempts for selected quiz.');
    END IF;

    pkg_testing.start_attempt(v_author_id, v_demo_quiz_id, v_attempt_id);
    pkg_admin.reset_user_progress(v_admin_id, v_author_id);
    SELECT COUNT(*) INTO v_count FROM attempts WHERE user_id = v_author_id;
    IF v_count <> 0 THEN
        RAISE_APPLICATION_ERROR(-20991, 'ADMIN could not reset all user attempts.');
    END IF;

    DBMS_OUTPUT.PUT_LINE('Content management smoke test successful. AUTHOR deletion and stats recalculation verified.');
    ROLLBACK TO before_content_management_test;
EXCEPTION WHEN OTHERS THEN
    ROLLBACK TO before_content_management_test;
    RAISE;
END;
/

