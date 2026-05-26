CREATE OR REPLACE PACKAGE BODY pkg_testing AS
    PROCEDURE start_attempt (
        p_user_id IN NUMBER,
        p_quiz_id IN NUMBER,
        p_attempt_id OUT NUMBER
    ) IS
        v_duration quizzes.duration_minutes%TYPE;
        v_limit quizzes.question_limit%TYPE;
        v_count NUMBER;
    BEGIN
        IF fn_can_access_quiz(p_user_id, p_quiz_id) = 0 THEN
            RAISE_APPLICATION_ERROR(-20200, 'Тест недоступен или еще не опубликован.');
        END IF;

        SELECT duration_minutes, question_limit
          INTO v_duration, v_limit
          FROM quizzes
         WHERE quiz_id = p_quiz_id;

        INSERT INTO attempts (user_id, quiz_id, deadline_at)
        VALUES (p_user_id, p_quiz_id, SYSTIMESTAMP + NUMTODSINTERVAL(v_duration, 'MINUTE'))
        RETURNING attempt_id INTO p_attempt_id;

        INSERT INTO attempt_questions (attempt_id, question_id, display_order)
        SELECT p_attempt_id, question_id, row_number_value
          FROM (
                SELECT q.question_id, ROW_NUMBER() OVER (ORDER BY q.seq_no) AS row_number_value
                  FROM questions q
                 WHERE q.quiz_id = p_quiz_id
          )
         WHERE v_limit IS NULL OR row_number_value <= v_limit;

        SELECT COUNT(*) INTO v_count FROM attempt_questions WHERE attempt_id = p_attempt_id;
        IF v_count = 0 THEN
            RAISE_APPLICATION_ERROR(-20201, 'В опубликованном тесте отсутствуют вопросы.');
        END IF;
    END;

    PROCEDURE submit_answer (
        p_attempt_id IN NUMBER,
        p_question_id IN NUMBER,
        p_selected_option_ids IN VARCHAR2,
        p_text_answer IN VARCHAR2
    ) IS
        v_status attempts.status%TYPE;
        v_deadline attempts.deadline_at%TYPE;
        v_type questions.type_code%TYPE;
        v_expected questions.expected_answer%TYPE;
        v_points questions.points%TYPE;
        v_answer_id NUMBER;
        v_clean_ids VARCHAR2(4000) := REPLACE(TRIM(p_selected_option_ids), ' ', '');
        v_selected_count NUMBER := 0;
        v_selected_correct NUMBER := 0;
        v_correct_count NUMBER := 0;
        v_token_count NUMBER := 0;
        v_is_correct NUMBER(1) := 0;
    BEGIN
        SELECT a.status, a.deadline_at, q.type_code, q.expected_answer, q.points
          INTO v_status, v_deadline, v_type, v_expected, v_points
          FROM attempts a
          JOIN attempt_questions aq ON aq.attempt_id = a.attempt_id
          JOIN questions q ON q.question_id = aq.question_id
         WHERE a.attempt_id = p_attempt_id
           AND q.question_id = p_question_id
         FOR UPDATE OF a.status;

        IF v_status <> 'IN_PROGRESS' THEN
            RAISE_APPLICATION_ERROR(-20202, 'Попытка уже завершена.');
        END IF;
        IF v_deadline IS NOT NULL AND SYSTIMESTAMP > v_deadline THEN
            RAISE_APPLICATION_ERROR(-20203, 'Время прохождения истекло. Завершите попытку.');
        END IF;

        DELETE FROM user_answers
         WHERE attempt_id = p_attempt_id
           AND question_id = p_question_id;

        INSERT INTO user_answers (attempt_id, question_id, text_answer)
        VALUES (p_attempt_id, p_question_id, TRIM(p_text_answer))
        RETURNING answer_id INTO v_answer_id;

        IF v_type IN ('SINGLE_CHOICE', 'MULTIPLE_CHOICE', 'BOOLEAN') THEN
            IF v_clean_ids IS NULL OR NOT REGEXP_LIKE(v_clean_ids, '^[0-9]+(,[0-9]+)*$') THEN
                RAISE_APPLICATION_ERROR(-20204, 'Выберите допустимый вариант ответа.');
            END IF;

            v_token_count := REGEXP_COUNT(v_clean_ids, '[^,]+');
            INSERT INTO answer_choices (answer_id, option_id)
            SELECT v_answer_id, qo.option_id
              FROM question_options qo
             WHERE qo.question_id = p_question_id
               AND INSTR(',' || v_clean_ids || ',', ',' || TO_CHAR(qo.option_id) || ',') > 0;
            v_selected_count := SQL%ROWCOUNT;

            IF v_selected_count <> v_token_count OR (v_type IN ('SINGLE_CHOICE', 'BOOLEAN') AND v_selected_count <> 1) THEN
                RAISE_APPLICATION_ERROR(-20205, 'Выбран некорректный набор вариантов.');
            END IF;

            SELECT COUNT(*), NVL(SUM(qo.is_correct), 0)
              INTO v_selected_count, v_selected_correct
              FROM answer_choices ac
              JOIN question_options qo ON qo.option_id = ac.option_id
             WHERE ac.answer_id = v_answer_id;
            SELECT COUNT(*) INTO v_correct_count
              FROM question_options
             WHERE question_id = p_question_id
               AND is_correct = 1;

            IF v_selected_count = v_correct_count AND v_selected_correct = v_correct_count THEN
                v_is_correct := 1;
            END IF;
        ELSIF v_type = 'NUMBER' THEN
            BEGIN
                IF TO_NUMBER(REPLACE(TRIM(p_text_answer), ',', '.')) =
                   TO_NUMBER(REPLACE(TRIM(v_expected), ',', '.')) THEN
                    v_is_correct := 1;
                END IF;
            EXCEPTION
                WHEN VALUE_ERROR THEN
                    v_is_correct := 0;
            END;
        ELSE
            IF UPPER(TRIM(p_text_answer)) = UPPER(TRIM(v_expected)) THEN
                v_is_correct := 1;
            END IF;
        END IF;

        UPDATE user_answers
           SET is_correct = v_is_correct,
               awarded_points = CASE WHEN v_is_correct = 1 THEN v_points ELSE 0 END
         WHERE answer_id = v_answer_id;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20206, 'Вопрос не входит в текущую попытку.');
    END;

    PROCEDURE finish_attempt (
        p_attempt_id IN NUMBER
    ) IS
        v_status attempts.status%TYPE;
        v_deadline attempts.deadline_at%TYPE;
        v_awarded NUMBER;
        v_max NUMBER;
        v_result_status VARCHAR2(20);
    BEGIN
        SELECT status, deadline_at
          INTO v_status, v_deadline
          FROM attempts
         WHERE attempt_id = p_attempt_id
         FOR UPDATE;
        IF v_status <> 'IN_PROGRESS' THEN
            RETURN;
        END IF;

        SELECT NVL(SUM(ua.awarded_points), 0), NVL(SUM(q.points), 0)
          INTO v_awarded, v_max
          FROM attempt_questions aq
          JOIN questions q ON q.question_id = aq.question_id
          LEFT JOIN user_answers ua
            ON ua.attempt_id = aq.attempt_id
           AND ua.question_id = aq.question_id
         WHERE aq.attempt_id = p_attempt_id;

        v_result_status := CASE
            WHEN v_deadline IS NOT NULL AND SYSTIMESTAMP > v_deadline THEN 'EXPIRED'
            ELSE 'FINISHED'
        END;
        UPDATE attempts
           SET status = v_result_status,
               finished_at = SYSTIMESTAMP,
               awarded_points = v_awarded,
               max_points = v_max,
               score_percent = fn_attempt_percent(p_attempt_id)
         WHERE attempt_id = p_attempt_id;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20207, 'Попытка не найдена.');
    END;
END pkg_testing;
/
