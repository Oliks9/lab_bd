WHENEVER SQLERROR EXIT SQL.SQLCODE
SET SERVEROUTPUT ON

PROMPT === Migrating ORDERING questions to option-based sequence mode ===

DECLARE
    v_created_options NUMBER := 0;
    v_normalized_options NUMBER := 0;
    v_cleared_expected NUMBER := 0;
    v_option_count NUMBER;
    v_piece VARCHAR2(1000);
BEGIN
    UPDATE question_types
       SET answer_mode = 'OPTIONS'
     WHERE type_code = 'ORDERING'
       AND answer_mode <> 'OPTIONS';
    DBMS_OUTPUT.PUT_LINE('question_types.ORDERING -> OPTIONS: ' || SQL%ROWCOUNT);

    FOR rec IN (
        SELECT q.question_id, q.expected_answer
          FROM questions q
         WHERE q.type_code = 'ORDERING'
    ) LOOP
        SELECT COUNT(*)
          INTO v_option_count
          FROM question_options
         WHERE question_id = rec.question_id;

        IF v_option_count = 0 AND rec.expected_answer IS NOT NULL THEN
            FOR idx IN 1 .. REGEXP_COUNT(rec.expected_answer, '[^;]+') LOOP
                v_piece := TRIM(REGEXP_SUBSTR(rec.expected_answer, '[^;]+', 1, idx));
                IF v_piece IS NOT NULL THEN
                    INSERT INTO question_options (question_id, seq_no, option_text, is_correct)
                    VALUES (rec.question_id, idx, v_piece, 1);
                    v_created_options := v_created_options + 1;
                END IF;
            END LOOP;
        END IF;

        UPDATE question_options
           SET is_correct = 1
         WHERE question_id = rec.question_id
           AND NVL(is_correct, 0) <> 1;
        v_normalized_options := v_normalized_options + SQL%ROWCOUNT;
    END LOOP;

    UPDATE questions
       SET expected_answer = NULL
     WHERE type_code = 'ORDERING'
       AND expected_answer IS NOT NULL;
    v_cleared_expected := SQL%ROWCOUNT;

    DBMS_OUTPUT.PUT_LINE('Created ordering options: ' || v_created_options);
    DBMS_OUTPUT.PUT_LINE('Normalized ordering option flags: ' || v_normalized_options);
    DBMS_OUTPUT.PUT_LINE('Cleared legacy expected_answer values: ' || v_cleared_expected);
END;
/
