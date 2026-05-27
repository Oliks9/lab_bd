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
        SELECT COUNT(*)
          INTO v_count
          FROM quizzes
         WHERE quiz_id = p_quiz_id
           AND status = 'DRAFT'
           AND (author_id = p_actor_id OR v_role = 'ADMIN');
        IF v_count = 0 THEN
            RAISE_APPLICATION_ERROR(-20102, 'Изменять можно только доступный черновик теста.');
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
        p_duration_minutes IN NUMBER,
        p_show_feedback IN NUMBER,
        p_access_mode IN VARCHAR2,
        p_quiz_id OUT NUMBER
    ) IS
    BEGIN
        require_editor(p_actor_id);
        INSERT INTO quizzes (
            topic_id, author_id, title, description, duration_minutes,
            show_feedback, access_mode
        ) VALUES (
            p_topic_id, p_actor_id, TRIM(p_title), TRIM(p_description),
            p_duration_minutes, p_show_feedback, UPPER(p_access_mode)
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
    BEGIN
        require_admin(p_admin_id);
        DELETE FROM questions
         WHERE question_id = p_question_id
           AND quiz_id IN (SELECT quiz_id FROM quizzes WHERE status = 'DRAFT');
        IF SQL%ROWCOUNT = 0 THEN
            RAISE_APPLICATION_ERROR(-20118, 'Удалять можно только вопрос из черновика.');
        END IF;
    END;

    PROCEDURE delete_quiz (
        p_admin_id IN NUMBER,
        p_quiz_id IN NUMBER
    ) IS
    BEGIN
        require_admin(p_admin_id);
        DELETE FROM quizzes
         WHERE quiz_id = p_quiz_id
           AND status = 'DRAFT';
        IF SQL%ROWCOUNT = 0 THEN
            RAISE_APPLICATION_ERROR(-20119, 'Удалять можно только черновик. Опубликованный тест архивируйте.');
        END IF;
    END;

    PROCEDURE archive_quiz (
        p_admin_id IN NUMBER,
        p_quiz_id IN NUMBER
    ) IS
    BEGIN
        require_admin(p_admin_id);
        UPDATE quizzes
           SET status = 'ARCHIVED'
         WHERE quiz_id = p_quiz_id
           AND status = 'PUBLISHED';
        IF SQL%ROWCOUNT = 0 THEN
            RAISE_APPLICATION_ERROR(-20120, 'Архивировать можно только опубликованный тест.');
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
END pkg_admin;
/
