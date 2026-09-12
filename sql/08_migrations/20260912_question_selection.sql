WHENEVER SQLERROR EXIT SQL.SQLCODE
SET SERVEROUTPUT ON

DECLARE
    v_count NUMBER;
    PROCEDURE add_constraint(p_name VARCHAR2, p_definition VARCHAR2) IS
    BEGIN
        SELECT COUNT(*) INTO v_count FROM user_constraints WHERE constraint_name = p_name;
        IF v_count = 0 THEN
            EXECUTE IMMEDIATE 'ALTER TABLE quizzes ADD CONSTRAINT ' || p_name || ' ' || p_definition;
        END IF;
    END;
BEGIN
    SELECT COUNT(*) INTO v_count FROM user_tab_cols
     WHERE table_name = 'QUIZZES' AND column_name = 'SELECTION_CATEGORY_ID';
    IF v_count = 0 THEN
        EXECUTE IMMEDIATE 'ALTER TABLE quizzes ADD selection_category_id NUMBER';
    END IF;
    SELECT COUNT(*) INTO v_count FROM user_tab_cols
     WHERE table_name = 'QUIZZES' AND column_name = 'SELECTION_DIFFICULTY_CODE';
    IF v_count = 0 THEN
        EXECUTE IMMEDIATE 'ALTER TABLE quizzes ADD selection_difficulty_code VARCHAR2(20)';
    END IF;
    add_constraint('FK_QUIZZES_SELECTION_CATEGORY', 'FOREIGN KEY (selection_category_id) REFERENCES categories(category_id)');
    add_constraint('FK_QUIZZES_SELECTION_LEVEL', 'FOREIGN KEY (selection_difficulty_code) REFERENCES difficulty_levels(difficulty_code)');
    add_constraint('CK_QUIZZES_SELECTION', 'CHECK (
        (selection_category_id IS NULL AND selection_difficulty_code IS NULL)
        OR (selection_category_id IS NOT NULL AND selection_difficulty_code IS NOT NULL
            AND question_limit IS NOT NULL AND question_limit BETWEEN 1 AND 1000
            AND question_limit = TRUNC(question_limit)))');
    DBMS_OUTPUT.PUT_LINE('Question selection schema is ready; existing quizzes and attempts are unchanged.');
END;
/
