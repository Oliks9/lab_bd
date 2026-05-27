CREATE OR REPLACE PACKAGE BODY pkg_testing AS
    PROCEDURE advance_active_question (
        p_attempt_id IN NUMBER,
        p_active_order IN NUMBER
    ) IS
        v_total_questions NUMBER;
    BEGIN
        SELECT COUNT(*)
          INTO v_total_questions
          FROM attempt_questions
         WHERE attempt_id = p_attempt_id;

        IF p_active_order < v_total_questions THEN
            UPDATE attempts
               SET active_question_order = p_active_order + 1,
                   question_started_at = SYSTIMESTAMP
             WHERE attempt_id = p_attempt_id;
        ELSE
            UPDATE attempts
               SET active_question_order = v_total_questions + 1,
                   question_started_at = NULL
             WHERE attempt_id = p_attempt_id;
        END IF;
    END;

    PROCEDURE start_attempt (
        p_user_id IN NUMBER,
        p_quiz_id IN NUMBER,
        p_attempt_id OUT NUMBER
    ) IS
        v_duration quizzes.duration_minutes%TYPE;
        v_limit quizzes.question_limit%TYPE;
        v_timer_mode quizzes.timer_mode%TYPE;
        v_attempt_limit quizzes.attempt_limit%TYPE;
        v_user_attempt_count NUMBER;
        v_count NUMBER;
    BEGIN
        IF fn_can_access_quiz(p_user_id, p_quiz_id) = 0 THEN
            RAISE_APPLICATION_ERROR(-20200, 'Quiz is unavailable or not published.');
        END IF;

        SELECT duration_minutes, question_limit, timer_mode, attempt_limit
          INTO v_duration, v_limit, v_timer_mode, v_attempt_limit
          FROM quizzes
         WHERE quiz_id = p_quiz_id;

        IF v_attempt_limit IS NOT NULL THEN
            SELECT COUNT(*)
              INTO v_user_attempt_count
              FROM attempts
             WHERE user_id = p_user_id
               AND quiz_id = p_quiz_id;
            IF v_user_attempt_count >= v_attempt_limit THEN
                RAISE_APPLICATION_ERROR(-20211, 'Attempt limit for this quiz has been reached.');
            END IF;
        END IF;

        INSERT INTO attempts (
            user_id,
            quiz_id,
            deadline_at,
            timer_mode,
            question_duration_minutes,
            active_question_order,
            question_started_at
        )
        VALUES (
            p_user_id,
            p_quiz_id,
            CASE
                WHEN v_timer_mode = 'QUIZ' THEN SYSTIMESTAMP + NUMTODSINTERVAL(v_duration, 'MINUTE')
                ELSE NULL
            END,
            v_timer_mode,
            CASE WHEN v_timer_mode = 'QUESTION' THEN v_duration ELSE NULL END,
            CASE WHEN v_timer_mode = 'QUESTION' THEN 1 ELSE NULL END,
            CASE WHEN v_timer_mode = 'QUESTION' THEN SYSTIMESTAMP ELSE NULL END
        )
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
            RAISE_APPLICATION_ERROR(-20201, 'Published quiz has no questions.');
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
        v_timer_mode attempts.timer_mode%TYPE;
        v_question_duration attempts.question_duration_minutes%TYPE;
        v_active_order attempts.active_question_order%TYPE;
        v_question_started attempts.question_started_at%TYPE;
        v_display_order attempt_questions.display_order%TYPE;
        v_type questions.type_code%TYPE;
        v_expected questions.expected_answer%TYPE;
        v_points questions.points%TYPE;
        v_answer_id NUMBER;
        v_clean_ids VARCHAR2(4000) := REPLACE(TRIM(p_selected_option_ids), ' ', '');
        v_selected_count NUMBER := 0;
        v_selected_correct NUMBER := 0;
        v_correct_count NUMBER := 0;
        v_token_count NUMBER := 0;
        v_total_option_count NUMBER := 0;
        v_ordered_correct_ids VARCHAR2(4000);
        v_is_correct NUMBER(1) := 0;
        v_text_to_store VARCHAR2(1000);
    BEGIN
        SELECT
            a.status,
            a.deadline_at,
            a.timer_mode,
            a.question_duration_minutes,
            a.active_question_order,
            a.question_started_at,
            aq.display_order,
            q.type_code,
            q.expected_answer,
            q.points
          INTO
            v_status,
            v_deadline,
            v_timer_mode,
            v_question_duration,
            v_active_order,
            v_question_started,
            v_display_order,
            v_type,
            v_expected,
            v_points
          FROM attempts a
          JOIN attempt_questions aq ON aq.attempt_id = a.attempt_id
          JOIN questions q ON q.question_id = aq.question_id
         WHERE a.attempt_id = p_attempt_id
           AND q.question_id = p_question_id
         FOR UPDATE OF a.status, a.active_question_order, a.question_started_at;

        IF v_status <> 'IN_PROGRESS' THEN
            RAISE_APPLICATION_ERROR(-20202, 'Attempt is already finished.');
        END IF;

        IF v_timer_mode = 'QUIZ' THEN
            IF v_deadline IS NOT NULL AND SYSTIMESTAMP > v_deadline THEN
                RAISE_APPLICATION_ERROR(-20203, 'Time limit has expired.');
            END IF;
        ELSE
            IF v_active_order IS NULL THEN
                RAISE_APPLICATION_ERROR(-20202, 'Attempt is already finished.');
            END IF;
            IF v_display_order <> v_active_order THEN
                RAISE_APPLICATION_ERROR(-20208, 'Answer questions in order.');
            END IF;
            IF v_question_duration IS NULL THEN
                v_question_duration := 1;
            END IF;
            IF v_question_started IS NULL THEN
                v_question_started := SYSTIMESTAMP;
                UPDATE attempts
                   SET question_started_at = v_question_started
                 WHERE attempt_id = p_attempt_id;
            END IF;
            IF SYSTIMESTAMP > v_question_started + NUMTODSINTERVAL(v_question_duration, 'MINUTE') THEN
                RAISE_APPLICATION_ERROR(-20203, 'Time limit has expired.');
            END IF;
        END IF;

        IF v_type = 'ORDERING' THEN
            v_text_to_store := v_clean_ids;
        ELSE
            v_text_to_store := TRIM(p_text_answer);
        END IF;

        DELETE FROM user_answers
         WHERE attempt_id = p_attempt_id
           AND question_id = p_question_id;

        INSERT INTO user_answers (attempt_id, question_id, text_answer)
        VALUES (p_attempt_id, p_question_id, v_text_to_store)
        RETURNING answer_id INTO v_answer_id;

        IF v_type IN ('SINGLE_CHOICE', 'MULTIPLE_CHOICE', 'BOOLEAN', 'ORDERING') THEN
            IF v_clean_ids IS NULL OR NOT REGEXP_LIKE(v_clean_ids, '^[0-9]+(,[0-9]+)*$') THEN
                RAISE_APPLICATION_ERROR(-20204, 'Select a valid answer option.');
            END IF;

            v_token_count := REGEXP_COUNT(v_clean_ids, '[^,]+');
            INSERT INTO answer_choices (answer_id, option_id)
            SELECT v_answer_id, qo.option_id
              FROM question_options qo
             WHERE qo.question_id = p_question_id
               AND INSTR(',' || v_clean_ids || ',', ',' || TO_CHAR(qo.option_id) || ',') > 0;
            v_selected_count := SQL%ROWCOUNT;

            IF v_selected_count <> v_token_count OR (v_type IN ('SINGLE_CHOICE', 'BOOLEAN') AND v_selected_count <> 1) THEN
                RAISE_APPLICATION_ERROR(-20205, 'Selected options are invalid.');
            END IF;

            IF v_type = 'ORDERING' THEN
                SELECT COUNT(*)
                  INTO v_total_option_count
                  FROM question_options
                 WHERE question_id = p_question_id;
                IF v_total_option_count < 2 THEN
                    RAISE_APPLICATION_ERROR(-20209, 'Ordering question is not configured correctly.');
                END IF;
                IF v_selected_count <> v_total_option_count THEN
                    RAISE_APPLICATION_ERROR(-20205, 'Selected options are invalid.');
                END IF;

                SELECT LISTAGG(TO_CHAR(option_id), ',') WITHIN GROUP (ORDER BY seq_no)
                  INTO v_ordered_correct_ids
                  FROM question_options
                 WHERE question_id = p_question_id;

                IF v_clean_ids = v_ordered_correct_ids THEN
                    v_is_correct := 1;
                END IF;
            ELSE
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

        IF v_timer_mode = 'QUESTION' THEN
            advance_active_question(p_attempt_id, v_active_order);
        END IF;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20206, 'Question is not part of this attempt.');
    END;

    PROCEDURE expire_question (
        p_attempt_id IN NUMBER
    ) IS
        v_status attempts.status%TYPE;
        v_timer_mode attempts.timer_mode%TYPE;
        v_active_order attempts.active_question_order%TYPE;
    BEGIN
        SELECT status, timer_mode, active_question_order
          INTO v_status, v_timer_mode, v_active_order
          FROM attempts
         WHERE attempt_id = p_attempt_id
         FOR UPDATE OF status, active_question_order, question_started_at;

        IF v_status <> 'IN_PROGRESS' THEN
            RETURN;
        END IF;
        IF v_timer_mode <> 'QUESTION' THEN
            RAISE_APPLICATION_ERROR(-20210, 'Auto-advance is available only in QUESTION timer mode.');
        END IF;
        IF v_active_order IS NULL THEN
            RETURN;
        END IF;

        advance_active_question(p_attempt_id, v_active_order);
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20207, 'Attempt not found.');
    END;

    PROCEDURE finish_attempt (
        p_attempt_id IN NUMBER
    ) IS
        v_status attempts.status%TYPE;
        v_deadline attempts.deadline_at%TYPE;
        v_timer_mode attempts.timer_mode%TYPE;
        v_question_duration attempts.question_duration_minutes%TYPE;
        v_question_started attempts.question_started_at%TYPE;
        v_awarded NUMBER;
        v_max NUMBER;
        v_result_status VARCHAR2(20);
    BEGIN
        SELECT status, deadline_at, timer_mode, question_duration_minutes, question_started_at
          INTO v_status, v_deadline, v_timer_mode, v_question_duration, v_question_started
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
            WHEN v_timer_mode = 'QUIZ'
                 AND v_deadline IS NOT NULL
                 AND SYSTIMESTAMP > v_deadline THEN 'EXPIRED'
            WHEN v_timer_mode = 'QUESTION'
                 AND v_question_started IS NOT NULL
                 AND v_question_duration IS NOT NULL
                 AND SYSTIMESTAMP > v_question_started + NUMTODSINTERVAL(v_question_duration, 'MINUTE') THEN 'EXPIRED'
            ELSE 'FINISHED'
        END;
        UPDATE attempts
           SET status = v_result_status,
               finished_at = SYSTIMESTAMP,
               active_question_order = NULL,
               question_started_at = NULL,
               awarded_points = v_awarded,
               max_points = v_max,
               score_percent = fn_attempt_percent(p_attempt_id)
         WHERE attempt_id = p_attempt_id;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20207, 'Attempt not found.');
    END;

    PROCEDURE abandon_attempt (
        p_attempt_id IN NUMBER
    ) IS
    BEGIN
        finish_attempt(p_attempt_id);
        UPDATE attempts
           SET status = 'EXPIRED'
         WHERE attempt_id = p_attempt_id
           AND status = 'FINISHED';
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20207, 'Attempt not found.');
    END;

    PROCEDURE abandon_user_attempts (
        p_user_id IN NUMBER
    ) IS
    BEGIN
        FOR rec IN (
            SELECT attempt_id
              FROM attempts
             WHERE user_id = p_user_id
               AND status = 'IN_PROGRESS'
        ) LOOP
            abandon_attempt(rec.attempt_id);
        END LOOP;
    END;
END pkg_testing;
/

