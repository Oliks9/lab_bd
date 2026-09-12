SET SERVEROUTPUT ON
DECLARE
    v_admin_id NUMBER;
    v_user_id NUMBER;
    v_topic_id NUMBER;
    v_category_id NUMBER;
    v_option_id NUMBER;
    v_types SYS.ODCIVARCHAR2LIST := SYS.ODCIVARCHAR2LIST(
        'SINGLE_CHOICE', 'MULTIPLE_CHOICE', 'TEXT', 'NUMBER', 'BOOLEAN', 'ORDERING');
    v_login VARCHAR2(50);
    v_quiz_id NUMBER;
    v_attempt_id NUMBER;
    v_question_id NUMBER;
    v_option_ids VARCHAR2(1000);
    v_score NUMBER;
BEGIN
    SAVEPOINT before_testing_smoke_test;
    v_login := 'smoke_player_' || LOWER(RAWTOHEX(SYS_GUID()));
    pr_register_user(v_login, 'Smoke123!', 'Smoke Player', v_user_id);
    SELECT user_id INTO v_admin_id FROM app_users WHERE role_code = 'ADMIN' AND is_active = 1 AND ROWNUM = 1;
    pkg_admin.create_topic(v_admin_id, v_login, NULL, v_topic_id);
    pkg_admin.create_category(v_admin_id, v_topic_id, 'Six types', v_category_id);
    pkg_admin.create_quiz(v_admin_id, v_topic_id, 'Six types test', NULL, 'QUIZ', 10, NULL, 1, 'PUBLIC', v_quiz_id);
    FOR i IN 1..v_types.COUNT LOOP
        pkg_admin.add_question(v_admin_id, v_quiz_id, v_category_id, v_types(i), 'EASY',
            'Question ' || i, CASE v_types(i) WHEN 'TEXT' THEN 'COMMIT' WHEN 'NUMBER' THEN '2' END,
            NULL, 1, v_question_id);
        IF v_types(i) IN ('SINGLE_CHOICE', 'BOOLEAN') THEN
            pkg_admin.add_option(v_admin_id, v_question_id, 'Correct', 1, v_option_id);
            pkg_admin.add_option(v_admin_id, v_question_id, 'Wrong', 0, v_option_id);
        ELSIF v_types(i) IN ('MULTIPLE_CHOICE', 'ORDERING') THEN
            FOR j IN 1..3 LOOP
                pkg_admin.add_option(v_admin_id, v_question_id, 'Option ' || j,
                    CASE WHEN v_types(i) = 'ORDERING' OR j < 3 THEN 1 ELSE 0 END, v_option_id);
            END LOOP;
        END IF;
    END LOOP;
    pkg_admin.publish_quiz(v_admin_id, v_quiz_id);
    pkg_testing.start_attempt(v_user_id, v_quiz_id, v_attempt_id);

    SELECT q.question_id, TO_CHAR(qo.option_id)
      INTO v_question_id, v_option_ids
      FROM questions q
      JOIN question_options qo ON qo.question_id = q.question_id AND qo.is_correct = 1
     WHERE q.quiz_id = v_quiz_id
       AND q.seq_no = 1;
    pkg_testing.submit_answer(v_attempt_id, v_question_id, v_option_ids, NULL);

    SELECT q.question_id, LISTAGG(TO_CHAR(qo.option_id), ',') WITHIN GROUP (ORDER BY qo.seq_no)
      INTO v_question_id, v_option_ids
      FROM questions q
      JOIN question_options qo ON qo.question_id = q.question_id AND qo.is_correct = 1
     WHERE q.quiz_id = v_quiz_id
       AND q.seq_no = 2
     GROUP BY q.question_id;
    pkg_testing.submit_answer(v_attempt_id, v_question_id, v_option_ids, NULL);

    SELECT question_id INTO v_question_id FROM questions WHERE quiz_id = v_quiz_id AND seq_no = 3;
    pkg_testing.submit_answer(v_attempt_id, v_question_id, NULL, 'COMMIT');

    SELECT question_id INTO v_question_id FROM questions WHERE quiz_id = v_quiz_id AND seq_no = 4;
    pkg_testing.submit_answer(v_attempt_id, v_question_id, NULL, '2');

    SELECT q.question_id, TO_CHAR(qo.option_id)
      INTO v_question_id, v_option_ids
      FROM questions q
      JOIN question_options qo ON qo.question_id = q.question_id AND qo.is_correct = 1
     WHERE q.quiz_id = v_quiz_id
       AND q.seq_no = 5;
    pkg_testing.submit_answer(v_attempt_id, v_question_id, v_option_ids, NULL);

    SELECT q.question_id, LISTAGG(TO_CHAR(qo.option_id), ',') WITHIN GROUP (ORDER BY qo.seq_no)
      INTO v_question_id, v_option_ids
      FROM questions q
      JOIN question_options qo ON qo.question_id = q.question_id
     WHERE q.quiz_id = v_quiz_id
       AND q.seq_no = 6
     GROUP BY q.question_id;
    pkg_testing.submit_answer(v_attempt_id, v_question_id, v_option_ids, NULL);

    SELECT COUNT(*) INTO v_score FROM attempts
     WHERE attempt_id = v_attempt_id AND status = 'FINISHED';
    IF v_score <> 1 THEN
        RAISE_APPLICATION_ERROR(-20997, 'The final answer did not finish the attempt in Oracle.');
    END IF;
    pkg_testing.finish_attempt(v_attempt_id);
    SELECT score_percent INTO v_score FROM attempts WHERE attempt_id = v_attempt_id;

    IF v_score <> 100 THEN
        RAISE_APPLICATION_ERROR(-20997, 'Testing smoke test expected 100%, got ' || v_score || '%.');
    END IF;

    DBMS_OUTPUT.PUT_LINE('Testing smoke test successful. Six answer types scored: ' || v_score || '%');
    ROLLBACK TO before_testing_smoke_test;
EXCEPTION WHEN OTHERS THEN
    ROLLBACK TO before_testing_smoke_test;
    RAISE;
END;
/
