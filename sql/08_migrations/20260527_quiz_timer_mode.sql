WHENEVER SQLERROR EXIT SQL.SQLCODE
SET SERVEROUTPUT ON

PROMPT === Adding quiz timer mode support ===

DECLARE
    v_count NUMBER;
BEGIN
    SELECT COUNT(*)
      INTO v_count
      FROM user_tab_columns
     WHERE table_name = 'QUIZZES'
       AND column_name = 'TIMER_MODE';
    IF v_count = 0 THEN
        EXECUTE IMMEDIATE q'[ALTER TABLE quizzes ADD (timer_mode VARCHAR2(15) DEFAULT 'QUIZ' NOT NULL)]';
        DBMS_OUTPUT.PUT_LINE('Added column quizzes.timer_mode.');
    ELSE
        DBMS_OUTPUT.PUT_LINE('Column quizzes.timer_mode already exists.');
    END IF;

    SELECT COUNT(*)
      INTO v_count
      FROM user_constraints
     WHERE table_name = 'QUIZZES'
       AND constraint_name = 'CK_QUIZZES_TIMER_MODE';
    IF v_count = 0 THEN
        EXECUTE IMMEDIATE q'[ALTER TABLE quizzes ADD CONSTRAINT ck_quizzes_timer_mode CHECK (timer_mode IN ('QUIZ', 'QUESTION'))]';
        DBMS_OUTPUT.PUT_LINE('Added constraint ck_quizzes_timer_mode.');
    END IF;

    SELECT COUNT(*)
      INTO v_count
      FROM user_tab_columns
     WHERE table_name = 'ATTEMPTS'
       AND column_name = 'TIMER_MODE';
    IF v_count = 0 THEN
        EXECUTE IMMEDIATE q'[ALTER TABLE attempts ADD (timer_mode VARCHAR2(15) DEFAULT 'QUIZ' NOT NULL)]';
        DBMS_OUTPUT.PUT_LINE('Added column attempts.timer_mode.');
    END IF;

    SELECT COUNT(*)
      INTO v_count
      FROM user_constraints
     WHERE table_name = 'ATTEMPTS'
       AND constraint_name = 'CK_ATTEMPTS_TIMER_MODE';
    IF v_count = 0 THEN
        EXECUTE IMMEDIATE q'[ALTER TABLE attempts ADD CONSTRAINT ck_attempts_timer_mode CHECK (timer_mode IN ('QUIZ', 'QUESTION'))]';
        DBMS_OUTPUT.PUT_LINE('Added constraint ck_attempts_timer_mode.');
    END IF;

    SELECT COUNT(*)
      INTO v_count
      FROM user_tab_columns
     WHERE table_name = 'ATTEMPTS'
       AND column_name = 'QUESTION_DURATION_MINUTES';
    IF v_count = 0 THEN
        EXECUTE IMMEDIATE 'ALTER TABLE attempts ADD (question_duration_minutes NUMBER)';
        DBMS_OUTPUT.PUT_LINE('Added column attempts.question_duration_minutes.');
    END IF;

    SELECT COUNT(*)
      INTO v_count
      FROM user_constraints
     WHERE table_name = 'ATTEMPTS'
       AND constraint_name = 'CK_ATTEMPTS_QUESTION_DURATION';
    IF v_count = 0 THEN
        EXECUTE IMMEDIATE q'[ALTER TABLE attempts ADD CONSTRAINT ck_attempts_question_duration CHECK (question_duration_minutes IS NULL OR question_duration_minutes BETWEEN 1 AND 1440)]';
        DBMS_OUTPUT.PUT_LINE('Added constraint ck_attempts_question_duration.');
    END IF;

    SELECT COUNT(*)
      INTO v_count
      FROM user_tab_columns
     WHERE table_name = 'ATTEMPTS'
       AND column_name = 'ACTIVE_QUESTION_ORDER';
    IF v_count = 0 THEN
        EXECUTE IMMEDIATE 'ALTER TABLE attempts ADD (active_question_order NUMBER)';
        DBMS_OUTPUT.PUT_LINE('Added column attempts.active_question_order.');
    END IF;

    SELECT COUNT(*)
      INTO v_count
      FROM user_constraints
     WHERE table_name = 'ATTEMPTS'
       AND constraint_name = 'CK_ATTEMPTS_ACTIVE_ORDER';
    IF v_count = 0 THEN
        EXECUTE IMMEDIATE q'[ALTER TABLE attempts ADD CONSTRAINT ck_attempts_active_order CHECK (active_question_order IS NULL OR active_question_order > 0)]';
        DBMS_OUTPUT.PUT_LINE('Added constraint ck_attempts_active_order.');
    END IF;

    SELECT COUNT(*)
      INTO v_count
      FROM user_tab_columns
     WHERE table_name = 'ATTEMPTS'
       AND column_name = 'QUESTION_STARTED_AT';
    IF v_count = 0 THEN
        EXECUTE IMMEDIATE 'ALTER TABLE attempts ADD (question_started_at TIMESTAMP WITH TIME ZONE)';
        DBMS_OUTPUT.PUT_LINE('Added column attempts.question_started_at.');
    END IF;

    EXECUTE IMMEDIATE q'[
        UPDATE attempts a
           SET timer_mode = (
                SELECT NVL(q.timer_mode, 'QUIZ')
                  FROM quizzes q
                 WHERE q.quiz_id = a.quiz_id
           )
    ]';

    EXECUTE IMMEDIATE q'[
        UPDATE attempts a
           SET question_duration_minutes = (
                SELECT CASE
                           WHEN NVL(q.timer_mode, 'QUIZ') = 'QUESTION' THEN q.duration_minutes
                           ELSE NULL
                       END
                  FROM quizzes q
                 WHERE q.quiz_id = a.quiz_id
           )
    ]';

    EXECUTE IMMEDIATE q'[
        UPDATE attempts a
           SET active_question_order = CASE
                                           WHEN a.timer_mode = 'QUESTION' AND a.status = 'IN_PROGRESS' THEN 1
                                           ELSE NULL
                                       END,
               question_started_at = CASE
                                         WHEN a.timer_mode = 'QUESTION' AND a.status = 'IN_PROGRESS'
                                             THEN NVL(a.question_started_at, SYSTIMESTAMP)
                                         ELSE NULL
                                     END
    ]';

    DBMS_OUTPUT.PUT_LINE('Quiz timer mode migration completed.');
END;
/
