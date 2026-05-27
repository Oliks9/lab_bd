SET SERVEROUTPUT ON
DECLARE
    v_admin_id NUMBER;
    v_author_id NUMBER;
    v_topic_id NUMBER;
    v_category_id NUMBER;
    v_quiz_id NUMBER;
    v_demo_quiz_id NUMBER;
    v_question_id NUMBER;
    v_option_id NUMBER;
    v_attempt_id NUMBER;
    v_name VARCHAR2(200);
    v_role VARCHAR2(20);
    v_count NUMBER;
BEGIN
    SAVEPOINT before_content_management_test;

    pr_login('admin', 'Admin123!', v_admin_id, v_name, v_role);
    pkg_admin.create_author(v_admin_id, 'smoke_editor', 'Editor123!', 'Smoke Editor', v_author_id);
    pkg_admin.create_topic(v_author_id, 'Smoke content topic', 'Temporary author material', v_topic_id);
    pkg_admin.create_category(v_author_id, v_topic_id, 'Author category', v_category_id);

    SELECT COUNT(*) INTO v_count
      FROM categories
     WHERE category_id = v_category_id
       AND topic_id = v_topic_id;
    IF v_count <> 1 THEN
        RAISE_APPLICATION_ERROR(-20993, 'AUTHOR could not create a category.');
    END IF;

    pkg_admin.create_quiz(v_author_id, v_topic_id, 'Temporary draft', NULL, 'QUIZ', 10, 1, 'PUBLIC', v_quiz_id);
    pkg_admin.set_quiz_feedback(v_author_id, v_quiz_id, 0);
    SELECT show_feedback INTO v_count FROM quizzes WHERE quiz_id = v_quiz_id;
    IF v_count <> 0 THEN
        RAISE_APPLICATION_ERROR(-20994, 'Could not update show_feedback for draft quiz.');
    END IF;
    pkg_admin.set_quiz_feedback(v_author_id, v_quiz_id, 1);
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

    SELECT quiz_id INTO v_demo_quiz_id FROM quizzes WHERE title = 'Oracle: основы серверной логики';
    pkg_testing.start_attempt(v_author_id, v_demo_quiz_id, v_attempt_id);
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
END;
/
