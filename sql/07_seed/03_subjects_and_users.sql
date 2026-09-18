DECLARE
    v_admin_id NUMBER;
    v_author_id NUMBER;
    v_student_id NUMBER;
    v_topic_id NUMBER;
    v_category_id NUMBER;
    v_quiz_id NUMBER;
    v_question_id NUMBER;
    v_option_id NUMBER;
BEGIN
    SELECT user_id INTO v_admin_id FROM app_users WHERE login = 'admin';
    pkg_admin.create_author(v_admin_id, 'author', 'Author123!', 'Демонстрационный автор', v_author_id);
    pr_register_user('student', 'Student123!', 'Демонстрационный участник', v_student_id);

    pkg_admin.create_topic(v_author_id, 'Математика',
        'Арифметика, геометрия и порядок чисел.', v_topic_id);
    pkg_admin.create_category(v_author_id, v_topic_id, 'Основы математики', v_category_id);
    pkg_admin.create_quiz(v_author_id, v_topic_id, 'Математика: базовые знания',
        'Шесть заданий по арифметике и геометрии с пояснениями к ответам.',
        'QUIZ', 15, NULL, 1, 'PUBLIC', v_quiz_id);

    pkg_admin.add_question(v_author_id, v_quiz_id, v_category_id, 'SINGLE_CHOICE', 'EASY',
        'Чему равно произведение 7 и 8?', NULL,
        'По таблице умножения: 7 * 8 = 56.', 1, v_question_id);
    pkg_admin.add_option(v_author_id, v_question_id, '54', 0, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, '56', 1, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, '64', 0, v_option_id);

    pkg_admin.add_question(v_author_id, v_quiz_id, v_category_id, 'MULTIPLE_CHOICE', 'MEDIUM',
        'Выберите все чётные числа.', NULL,
        'Чётные числа делятся на 2 без остатка. В этом списке это 2 и 4.', 2, v_question_id);
    pkg_admin.add_option(v_author_id, v_question_id, '2', 1, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, '3', 0, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, '4', 1, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, '5', 0, v_option_id);

    pkg_admin.add_question(v_author_id, v_quiz_id, v_category_id, 'TEXT', 'EASY',
        'Как называется арифметическое действие, обозначаемое знаком +? Введите одно слово.',
        'сложение', 'Действие со знаком + называется сложением.', 1, v_question_id);

    pkg_admin.add_question(v_author_id, v_quiz_id, v_category_id, 'NUMBER', 'MEDIUM',
        'Длина прямоугольника 6 см, ширина 4 см. Чему равна площадь в квадратных сантиметрах? Введите только число.',
        '24', 'Площадь прямоугольника равна произведению длины и ширины: 6 * 4 = 24.', 1, v_question_id);

    pkg_admin.add_question(v_author_id, v_quiz_id, v_category_id, 'BOOLEAN', 'EASY',
        'Каждый квадрат является прямоугольником.', NULL,
        'У квадрата, как и у прямоугольника, все углы прямые. Квадрат является частным случаем прямоугольника.',
        1, v_question_id);
    pkg_admin.add_option(v_author_id, v_question_id, 'Верно', 1, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, 'Неверно', 0, v_option_id);

    pkg_admin.add_question(v_author_id, v_quiz_id, v_category_id, 'ORDERING', 'HARD',
        'Расположите числа по возрастанию: от наименьшего к наибольшему.', NULL,
        'Правильный порядок: -3, 0, 2, 7. Отрицательное число меньше нуля, а положительные числа больше нуля.',
        2, v_question_id);
    pkg_admin.add_option(v_author_id, v_question_id, '-3', 1, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, '0', 1, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, '2', 1, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, '7', 1, v_option_id);
    pkg_admin.publish_quiz(v_author_id, v_quiz_id);

    pkg_admin.create_topic(v_author_id, 'Русский язык',
        'Части речи, орфография, алфавит и члены предложения.', v_topic_id);
    pkg_admin.create_category(v_author_id, v_topic_id, 'Основы русского языка', v_category_id);
    pkg_admin.create_quiz(v_author_id, v_topic_id, 'Русский язык: базовые знания',
        'Шесть заданий по русскому языку с пояснениями к ответам.',
        'QUIZ', 10, NULL, 1, 'PUBLIC', v_quiz_id);

    pkg_admin.add_question(v_author_id, v_quiz_id, v_category_id, 'SINGLE_CHOICE', 'EASY',
        'Какая часть речи обозначает предмет и отвечает на вопросы «кто?» и «что?»?', NULL,
        'Имя существительное обозначает предмет и отвечает на вопросы «кто?» и «что?».', 1, v_question_id);
    pkg_admin.add_option(v_author_id, v_question_id, 'Имя прилагательное', 0, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, 'Глагол', 0, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, 'Имя существительное', 1, v_option_id);

    pkg_admin.add_question(v_author_id, v_quiz_id, v_category_id, 'MULTIPLE_CHOICE', 'MEDIUM',
        'Выберите все глаголы.', NULL,
        '«Читать» и «писать» обозначают действия и отвечают на вопрос «что делать?».', 2, v_question_id);
    pkg_admin.add_option(v_author_id, v_question_id, 'читать', 1, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, 'книга', 0, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, 'писать', 1, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, 'красивый', 0, v_option_id);

    pkg_admin.add_question(v_author_id, v_quiz_id, v_category_id, 'TEXT', 'EASY',
        'Как называется главный член предложения, который обозначает, о ком или о чём говорится в предложении? Введите одно слово.',
        'подлежащее', 'Подлежащее обозначает предмет речи и отвечает на вопросы «кто?» и «что?».', 1, v_question_id);

    pkg_admin.add_question(v_author_id, v_quiz_id, v_category_id, 'NUMBER', 'MEDIUM',
        'Сколько букв в слове «школа»? Введите только число.',
        '5', 'В слове «школа» пять букв: ш, к, о, л, а.', 1, v_question_id);

    pkg_admin.add_question(v_author_id, v_quiz_id, v_category_id, 'BOOLEAN', 'EASY',
        'В сочетаниях ЖИ и ШИ нужно писать букву Ы.', NULL,
        'Утверждение неверно: сочетания ЖИ и ШИ пишутся с буквой И.', 1, v_question_id);
    pkg_admin.add_option(v_author_id, v_question_id, 'Верно', 0, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, 'Неверно', 1, v_option_id);

    pkg_admin.add_question(v_author_id, v_quiz_id, v_category_id, 'ORDERING', 'HARD',
        'Расположите слова в алфавитном порядке.', NULL,
        'Первые буквы слов идут по алфавиту: А, Б, В, Г. Порядок: арбуз, берёза, вишня, груша.',
        2, v_question_id);
    pkg_admin.add_option(v_author_id, v_question_id, 'арбуз', 1, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, 'берёза', 1, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, 'вишня', 1, v_option_id);
    pkg_admin.add_option(v_author_id, v_question_id, 'груша', 1, v_option_id);
    pkg_admin.publish_quiz(v_author_id, v_quiz_id);
END;
/
