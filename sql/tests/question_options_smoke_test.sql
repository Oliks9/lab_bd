SET SERVEROUTPUT ON
DECLARE
    v_admin NUMBER;
    v_topic NUMBER;
    v_category NUMBER;
    v_quiz NUMBER;
    v_question NUMBER;
    v_option NUMBER;
    v_count NUMBER;
    v_seq NUMBER;
    v_player NUMBER;
    v_attempt NUMBER;
    v_first_correct NUMBER;
    v_second_correct NUMBER;

    PROCEDURE check_ok(p_ok BOOLEAN, p_message VARCHAR2) IS
    BEGIN
        IF p_ok IS NULL OR NOT p_ok THEN
            RAISE_APPLICATION_ERROR(-20984, p_message);
        END IF;
    END;

    PROCEDURE reject_extra_correct IS
    BEGIN
        BEGIN
            pkg_admin.add_option(v_admin, v_question, 'Another correct', 1, v_option);
            RAISE_APPLICATION_ERROR(-20984, 'Second correct option accepted');
        EXCEPTION WHEN OTHERS THEN
            IF SQLCODE <> -20142 THEN RAISE; END IF;
        END;
        SELECT COUNT(*) INTO v_count FROM question_options
         WHERE question_id = v_question AND is_correct = 1;
        check_ok(v_count = 1, 'Rejected option changed stored answers');
    END;

    PROCEDURE reject_publication(p_code NUMBER DEFAULT -20109) IS
    BEGIN
        BEGIN
            pkg_admin.publish_quiz(v_admin, v_quiz);
            RAISE_APPLICATION_ERROR(-20984, 'Invalid question published');
        EXCEPTION WHEN OTHERS THEN
            IF SQLCODE <> p_code THEN RAISE; END IF;
        END;
    END;

    PROCEDURE reject_validation(p_code NUMBER) IS
    BEGIN
        BEGIN
            pkg_admin.validate_question(v_admin, v_question);
            RAISE_APPLICATION_ERROR(-20984, 'Invalid question passed final validation');
        EXCEPTION WHEN OTHERS THEN
            IF SQLCODE <> p_code THEN RAISE; END IF;
        END;
    END;
BEGIN
    SAVEPOINT question_options_test;
    SELECT user_id INTO v_admin FROM app_users WHERE role_code = 'ADMIN' AND is_active = 1 AND ROWNUM = 1;
    pkg_admin.create_topic(v_admin, 'Options ' || RAWTOHEX(SYS_GUID()), NULL, v_topic);
    pkg_admin.create_category(v_admin, v_topic, 'Options', v_category);
    pkg_admin.create_quiz(v_admin, v_topic, 'Answer count', NULL, 'QUIZ', 10, NULL, 1, 'PUBLIC', v_quiz);
    pkg_admin.add_question(v_admin, v_quiz, v_category, 'SINGLE_CHOICE', 'EASY', 'One answer', NULL, NULL, 1, v_question);
    pkg_admin.add_option(v_admin, v_question, 'Wrong one', 0, v_option);
    pkg_admin.add_option(v_admin, v_question, 'Wrong two', 0, v_option);
    reject_validation(-20109);
    reject_publication;
    pkg_admin.add_option(v_admin, v_question, 'Correct', 1, v_option);
    reject_extra_correct;
    pkg_admin.add_option(v_admin, v_question, 'Wrong three', 0, v_option);
    SELECT COUNT(*), MAX(seq_no) INTO v_count, v_seq FROM question_options WHERE question_id = v_question;
    check_ok(v_count = 4 AND v_seq = 4, 'Rejected option left a sequence gap');
    INSERT INTO question_options(question_id, seq_no, option_text, is_correct)
    VALUES(v_question, 5, 'Legacy invalid correct', 1);
    reject_publication;
    DELETE FROM question_options WHERE question_id = v_question AND seq_no = 5;
    pkg_admin.publish_quiz(v_admin, v_quiz);
    pkg_admin.archive_quiz(v_admin, v_quiz);

    pkg_admin.update_question(v_admin, v_question, v_category, 'BOOLEAN', 'EASY', 'True or false', NULL, NULL, 1);
    pkg_admin.add_option(v_admin, v_question, 'True', 1, v_option);
    reject_extra_correct;
    pkg_admin.add_option(v_admin, v_question, 'False', 0, v_option);
    pkg_admin.publish_quiz(v_admin, v_quiz);
    pkg_admin.archive_quiz(v_admin, v_quiz);

    FOR item IN (SELECT 'MULTIPLE_CHOICE' AS code FROM dual UNION ALL SELECT 'ORDERING' FROM dual) LOOP
        pkg_admin.update_question(v_admin, v_question, v_category, item.code, 'EASY', 'Several answers', NULL, NULL, 1);
        pkg_admin.add_option(v_admin, v_question, 'First', 1, v_option);
        pkg_admin.add_option(v_admin, v_question, 'Second', 1, v_option);
        SELECT COUNT(*) INTO v_count FROM question_options WHERE question_id = v_question AND is_correct = 1;
        check_ok(v_count = 2, 'Multiple correct options must remain supported');
        pkg_admin.validate_question(v_admin, v_question);
        pkg_admin.publish_quiz(v_admin, v_quiz);
        pkg_admin.archive_quiz(v_admin, v_quiz);
    END LOOP;
    pkg_admin.update_question(v_admin, v_question, v_category, 'SINGLE_CHOICE', 'EASY', 'Changed to single', NULL, NULL, 1);
    pkg_admin.add_option(v_admin, v_question, 'Wrong', 0, v_option);
    pkg_admin.add_option(v_admin, v_question, 'Correct', 1, v_option);
    reject_extra_correct;
    pkg_admin.publish_quiz(v_admin, v_quiz);
    pkg_admin.archive_quiz(v_admin, v_quiz);
    pkg_admin.update_question(v_admin, v_question, v_category, 'MULTIPLE_CHOICE', 'EASY', 'At least two', NULL, NULL, 1);
    pkg_admin.add_option(v_admin, v_question, 'Wrong', 0, v_option);
    reject_validation(-20143);
    reject_publication(-20143);
    pkg_admin.add_option(v_admin, v_question, 'First correct', 1, v_first_correct);
    reject_validation(-20143);
    reject_publication(-20143);
    pkg_admin.add_option(v_admin, v_question, 'Second correct', 1, v_second_correct);
    pkg_admin.validate_question(v_admin, v_question);
    pkg_admin.publish_quiz(v_admin, v_quiz);
    pr_register_user('multi_' || LOWER(RAWTOHEX(SYS_GUID())), 'MultiCheck123!', 'Multiple answers', v_player);
    pkg_testing.start_attempt(v_player, v_quiz, v_attempt);
    pkg_testing.submit_answer(v_attempt, v_question, TO_CHAR(v_first_correct), NULL);
    SELECT score_percent INTO v_count FROM attempts WHERE attempt_id = v_attempt;
    check_ok(v_count = 0, 'One selected answer must not earn points for multiple choice');
    pkg_testing.start_attempt(v_player, v_quiz, v_attempt);
    pkg_testing.submit_answer(v_attempt, v_question, TO_CHAR(v_first_correct) || ',' || TO_CHAR(v_second_correct), NULL);
    SELECT score_percent INTO v_count FROM attempts WHERE attempt_id = v_attempt;
    check_ok(v_count = 100, 'All correct options must earn full points');
    ROLLBACK TO question_options_test;
    DBMS_OUTPUT.PUT_LINE('Question options smoke test passed: single, boolean, multiple, ordering and type changes.');
EXCEPTION WHEN OTHERS THEN
    ROLLBACK TO question_options_test;
    RAISE;
END;
/
