CREATE OR REPLACE PROCEDURE pr_register_user (
    p_login IN VARCHAR2,
    p_password IN VARCHAR2,
    p_full_name IN VARCHAR2,
    p_user_id OUT NUMBER
)
IS
    v_login VARCHAR2(50) := LOWER(TRIM(p_login));
BEGIN
    IF NOT REGEXP_LIKE(v_login, '^[a-z0-9_.-]{3,50}$') THEN
        RAISE_APPLICATION_ERROR(-20010, 'Логин: 3-50 символов, латинские буквы, цифры, ., _ или -.');
    END IF;

    IF LENGTH(p_password) < 6 THEN
        RAISE_APPLICATION_ERROR(-20011, 'Пароль должен содержать не менее 6 символов.');
    END IF;

    IF TRIM(p_full_name) IS NULL THEN
        RAISE_APPLICATION_ERROR(-20012, 'Укажите имя пользователя.');
    END IF;

    INSERT INTO app_users (login, password_hash, full_name, role_code)
    VALUES (v_login, fn_hash_password(v_login, p_password), TRIM(p_full_name), 'USER')
    RETURNING user_id INTO p_user_id;
EXCEPTION
    WHEN DUP_VAL_ON_INDEX THEN
        RAISE_APPLICATION_ERROR(-20013, 'Пользователь с таким логином уже существует.');
END;
/
