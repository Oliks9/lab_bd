SELECT object_type, object_name, status
  FROM user_objects
 WHERE object_name IN (
       'FN_HASH_PASSWORD', 'FN_CAN_ACCESS_QUIZ', 'FN_ATTEMPT_PERCENT',
       'PR_REGISTER_USER', 'PR_LOGIN', 'PKG_ADMIN', 'PKG_TESTING',
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
BEGIN
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
