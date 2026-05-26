DECLARE
    v_admin_id NUMBER;
    v_topic_id NUMBER;
    v_category_id NUMBER;
    v_quiz_id NUMBER;
    v_question_id NUMBER;
    v_option_id NUMBER;
BEGIN
    INSERT INTO app_users (login, password_hash, full_name, role_code)
    VALUES ('admin', fn_hash_password('admin', 'Admin123!'), 'Администратор системы', 'ADMIN')
    RETURNING user_id INTO v_admin_id;

    pkg_admin.create_topic(
        v_admin_id, 'Программирование в базах данных',
        'SQL, PL/SQL, транзакции, триггеры и серверная бизнес-логика.', v_topic_id
    );
    pkg_admin.create_category(v_admin_id, v_topic_id, 'Oracle PL/SQL', v_category_id);
    pkg_admin.create_quiz(
        v_admin_id, v_topic_id, 'Oracle: основы серверной логики',
        'Демонстрационный тест с разными форматами ответа.', 20, 1, 'PUBLIC', v_quiz_id
    );

    pkg_admin.add_question(
        v_admin_id, v_quiz_id, v_category_id, 'SINGLE_CHOICE', 'EASY',
        'Какой объект Oracle объединяет процедуры и функции в единый программный модуль?',
        NULL, 'Package позволяет публиковать спецификацию и скрывать реализацию в теле.', 1, v_question_id
    );
    pkg_admin.add_option(v_admin_id, v_question_id, 'Представление (VIEW)', 0, v_option_id);
    pkg_admin.add_option(v_admin_id, v_question_id, 'Пакет (PACKAGE)', 1, v_option_id);
    pkg_admin.add_option(v_admin_id, v_question_id, 'Индекс (INDEX)', 0, v_option_id);

    pkg_admin.add_question(
        v_admin_id, v_quiz_id, v_category_id, 'MULTIPLE_CHOICE', 'MEDIUM',
        'Какие механизмы выполняются на стороне Oracle? Выберите два ответа.',
        NULL, 'Триггеры и хранимые процедуры исполняются сервером базы данных.', 2, v_question_id
    );
    pkg_admin.add_option(v_admin_id, v_question_id, 'Триггер', 1, v_option_id);
    pkg_admin.add_option(v_admin_id, v_question_id, 'Хранимая процедура', 1, v_option_id);
    pkg_admin.add_option(v_admin_id, v_question_id, 'Tkinter Frame', 0, v_option_id);
    pkg_admin.add_option(v_admin_id, v_question_id, 'CSS stylesheet', 0, v_option_id);

    pkg_admin.add_question(
        v_admin_id, v_quiz_id, v_category_id, 'TEXT', 'EASY',
        'Введите оператор фиксации транзакции в Oracle.',
        'COMMIT', 'COMMIT делает изменения транзакции постоянными.', 1, v_question_id
    );

    pkg_admin.add_question(
        v_admin_id, v_quiz_id, v_category_id, 'NUMBER', 'MEDIUM',
        'Сколько секций обычно содержит пакет PL/SQL: спецификация и тело?',
        '2', 'Пакет имеет спецификацию и, если нужна реализация, тело.', 1, v_question_id
    );

    pkg_admin.add_question(
        v_admin_id, v_quiz_id, v_category_id, 'BOOLEAN', 'EASY',
        'Триггер может автоматически сработать при INSERT в таблицу.',
        NULL, 'DML-триггер может реагировать на INSERT, UPDATE или DELETE.', 1, v_question_id
    );
    pkg_admin.add_option(v_admin_id, v_question_id, 'Верно', 1, v_option_id);
    pkg_admin.add_option(v_admin_id, v_question_id, 'Неверно', 0, v_option_id);

    pkg_admin.add_question(
        v_admin_id, v_quiz_id, v_category_id, 'ORDERING', 'HARD',
        'Введите логический порядок частей SELECT через точку с запятой: FROM, WHERE, SELECT.',
        'SELECT;FROM;WHERE', 'Сначала задается SELECT, затем источник FROM и условие WHERE.', 2, v_question_id
    );

    pkg_admin.publish_quiz(v_admin_id, v_quiz_id);
END;
/
