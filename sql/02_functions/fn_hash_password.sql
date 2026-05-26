CREATE OR REPLACE FUNCTION fn_hash_password (
    p_login IN VARCHAR2,
    p_password IN VARCHAR2
) RETURN VARCHAR2
DETERMINISTIC
IS
    v_hash VARCHAR2(64);
BEGIN
    SELECT RAWTOHEX(STANDARD_HASH(LOWER(TRIM(p_login)) || ':' || p_password, 'SHA256'))
      INTO v_hash
      FROM dual;

    RETURN v_hash;
END;
/
