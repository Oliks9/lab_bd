CREATE OR REPLACE FUNCTION fn_quiz_pool_count (
    p_quiz_id IN NUMBER,
    p_category_id IN NUMBER,
    p_difficulty_code IN VARCHAR2
) RETURN NUMBER IS
    v_count NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_count FROM questions
     WHERE quiz_id = p_quiz_id
       AND (p_category_id IS NULL OR category_id = p_category_id)
       AND (p_difficulty_code IS NULL OR difficulty_code = p_difficulty_code);
    RETURN v_count;
END;
/
