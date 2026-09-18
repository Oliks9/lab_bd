SET SERVEROUTPUT ON
DECLARE
    v_logins SYS.ODCIVARCHAR2LIST := SYS.ODCIVARCHAR2LIST('author', 'student');
    v_titles SYS.ODCIVARCHAR2LIST := SYS.ODCIVARCHAR2LIST(
        'Oracle: основы серверной логики',
        'Математика: базовые знания',
        'Русский язык: базовые знания');
    v_user_id NUMBER;
    v_quiz_id NUMBER;
    v_attempt_id NUMBER;
    v_finished_count NUMBER;
    v_created_count NUMBER := 0;
    v_option_ids VARCHAR2(1000);
    v_text_answer VARCHAR2(1000);
    v_correct BOOLEAN;
BEGIN
    SAVEPOINT before_demo_attempts;
    FOR participant IN 1..v_logins.COUNT LOOP
        SELECT user_id INTO v_user_id FROM app_users
         WHERE login = v_logins(participant) AND is_active = 1
           AND role_code IN ('AUTHOR', 'USER') FOR UPDATE;
        FOR quiz_index IN 1..v_titles.COUNT LOOP
            SELECT quiz_id INTO v_quiz_id FROM quizzes
             WHERE title = v_titles(quiz_index) AND status = 'PUBLISHED'
               AND access_mode = 'PUBLIC';
            SELECT COUNT(*) INTO v_finished_count FROM attempts
             WHERE user_id = v_user_id AND quiz_id = v_quiz_id AND status = 'FINISHED';
            IF v_finished_count < 4 THEN
                FOR sample_number IN (v_finished_count + 1)..4 LOOP
                    pkg_testing.start_attempt(v_user_id, v_quiz_id, v_attempt_id);
                    FOR question IN (
                        SELECT q.question_id, q.type_code, q.expected_answer, aq.display_order
                          FROM attempt_questions aq JOIN questions q ON q.question_id = aq.question_id
                         WHERE aq.attempt_id = v_attempt_id ORDER BY aq.display_order
                    ) LOOP
                        v_correct := sample_number = 1
                            OR (sample_number = 2 AND MOD(question.display_order, 2) = MOD(participant + 1, 2))
                            OR (sample_number = 3 AND MOD(question.display_order, 2) = MOD(participant, 2));
                        v_option_ids := NULL;
                        v_text_answer := NULL;
                        IF question.type_code IN ('TEXT', 'NUMBER') THEN
                            IF v_correct THEN
                                v_text_answer := question.expected_answer;
                            ELSIF question.type_code = 'NUMBER' THEN
                                v_text_answer := CASE WHEN TO_NUMBER(question.expected_answer) = 0 THEN '1' ELSE '0' END;
                            ELSE
                                v_text_answer := 'Неверный демонстрационный ответ';
                            END IF;
                        ELSIF question.type_code = 'ORDERING' THEN
                            IF v_correct THEN
                                SELECT LISTAGG(TO_CHAR(option_id), ',') WITHIN GROUP (ORDER BY seq_no)
                                  INTO v_option_ids FROM question_options WHERE question_id = question.question_id;
                            ELSE
                                SELECT LISTAGG(TO_CHAR(option_id), ',') WITHIN GROUP (ORDER BY seq_no DESC)
                                  INTO v_option_ids FROM question_options WHERE question_id = question.question_id;
                            END IF;
                        ELSIF v_correct THEN
                            SELECT LISTAGG(TO_CHAR(option_id), ',') WITHIN GROUP (ORDER BY seq_no)
                              INTO v_option_ids FROM question_options
                             WHERE question_id = question.question_id AND is_correct = 1;
                        ELSE
                            SELECT TO_CHAR(MIN(option_id)) INTO v_option_ids FROM question_options
                             WHERE question_id = question.question_id AND is_correct = 0;
                        END IF;
                        pkg_testing.submit_answer(v_attempt_id, question.question_id, v_option_ids, v_text_answer);
                    END LOOP;
                    pkg_testing.finish_attempt(v_attempt_id);
                    SELECT COUNT(*) INTO v_finished_count FROM attempts
                     WHERE attempt_id = v_attempt_id AND status = 'FINISHED';
                    IF v_finished_count <> 1 THEN
                        RAISE_APPLICATION_ERROR(-20989, 'Демонстрационное прохождение не завершилось.');
                    END IF;
                    v_created_count := v_created_count + 1;
                END LOOP;
            END IF;
        END LOOP;
    END LOOP;
    DBMS_OUTPUT.PUT_LINE('Demo attempts created: ' || v_created_count);
EXCEPTION WHEN OTHERS THEN
    ROLLBACK TO before_demo_attempts;
    RAISE;
END;
/
