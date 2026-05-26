CREATE OR REPLACE TRIGGER trg_app_users_biu
BEFORE INSERT OR UPDATE ON app_users
FOR EACH ROW
BEGIN
    :NEW.login := LOWER(TRIM(:NEW.login));
    :NEW.full_name := TRIM(:NEW.full_name);

    IF INSERTING THEN
        :NEW.created_at := NVL(:NEW.created_at, SYSTIMESTAMP);
    END IF;
    :NEW.updated_at := SYSTIMESTAMP;
END;
/
