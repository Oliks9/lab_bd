CREATE OR REPLACE PACKAGE BODY pkg_admin AS
    FUNCTION actor_role(p_actor_id IN NUMBER) RETURN VARCHAR2 IS
        v_role app_users.role_code%TYPE;
    BEGIN
        SELECT role_code
          INTO v_role
          FROM app_users
         WHERE user_id = p_actor_id
           AND is_active = 1;
        RETURN v_role;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20100, 'Пользователь не найден или заблокирован.');
    END;

    PROCEDURE require_editor(p_actor_id IN NUMBER) IS
        v_role VARCHAR2(20);
    BEGIN
        v_role := actor_role(p_actor_id);
        IF v_role NOT IN ('ADMIN', 'AUTHOR') THEN
            RAISE_APPLICATION_ERROR(-20101, 'Создавать и изменять тесты может только автор или администратор.');
        END IF;
    END;

    PROCEDURE require_admin(p_actor_id IN NUMBER) IS
    BEGIN
        IF actor_role(p_actor_id) <> 'ADMIN' THEN
            RAISE_APPLICATION_ERROR(-20111, 'Эта операция доступна только администратору.');
        END IF;
    END;

    PROCEDURE require_quiz_owner(p_actor_id IN NUMBER, p_quiz_id IN NUMBER) IS
        v_count NUMBER;
        v_role VARCHAR2(20);
    BEGIN
        require_editor(p_actor_id);
        v_role := actor_role(p_actor_id);
        SELECT quiz_id
          INTO v_count
          FROM quizzes
         WHERE quiz_id = p_quiz_id
           AND status = 'DRAFT'
           AND (author_id = p_actor_id OR v_role = 'ADMIN') FOR UPDATE;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20102, 'Изменять можно только доступный черновик теста.');
    END;

    PROCEDURE require_quiz_manager(p_actor_id IN NUMBER, p_quiz_id IN NUMBER) IS
        v_count NUMBER;
        v_role VARCHAR2(20);
    BEGIN
        require_editor(p_actor_id);
        v_role := actor_role(p_actor_id);
        SELECT quiz_id
          INTO v_count
          FROM quizzes
         WHERE quiz_id = p_quiz_id
           AND (author_id = p_actor_id OR v_role = 'ADMIN') FOR UPDATE;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20125, 'Удалять можно только свой тест (или под ролью администратора).');
    END;

    PROCEDURE require_selection_pool(p_quiz_id NUMBER, p_exclude_question NUMBER DEFAULT NULL) IS
        v_quiz quizzes%ROWTYPE;
        v_count NUMBER;
    BEGIN
        SELECT * INTO v_quiz FROM quizzes WHERE quiz_id = p_quiz_id;
        IF v_quiz.selection_category_id IS NOT NULL THEN
            SELECT COUNT(*) INTO v_count FROM questions
             WHERE quiz_id = p_quiz_id
               AND category_id = v_quiz.selection_category_id
               AND difficulty_code = v_quiz.selection_difficulty_code
               AND (p_exclude_question IS NULL OR question_id <> p_exclude_question);
            IF v_count < v_quiz.question_limit THEN
                RAISE_APPLICATION_ERROR(-20140, 'Недостаточно вопросов для подбора: нужно '
                    || v_quiz.question_limit || ', доступно ' || v_count
                    || '. Добавьте вопросы или измените подбор в черновике.');
            END IF;
        END IF;
    END;

    PROCEDURE create_topic (
        p_actor_id IN NUMBER,
        p_title IN VARCHAR2,
        p_description IN VARCHAR2,
        p_topic_id OUT NUMBER
    ) IS
    BEGIN
        require_editor(p_actor_id);
        INSERT INTO topics (title, description, created_by)
        VALUES (TRIM(p_title), TRIM(p_description), p_actor_id)
        RETURNING topic_id INTO p_topic_id;
    EXCEPTION
        WHEN DUP_VAL_ON_INDEX THEN
            RAISE_APPLICATION_ERROR(-20103, 'Тематика с таким названием уже существует.');
    END;

    PROCEDURE create_category (
        p_actor_id IN NUMBER,
        p_topic_id IN NUMBER,
        p_title IN VARCHAR2,
        p_category_id OUT NUMBER
    ) IS
    BEGIN
        require_editor(p_actor_id);
        INSERT INTO categories (topic_id, title)
        VALUES (p_topic_id, TRIM(p_title))
        RETURNING category_id INTO p_category_id;
    EXCEPTION
        WHEN DUP_VAL_ON_INDEX THEN
            RAISE_APPLICATION_ERROR(-20104, 'Такая категория уже есть в выбранной тематике.');
    END;

    PROCEDURE create_quiz (
        p_actor_id IN NUMBER,
        p_topic_id IN NUMBER,
        p_title IN VARCHAR2,
        p_description IN VARCHAR2,
        p_timer_mode IN VARCHAR2,
        p_duration_minutes IN NUMBER,
        p_attempt_limit IN NUMBER,
        p_show_feedback IN NUMBER,
        p_access_mode IN VARCHAR2,
        p_quiz_id OUT NUMBER
    ) IS
        v_timer_mode VARCHAR2(15) := UPPER(TRIM(p_timer_mode));
        v_attempt_limit NUMBER := p_attempt_limit;
    BEGIN
        require_editor(p_actor_id);
        IF v_timer_mode NOT IN ('QUIZ', 'QUESTION') THEN
            RAISE_APPLICATION_ERROR(-20124, 'Режим времени должен быть QUIZ или QUESTION.');
        END IF;
        IF v_attempt_limit IS NOT NULL AND (v_attempt_limit < 1 OR v_attempt_limit > 1000 OR v_attempt_limit <> TRUNC(v_attempt_limit)) THEN
            RAISE_APPLICATION_ERROR(-20129, 'Лимит попыток должен быть целым числом от 1 до 1000 или NULL.');
        END IF;

        INSERT INTO quizzes (
            topic_id, author_id, title, description, timer_mode, duration_minutes,
            attempt_limit, show_feedback, access_mode
        ) VALUES (
            p_topic_id, p_actor_id, TRIM(p_title), TRIM(p_description),
            v_timer_mode, p_duration_minutes, v_attempt_limit, p_show_feedback, UPPER(p_access_mode)
        )
        RETURNING quiz_id INTO p_quiz_id;
    EXCEPTION
        WHEN DUP_VAL_ON_INDEX THEN
            RAISE_APPLICATION_ERROR(-20105, 'Тест с таким названием уже есть в выбранной тематике.');
    END;

    PROCEDURE add_question (
        p_actor_id IN NUMBER,
        p_quiz_id IN NUMBER,
        p_category_id IN NUMBER,
        p_type_code IN VARCHAR2,
        p_difficulty_code IN VARCHAR2,
        p_question_text IN VARCHAR2,
        p_expected_answer IN VARCHAR2,
        p_explanation IN VARCHAR2,
        p_points IN NUMBER,
        p_question_id OUT NUMBER
    ) IS
        v_seq NUMBER;
        v_count NUMBER;
    BEGIN
        require_quiz_owner(p_actor_id, p_quiz_id);
        SELECT COUNT(*)
          INTO v_count
          FROM quizzes q
          JOIN categories c ON c.topic_id = q.topic_id
         WHERE q.quiz_id = p_quiz_id
           AND c.category_id = p_category_id;
        IF v_count = 0 THEN
            RAISE_APPLICATION_ERROR(-20106, 'Категория должна относиться к тематике теста.');
        END IF;

        SELECT NVL(MAX(seq_no), 0) + 1 INTO v_seq FROM questions WHERE quiz_id = p_quiz_id;
        INSERT INTO questions (
            quiz_id, category_id, type_code, difficulty_code, seq_no,
            question_text, expected_answer, explanation, points
        ) VALUES (
            p_quiz_id, p_category_id, UPPER(p_type_code), UPPER(p_difficulty_code),
            v_seq, TRIM(p_question_text), TRIM(p_expected_answer), TRIM(p_explanation), p_points
        )
        RETURNING question_id INTO p_question_id;
    END;

    PROCEDURE update_question (
        p_actor_id IN NUMBER,
        p_question_id IN NUMBER,
        p_category_id IN NUMBER,
        p_type_code IN VARCHAR2,
        p_difficulty_code IN VARCHAR2,
        p_question_text IN VARCHAR2,
        p_expected_answer IN VARCHAR2,
        p_explanation IN VARCHAR2,
        p_points IN NUMBER
    ) IS
        v_quiz_id NUMBER;
        v_count NUMBER;
    BEGIN
        SELECT quiz_id
          INTO v_quiz_id
          FROM questions
         WHERE question_id = p_question_id;
        require_quiz_owner(p_actor_id, v_quiz_id);

        SELECT COUNT(*)
          INTO v_count
          FROM quizzes q
          JOIN categories c ON c.topic_id = q.topic_id
         WHERE q.quiz_id = v_quiz_id
           AND c.category_id = p_category_id;
        IF v_count = 0 THEN
            RAISE_APPLICATION_ERROR(-20106, 'Категория должна относиться к тематике теста.');
        END IF;

        UPDATE questions
           SET category_id = p_category_id,
               type_code = UPPER(p_type_code),
               difficulty_code = UPPER(p_difficulty_code),
               question_text = TRIM(p_question_text),
               expected_answer = TRIM(p_expected_answer),
               explanation = TRIM(p_explanation),
               points = p_points
         WHERE question_id = p_question_id;

        DELETE FROM question_options WHERE question_id = p_question_id;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20123, 'Вопрос не найден.');
    END;

    PROCEDURE add_option (
        p_actor_id IN NUMBER,
        p_question_id IN NUMBER,
        p_option_text IN VARCHAR2,
        p_is_correct IN NUMBER,
        p_option_id OUT NUMBER
    ) IS
        v_quiz_id NUMBER;
        v_type_mode question_types.answer_mode%TYPE;
        v_seq NUMBER;
    BEGIN
        SELECT q.quiz_id, qt.answer_mode
          INTO v_quiz_id, v_type_mode
          FROM questions q
          JOIN question_types qt ON qt.type_code = q.type_code
         WHERE q.question_id = p_question_id;
        require_quiz_owner(p_actor_id, v_quiz_id);
        IF v_type_mode <> 'OPTIONS' THEN
            RAISE_APPLICATION_ERROR(-20107, 'Для вопроса с вводом текста варианты ответа не добавляются.');
        END IF;

        SELECT NVL(MAX(seq_no), 0) + 1
          INTO v_seq
          FROM question_options
         WHERE question_id = p_question_id;

        INSERT INTO question_options (question_id, seq_no, option_text, is_correct)
        VALUES (p_question_id, v_seq, TRIM(p_option_text), p_is_correct)
        RETURNING option_id INTO p_option_id;
    END;

    PROCEDURE publish_quiz (
        p_actor_id IN NUMBER,
        p_quiz_id IN NUMBER
    ) IS
        v_question_count NUMBER;
        v_invalid_count NUMBER;
    BEGIN
        require_quiz_owner(p_actor_id, p_quiz_id);
        SELECT COUNT(*) INTO v_question_count FROM questions WHERE quiz_id = p_quiz_id;
        require_selection_pool(p_quiz_id);
        IF v_question_count = 0 THEN
            RAISE_APPLICATION_ERROR(-20108, 'В тест необходимо добавить хотя бы один вопрос.');
        END IF;

        SELECT COUNT(*)
          INTO v_invalid_count
          FROM questions q
          JOIN question_types qt ON qt.type_code = q.type_code
         WHERE q.quiz_id = p_quiz_id
           AND (
                (qt.answer_mode = 'TEXT' AND q.expected_answer IS NULL)
                OR (
                    qt.answer_mode = 'OPTIONS'
                    AND (
                        (SELECT COUNT(*) FROM question_options qo WHERE qo.question_id = q.question_id) < 2
                        OR (SELECT COUNT(*) FROM question_options qo WHERE qo.question_id = q.question_id AND qo.is_correct = 1) = 0
                        OR (
                            q.type_code IN ('SINGLE_CHOICE', 'BOOLEAN')
                            AND (SELECT COUNT(*) FROM question_options qo WHERE qo.question_id = q.question_id AND qo.is_correct = 1) <> 1
                        )
                    )
                )
           );
        IF v_invalid_count > 0 THEN
            RAISE_APPLICATION_ERROR(-20109, 'Публикация невозможна: заполните варианты и правильные ответы у всех вопросов.');
        END IF;

        UPDATE quizzes SET status = 'PUBLISHED' WHERE quiz_id = p_quiz_id;
    END;

    PROCEDURE set_quiz_feedback (
        p_actor_id IN NUMBER,
        p_quiz_id IN NUMBER,
        p_show_feedback IN NUMBER
    ) IS
    BEGIN
        require_quiz_owner(p_actor_id, p_quiz_id);
        IF p_show_feedback NOT IN (0, 1) THEN
            RAISE_APPLICATION_ERROR(-20127, 'Параметр show_feedback должен быть 0 или 1.');
        END IF;
        UPDATE quizzes
           SET show_feedback = p_show_feedback
         WHERE quiz_id = p_quiz_id
           AND status = 'DRAFT';
        IF SQL%ROWCOUNT = 0 THEN
            RAISE_APPLICATION_ERROR(-20128, 'Настройка доступна только для черновика теста.');
        END IF;
    END;

    PROCEDURE set_quiz_attempt_limit (
        p_actor_id IN NUMBER,
        p_quiz_id IN NUMBER,
        p_attempt_limit IN NUMBER
    ) IS
    BEGIN
        require_quiz_owner(p_actor_id, p_quiz_id);
        IF p_attempt_limit IS NOT NULL AND (p_attempt_limit < 1 OR p_attempt_limit > 1000 OR p_attempt_limit <> TRUNC(p_attempt_limit)) THEN
            RAISE_APPLICATION_ERROR(-20130, 'Лимит попыток должен быть целым числом от 1 до 1000 или NULL.');
        END IF;

        UPDATE quizzes
           SET attempt_limit = p_attempt_limit
         WHERE quiz_id = p_quiz_id
           AND status = 'DRAFT';
        IF SQL%ROWCOUNT = 0 THEN
            RAISE_APPLICATION_ERROR(-20131, 'Лимит попыток можно менять только у черновика.');
        END IF;
    END;

    PROCEDURE set_quiz_selection (
        p_actor_id IN NUMBER,
        p_quiz_id IN NUMBER,
        p_question_limit IN NUMBER,
        p_category_id IN NUMBER,
        p_difficulty_code IN VARCHAR2
    ) IS
        v_count NUMBER;
    BEGIN
        require_quiz_owner(p_actor_id, p_quiz_id);
        IF p_question_limit IS NULL AND p_category_id IS NULL AND p_difficulty_code IS NULL THEN
            UPDATE quizzes SET question_limit = NULL, selection_category_id = NULL,
                selection_difficulty_code = NULL WHERE quiz_id = p_quiz_id;
            RETURN;
        END IF;
        IF p_question_limit IS NULL OR p_question_limit < 1 OR p_question_limit > 1000
           OR p_question_limit <> TRUNC(p_question_limit)
           OR p_category_id IS NULL OR p_difficulty_code IS NULL THEN
            RAISE_APPLICATION_ERROR(-20138, 'Для подбора укажите категорию, сложность и целое количество от 1 до 1000.');
        END IF;
        SELECT COUNT(*) INTO v_count FROM categories c JOIN quizzes q ON q.topic_id = c.topic_id
         WHERE q.quiz_id = p_quiz_id AND c.category_id = p_category_id;
        IF v_count = 0 THEN
            RAISE_APPLICATION_ERROR(-20139, 'Категория подбора должна принадлежать тематике теста.');
        END IF;
        SELECT COUNT(*) INTO v_count FROM difficulty_levels WHERE difficulty_code = p_difficulty_code;
        IF v_count = 0 THEN
            RAISE_APPLICATION_ERROR(-20138, 'Выберите существующий уровень сложности.');
        END IF;
        UPDATE quizzes SET question_limit = p_question_limit, selection_category_id = p_category_id,
            selection_difficulty_code = p_difficulty_code WHERE quiz_id = p_quiz_id;
    END;

    PROCEDURE grant_access (
        p_actor_id IN NUMBER,
        p_quiz_id IN NUMBER,
        p_user_id IN NUMBER
    ) IS
        v_role VARCHAR2(20);
        v_author_id NUMBER;
    BEGIN
        v_role := actor_role(p_actor_id);
        SELECT author_id INTO v_author_id FROM quizzes WHERE quiz_id = p_quiz_id;
        IF v_role <> 'ADMIN' AND v_author_id <> p_actor_id THEN
            RAISE_APPLICATION_ERROR(-20110, 'Выдавать доступ может только автор теста или администратор.');
        END IF;
        MERGE INTO quiz_access qa
        USING (SELECT p_quiz_id quiz_id, p_user_id user_id FROM dual) src
           ON (qa.quiz_id = src.quiz_id AND qa.user_id = src.user_id)
        WHEN NOT MATCHED THEN INSERT (quiz_id, user_id) VALUES (src.quiz_id, src.user_id);
    END;

    PROCEDURE delete_category (
        p_admin_id IN NUMBER,
        p_category_id IN NUMBER
    ) IS
        v_question_count NUMBER;
    BEGIN
        require_admin(p_admin_id);
        SELECT COUNT(*) INTO v_question_count FROM questions WHERE category_id = p_category_id;
        IF v_question_count > 0 THEN
            RAISE_APPLICATION_ERROR(-20114, 'Категория используется в вопросах. Сначала удалите вопросы черновиков.');
        END IF;
        SELECT COUNT(*) INTO v_question_count FROM quizzes WHERE selection_category_id = p_category_id;
        IF v_question_count > 0 THEN
            RAISE_APPLICATION_ERROR(-20141, 'Категория используется в подборе теста. Сначала измените настройки подбора.');
        END IF;
        DELETE FROM categories WHERE category_id = p_category_id;
        IF SQL%ROWCOUNT = 0 THEN
            RAISE_APPLICATION_ERROR(-20115, 'Категория не найдена.');
        END IF;
    END;

    PROCEDURE delete_topic (
        p_admin_id IN NUMBER,
        p_topic_id IN NUMBER
    ) IS
        v_category_count NUMBER;
        v_quiz_count NUMBER;
    BEGIN
        require_admin(p_admin_id);
        SELECT COUNT(*) INTO v_category_count FROM categories WHERE topic_id = p_topic_id;
        SELECT COUNT(*) INTO v_quiz_count FROM quizzes WHERE topic_id = p_topic_id;
        IF v_category_count > 0 OR v_quiz_count > 0 THEN
            RAISE_APPLICATION_ERROR(-20116, 'Тематика используется. Сначала удалите ее категории и черновики тестов.');
        END IF;
        DELETE FROM topics WHERE topic_id = p_topic_id;
        IF SQL%ROWCOUNT = 0 THEN
            RAISE_APPLICATION_ERROR(-20117, 'Тематика не найдена.');
        END IF;
    END;

    PROCEDURE delete_question (
        p_admin_id IN NUMBER,
        p_question_id IN NUMBER
    ) IS
        v_quiz_id NUMBER;
        v_in_progress NUMBER;
        v_status quizzes.status%TYPE;
    BEGIN
        SELECT quiz_id
          INTO v_quiz_id
          FROM questions
         WHERE question_id = p_question_id;
        require_quiz_manager(p_admin_id, v_quiz_id);
        SELECT status INTO v_status FROM quizzes WHERE quiz_id = v_quiz_id;
        IF v_status = 'PUBLISHED' THEN
            require_selection_pool(v_quiz_id, p_question_id);
        END IF;

        SELECT COUNT(*)
          INTO v_in_progress
          FROM attempts
         WHERE quiz_id = v_quiz_id
           AND status = 'IN_PROGRESS';
        IF v_in_progress > 0 THEN
            RAISE_APPLICATION_ERROR(-20126, 'Нельзя удалить вопрос, пока есть активные попытки по этому тесту.');
        END IF;

        DELETE FROM attempt_questions
         WHERE question_id = p_question_id;

        DELETE FROM questions
         WHERE question_id = p_question_id;
        IF SQL%ROWCOUNT = 0 THEN
            RAISE_APPLICATION_ERROR(-20118, 'Вопрос не найден.');
        END IF;

        UPDATE questions
           SET seq_no = seq_no + 100000
         WHERE quiz_id = v_quiz_id;

        MERGE INTO questions q
        USING (
            SELECT ROWID rid, ROW_NUMBER() OVER (ORDER BY seq_no) AS new_seq
              FROM questions
             WHERE quiz_id = v_quiz_id
        ) src
           ON (q.ROWID = src.rid)
        WHEN MATCHED THEN
            UPDATE SET q.seq_no = src.new_seq;

        UPDATE attempt_questions
           SET display_order = display_order + 100000
         WHERE attempt_id IN (
            SELECT attempt_id
              FROM attempts
             WHERE quiz_id = v_quiz_id
         );

        MERGE INTO attempt_questions aq
        USING (
            SELECT ROWID rid,
                   ROW_NUMBER() OVER (PARTITION BY attempt_id ORDER BY display_order) AS new_order
              FROM attempt_questions
             WHERE attempt_id IN (
                SELECT attempt_id
                  FROM attempts
                 WHERE quiz_id = v_quiz_id
             )
        ) src
           ON (aq.ROWID = src.rid)
        WHEN MATCHED THEN
            UPDATE SET aq.display_order = src.new_order;

        UPDATE attempts a
           SET awarded_points = (
                   SELECT NVL(SUM(ua.awarded_points), 0)
                     FROM attempt_questions aq
                     LEFT JOIN user_answers ua
                       ON ua.attempt_id = aq.attempt_id
                      AND ua.question_id = aq.question_id
                    WHERE aq.attempt_id = a.attempt_id
               ),
               max_points = (
                   SELECT NVL(SUM(q.points), 0)
                     FROM attempt_questions aq
                     JOIN questions q ON q.question_id = aq.question_id
                    WHERE aq.attempt_id = a.attempt_id
               )
         WHERE a.quiz_id = v_quiz_id;

        UPDATE attempts a
           SET score_percent = fn_attempt_percent(a.attempt_id)
         WHERE a.quiz_id = v_quiz_id;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20118, 'Вопрос не найден.');
    END;

    PROCEDURE delete_quiz (
        p_admin_id IN NUMBER,
        p_quiz_id IN NUMBER
    ) IS
    BEGIN
        require_quiz_manager(p_admin_id, p_quiz_id);

        DELETE FROM attempts
         WHERE quiz_id = p_quiz_id;

        DELETE FROM quizzes
         WHERE quiz_id = p_quiz_id;
        IF SQL%ROWCOUNT = 0 THEN
            RAISE_APPLICATION_ERROR(-20119, 'Тест не найден.');
        END IF;
    END;

    PROCEDURE archive_quiz (
        p_admin_id IN NUMBER,
        p_quiz_id IN NUMBER
    ) IS
    BEGIN
        require_quiz_manager(p_admin_id, p_quiz_id);
        UPDATE quizzes
           SET status = 'DRAFT'
         WHERE quiz_id = p_quiz_id
           AND status IN ('PUBLISHED', 'ARCHIVED');
        IF SQL%ROWCOUNT = 0 THEN
            RAISE_APPLICATION_ERROR(-20120, 'Скрыть можно только опубликованный или архивный тест.');
        END IF;
    END;

    PROCEDURE reset_user_quiz_attempts (
        p_admin_id IN NUMBER,
        p_user_id IN NUMBER,
        p_quiz_id IN NUMBER
    ) IS
        v_deleted NUMBER;
        v_user_count NUMBER;
        v_quiz_count NUMBER;
    BEGIN
        require_admin(p_admin_id);
        SELECT COUNT(*) INTO v_user_count FROM app_users WHERE user_id = p_user_id;
        SELECT COUNT(*) INTO v_quiz_count FROM quizzes WHERE quiz_id = p_quiz_id;
        IF v_user_count = 0 OR v_quiz_count = 0 THEN
            RAISE_APPLICATION_ERROR(-20121, 'Пользователь или тест не найден.');
        END IF;

        DELETE FROM attempts WHERE user_id = p_user_id AND quiz_id = p_quiz_id;
        v_deleted := SQL%ROWCOUNT;
        INSERT INTO audit_log (event_type, entity_name, entity_id, details)
        VALUES (
            'PROGRESS_RESET_QUIZ',
            'APP_USERS',
            p_user_id,
            'admin_id=' || p_admin_id || '; quiz_id=' || p_quiz_id || '; deleted_attempts=' || v_deleted
        );
    END;

    PROCEDURE reset_user_progress (
        p_admin_id IN NUMBER,
        p_user_id IN NUMBER
    ) IS
        v_deleted NUMBER;
        v_user_count NUMBER;
    BEGIN
        require_admin(p_admin_id);
        SELECT COUNT(*) INTO v_user_count FROM app_users WHERE user_id = p_user_id;
        IF v_user_count = 0 THEN
            RAISE_APPLICATION_ERROR(-20122, 'Пользователь не найден.');
        END IF;

        DELETE FROM attempts WHERE user_id = p_user_id;
        v_deleted := SQL%ROWCOUNT;
        INSERT INTO audit_log (event_type, entity_name, entity_id, details)
        VALUES (
            'PROGRESS_RESET_ALL',
            'APP_USERS',
            p_user_id,
            'admin_id=' || p_admin_id || '; deleted_attempts=' || v_deleted
        );
    END;

    PROCEDURE create_author (
        p_admin_id IN NUMBER,
        p_login IN VARCHAR2,
        p_password IN VARCHAR2,
        p_full_name IN VARCHAR2,
        p_user_id OUT NUMBER
    ) IS
    BEGIN
        require_admin(p_admin_id);

        pr_register_user(p_login, p_password, p_full_name, p_user_id);
        UPDATE app_users
           SET role_code = 'AUTHOR'
         WHERE user_id = p_user_id;
    END;

    PROCEDURE set_user_role (
        p_admin_id IN NUMBER,
        p_user_id IN NUMBER,
        p_role_code IN VARCHAR2
    ) IS
    BEGIN
        require_admin(p_admin_id);
        IF p_admin_id = p_user_id AND UPPER(p_role_code) <> 'ADMIN' THEN
            RAISE_APPLICATION_ERROR(-20113, 'Нельзя снять роль ADMIN у текущей учетной записи.');
        END IF;
        UPDATE app_users SET role_code = UPPER(p_role_code) WHERE user_id = p_user_id;
        IF SQL%ROWCOUNT = 0 THEN
            RAISE_APPLICATION_ERROR(-20112, 'Пользователь не найден.');
        END IF;
    END;

    PROCEDURE set_user_password (
        p_admin_id IN NUMBER,
        p_user_id IN NUMBER,
        p_new_password IN VARCHAR2
    ) IS
        v_login app_users.login%TYPE;
    BEGIN
        require_admin(p_admin_id);
        IF p_new_password IS NULL OR LENGTH(p_new_password) < 6 THEN
            RAISE_APPLICATION_ERROR(-20132, 'Password must contain at least 6 characters.');
        END IF;

        SELECT login
          INTO v_login
          FROM app_users
         WHERE user_id = p_user_id;

        UPDATE app_users
           SET password_hash = fn_hash_password(v_login, p_new_password),
               updated_at = SYSTIMESTAMP
         WHERE user_id = p_user_id;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20112, 'User not found.');
    END;

    PROCEDURE set_user_active (
        p_admin_id IN NUMBER,
        p_user_id IN NUMBER,
        p_is_active IN NUMBER
    ) IS
        v_role app_users.role_code%TYPE;
    BEGIN
        require_admin(p_admin_id);
        IF p_is_active NOT IN (0, 1) THEN
            RAISE_APPLICATION_ERROR(-20135, 'Active flag must be 0 or 1.');
        END IF;
        IF p_admin_id = p_user_id AND p_is_active = 0 THEN
            RAISE_APPLICATION_ERROR(-20136, 'Cannot deactivate current admin account.');
        END IF;

        SELECT role_code
          INTO v_role
          FROM app_users
         WHERE user_id = p_user_id;

        IF v_role = 'ADMIN' AND p_is_active = 0 THEN
            RAISE_APPLICATION_ERROR(-20137, 'Cannot deactivate ADMIN account.');
        END IF;

        IF p_is_active = 0 THEN
            pkg_testing.abandon_user_attempts(p_user_id);
        END IF;

        UPDATE app_users
           SET is_active = p_is_active,
               updated_at = SYSTIMESTAMP
         WHERE user_id = p_user_id;

        IF SQL%ROWCOUNT = 0 THEN
            RAISE_APPLICATION_ERROR(-20112, 'User not found.');
        END IF;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20112, 'User not found.');
    END;

    PROCEDURE delete_user (
        p_admin_id IN NUMBER,
        p_user_id IN NUMBER
    ) IS
        v_role app_users.role_code%TYPE;
    BEGIN
        require_admin(p_admin_id);
        IF p_admin_id = p_user_id THEN
            RAISE_APPLICATION_ERROR(-20133, 'Cannot delete current admin account.');
        END IF;

        SELECT role_code
          INTO v_role
          FROM app_users
         WHERE user_id = p_user_id;

        IF v_role = 'ADMIN' THEN
            RAISE_APPLICATION_ERROR(-20134, 'Cannot delete ADMIN account.');
        END IF;

        DELETE FROM attempts
         WHERE quiz_id IN (
            SELECT quiz_id
              FROM quizzes
             WHERE author_id = p_user_id
         );

        DELETE FROM attempts
         WHERE user_id = p_user_id;

        DELETE FROM quizzes
         WHERE author_id = p_user_id;

        UPDATE topics
           SET created_by = p_admin_id
         WHERE created_by = p_user_id;

        DELETE FROM app_users
         WHERE user_id = p_user_id;

        IF SQL%ROWCOUNT = 0 THEN
            RAISE_APPLICATION_ERROR(-20112, 'User not found.');
        END IF;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RAISE_APPLICATION_ERROR(-20112, 'User not found.');
    END;
END pkg_admin;
/
