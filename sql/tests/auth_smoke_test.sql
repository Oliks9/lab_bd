SET SERVEROUTPUT ON
DECLARE
    v_user_id NUMBER;
    v_login_user_id NUMBER;
    v_admin_id NUMBER;
    v_author_id NUMBER;
    v_name VARCHAR2(200);
    v_role VARCHAR2(20);
BEGIN
    SAVEPOINT before_auth_smoke_test;

    pr_register_user('smoke_user', 'Smoke123!', 'Smoke User', v_user_id);
    pr_login('smoke_user', 'Smoke123!', v_login_user_id, v_name, v_role);

    IF v_login_user_id <> v_user_id OR v_role <> 'USER' THEN
        RAISE_APPLICATION_ERROR(-20996, 'Registration/login smoke test returned unexpected user data.');
    END IF;

    pr_login('admin', 'Admin123!', v_admin_id, v_name, v_role);
    pkg_admin.create_author(v_admin_id, 'smoke_author', 'Author123!', 'Smoke Author', v_author_id);
    pr_login('smoke_author', 'Author123!', v_login_user_id, v_name, v_role);
    IF v_login_user_id <> v_author_id OR v_role <> 'AUTHOR' THEN
        RAISE_APPLICATION_ERROR(-20994, 'Admin-created author has unexpected role.');
    END IF;

    DBMS_OUTPUT.PUT_LINE('Registration/login smoke test successful. User and AUTHOR creation verified.');
    ROLLBACK TO before_auth_smoke_test;
END;
/
