SELECT object_type, object_name, status
  FROM user_objects
 WHERE object_name IN (
       'FN_HASH_PASSWORD', 'FN_CAN_ACCESS_QUIZ', 'FN_ATTEMPT_PERCENT',
       'PR_REGISTER_USER', 'PR_LOGIN', 'PKG_ADMIN', 'PKG_TESTING', 'PKG_REPORTS', 'FN_QUIZ_POOL_COUNT',
       'TRG_APP_USERS_BIU', 'TRG_QUIZZES_BIU', 'TRG_ATTEMPTS_BIU',
       'TRG_AUDIT_USERS', 'TRG_AUDIT_ATTEMPTS'
 )
   AND status <> 'VALID'
 ORDER BY object_type, object_name;

SELECT name, type, line, position, text
  FROM user_errors
 ORDER BY name, sequence;

DECLARE
    v_invalid_count NUMBER;

    PROCEDURE require_objects(p_type VARCHAR2, p_names SYS.ODCIVARCHAR2LIST) IS
        v_count NUMBER;
    BEGIN
        FOR i IN 1..p_names.COUNT LOOP
            SELECT COUNT(*) INTO v_count FROM user_objects
             WHERE object_name = p_names(i) AND object_type = p_type;
            IF v_count = 0 THEN
                RAISE_APPLICATION_ERROR(-20998, 'Missing required object: ' || p_type || ' ' || p_names(i));
            END IF;
        END LOOP;
    END;
BEGIN
    require_objects('TABLE', SYS.ODCIVARCHAR2LIST(
        'ROLES', 'APP_USERS', 'QUESTION_TYPES', 'DIFFICULTY_LEVELS', 'TOPICS',
        'CATEGORIES', 'QUIZZES', 'QUIZ_ACCESS', 'QUESTIONS', 'QUESTION_OPTIONS',
        'ATTEMPTS', 'ATTEMPT_QUESTIONS', 'USER_ANSWERS', 'ANSWER_CHOICES', 'AUDIT_LOG'));
    require_objects('FUNCTION', SYS.ODCIVARCHAR2LIST(
        'FN_HASH_PASSWORD', 'FN_CAN_ACCESS_QUIZ', 'FN_ATTEMPT_PERCENT', 'FN_QUIZ_POOL_COUNT'));
    require_objects('PROCEDURE', SYS.ODCIVARCHAR2LIST('PR_REGISTER_USER', 'PR_LOGIN'));
    require_objects('PACKAGE', SYS.ODCIVARCHAR2LIST('PKG_ADMIN', 'PKG_TESTING', 'PKG_REPORTS'));
    require_objects('PACKAGE BODY', SYS.ODCIVARCHAR2LIST('PKG_ADMIN', 'PKG_TESTING', 'PKG_REPORTS'));
    require_objects('TRIGGER', SYS.ODCIVARCHAR2LIST(
        'TRG_APP_USERS_BIU', 'TRG_QUIZZES_BIU', 'TRG_ATTEMPTS_BIU', 'TRG_AUDIT_USERS', 'TRG_AUDIT_ATTEMPTS'));
    SELECT COUNT(*)
      INTO v_invalid_count
      FROM user_objects
     WHERE status <> 'VALID';
    IF v_invalid_count > 0 THEN
        RAISE_APPLICATION_ERROR(-20999, 'Обнаружены невалидные Oracle-объекты: ' || v_invalid_count);
    END IF;
    DBMS_OUTPUT.PUT_LINE('All Oracle objects are VALID.');
END;
/
