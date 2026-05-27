WHENEVER SQLERROR EXIT SQL.SQLCODE
SET SERVEROUTPUT ON

PROMPT === Adding per-user attempt limit for quizzes ===

DECLARE
    v_exists NUMBER;
BEGIN
    SELECT COUNT(*)
      INTO v_exists
      FROM user_tab_cols
     WHERE table_name = 'QUIZZES'
       AND column_name = 'ATTEMPT_LIMIT';

    IF v_exists = 0 THEN
        EXECUTE IMMEDIATE 'ALTER TABLE quizzes ADD (attempt_limit NUMBER)';
        DBMS_OUTPUT.PUT_LINE('Added column quizzes.attempt_limit.');
    ELSE
        DBMS_OUTPUT.PUT_LINE('Column quizzes.attempt_limit already exists.');
    END IF;

    SELECT COUNT(*)
      INTO v_exists
      FROM user_constraints
     WHERE table_name = 'QUIZZES'
       AND constraint_name = 'CK_QUIZZES_ATTEMPT_LIMIT';

    IF v_exists = 0 THEN
        EXECUTE IMMEDIATE q'[ALTER TABLE quizzes ADD CONSTRAINT ck_quizzes_attempt_limit CHECK (attempt_limit IS NULL OR attempt_limit > 0)]';
        DBMS_OUTPUT.PUT_LINE('Added constraint ck_quizzes_attempt_limit.');
    ELSE
        DBMS_OUTPUT.PUT_LINE('Constraint ck_quizzes_attempt_limit already exists.');
    END IF;
END;
/

