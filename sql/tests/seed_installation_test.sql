SET SERVEROUTPUT ON
DECLARE
    v_count NUMBER;
    v_user_id NUMBER;
    v_student_id NUMBER;
    v_full_name VARCHAR2(200);
    v_role VARCHAR2(20);
    v_attempt_id NUMBER;
    v_option_ids VARCHAR2(1000);
    v_score NUMBER;
    v_status VARCHAR2(20);
    v_logins SYS.ODCIVARCHAR2LIST := SYS.ODCIVARCHAR2LIST('admin', 'author', 'student');
    v_passwords SYS.ODCIVARCHAR2LIST := SYS.ODCIVARCHAR2LIST('Admin123!', 'Author123!', 'Student123!');
    v_roles SYS.ODCIVARCHAR2LIST := SYS.ODCIVARCHAR2LIST('ADMIN', 'AUTHOR', 'USER');

    PROCEDURE expect_count(p_actual NUMBER, p_expected NUMBER, p_message VARCHAR2) IS
    BEGIN
        IF p_actual IS NULL OR p_actual <> p_expected THEN
            RAISE_APPLICATION_ERROR(-20990, p_message || ': expected ' || p_expected || ', got ' || p_actual);
        END IF;
    END;
BEGIN
    SAVEPOINT before_seed_installation_test;
    SELECT COUNT(*) INTO v_count FROM app_users;
    expect_count(v_count, 3, 'Initial account count');
    SELECT COUNT(*) INTO v_count FROM attempts;
    expect_count(v_count, 0, 'Initial attempt count');
    SELECT COUNT(*) INTO v_count FROM quizzes;
    expect_count(v_count, 3, 'Initial quiz count');
    SELECT COUNT(*) INTO v_count FROM topics;
    expect_count(v_count, 3, 'Initial topic count');
    SELECT COUNT(*) INTO v_count FROM categories;
    expect_count(v_count, 3, 'Initial category count');
    SELECT COUNT(*) INTO v_count FROM questions;
    expect_count(v_count, 18, 'Initial question count');
    SELECT COUNT(*) INTO v_count FROM quizzes
     WHERE status = 'PUBLISHED' AND access_mode = 'PUBLIC' AND show_feedback = 1
       AND attempt_limit IS NULL AND question_limit IS NULL AND timer_mode = 'QUIZ';
    expect_count(v_count, 3, 'Initial quiz settings');

    FOR i IN 1..v_logins.COUNT LOOP
        pr_login(v_logins(i), v_passwords(i), v_user_id, v_full_name, v_role);
        IF v_role <> v_roles(i) OR v_full_name IS NULL THEN
            RAISE_APPLICATION_ERROR(-20990, 'Invalid role or display name for ' || v_logins(i));
        END IF;
        IF v_logins(i) = 'student' THEN
            v_student_id := v_user_id;
        END IF;
    END LOOP;

    SELECT COUNT(*) INTO v_count
      FROM quizzes q JOIN app_users u ON u.user_id = q.author_id
     WHERE u.login = 'author'
       AND q.title IN ('Математика: базовые знания', 'Русский язык: базовые знания');
    expect_count(v_count, 2, 'New quiz ownership and UTF-8 titles');

    FOR quiz IN (SELECT quiz_id, title FROM quizzes ORDER BY quiz_id) LOOP
        SELECT COUNT(*) INTO v_count FROM questions WHERE quiz_id = quiz.quiz_id;
        expect_count(v_count, 6, 'Questions per quiz');
        SELECT COUNT(DISTINCT type_code) INTO v_count FROM questions WHERE quiz_id = quiz.quiz_id;
        expect_count(v_count, 6, 'Question types per quiz');
        SELECT COUNT(*) INTO v_count FROM questions
         WHERE quiz_id = quiz.quiz_id AND explanation IS NOT NULL;
        expect_count(v_count, 6, 'Question explanations');
        SELECT SUM(points) INTO v_count FROM questions WHERE quiz_id = quiz.quiz_id;
        expect_count(v_count, 8, 'Maximum points');
        SELECT COUNT(*) INTO v_count
          FROM questions q JOIN categories c ON c.category_id = q.category_id
          JOIN quizzes z ON z.quiz_id = q.quiz_id
         WHERE q.quiz_id = quiz.quiz_id AND c.topic_id = z.topic_id;
        expect_count(v_count, 6, 'Category and quiz topic alignment');

        pkg_testing.start_attempt(v_student_id, quiz.quiz_id, v_attempt_id);
        FOR question IN (
            SELECT q.question_id, q.type_code, q.expected_answer
              FROM attempt_questions aq JOIN questions q ON q.question_id = aq.question_id
             WHERE aq.attempt_id = v_attempt_id ORDER BY aq.display_order
        ) LOOP
            v_option_ids := NULL;
            IF question.type_code NOT IN ('TEXT', 'NUMBER') THEN
                SELECT LISTAGG(TO_CHAR(option_id), ',') WITHIN GROUP (ORDER BY seq_no)
                  INTO v_option_ids FROM question_options
                 WHERE question_id = question.question_id
                   AND (is_correct = 1 OR question.type_code = 'ORDERING');
            END IF;
            pkg_testing.submit_answer(v_attempt_id, question.question_id, v_option_ids, question.expected_answer);
        END LOOP;
        SELECT score_percent, status INTO v_score, v_status FROM attempts WHERE attempt_id = v_attempt_id;
        expect_count(v_score, 100, 'Seed quiz score');
        IF v_status <> 'FINISHED' THEN
            RAISE_APPLICATION_ERROR(-20990, 'Seed quiz was not finished automatically');
        END IF;
        DBMS_OUTPUT.PUT_LINE('Seed quiz passed: ' || quiz.title || ', score=' || v_score);
    END LOOP;
    ROLLBACK TO before_seed_installation_test;
    DBMS_OUTPUT.PUT_LINE('Seed installation test successful: three accounts, three quizzes, eighteen questions; attempts rolled back.');
EXCEPTION WHEN OTHERS THEN
    ROLLBACK TO before_seed_installation_test;
    RAISE;
END;
/
