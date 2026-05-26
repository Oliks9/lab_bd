CREATE OR REPLACE PROCEDURE pr_login (
    p_login IN VARCHAR2,
    p_password IN VARCHAR2,
    p_user_id OUT NUMBER,
    p_full_name OUT VARCHAR2,
    p_role_code OUT VARCHAR2
)
IS
BEGIN
    SELECT user_id, full_name, role_code
      INTO p_user_id, p_full_name, p_role_code
      FROM app_users
     WHERE login = LOWER(TRIM(p_login))
       AND password_hash = fn_hash_password(p_login, p_password)
       AND is_active = 1;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(-20014, 'Неверный логин, пароль или учетная запись отключена.');
END;
/
