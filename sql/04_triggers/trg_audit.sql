CREATE OR REPLACE TRIGGER trg_audit_users
AFTER INSERT OR UPDATE OF role_code, is_active ON app_users
FOR EACH ROW
DECLARE
    v_event_type VARCHAR2(40);
BEGIN
    IF INSERTING THEN
        v_event_type := 'USER_REGISTERED';
    ELSE
        v_event_type := 'USER_CHANGED';
    END IF;
    INSERT INTO audit_log (event_type, entity_name, entity_id, details)
    VALUES (
        v_event_type,
        'APP_USERS',
        :NEW.user_id,
        'login=' || :NEW.login || '; role=' || :NEW.role_code || '; active=' || :NEW.is_active
    );
END;
/

CREATE OR REPLACE TRIGGER trg_audit_attempts
AFTER INSERT OR UPDATE OF status ON attempts
FOR EACH ROW
DECLARE
    v_event_type VARCHAR2(40);
BEGIN
    IF INSERTING THEN
        v_event_type := 'ATTEMPT_STARTED';
    ELSE
        v_event_type := 'ATTEMPT_' || :NEW.status;
    END IF;
    INSERT INTO audit_log (event_type, entity_name, entity_id, details)
    VALUES (
        v_event_type,
        'ATTEMPTS',
        :NEW.attempt_id,
        'user_id=' || :NEW.user_id || '; quiz_id=' || :NEW.quiz_id
    );
END;
/
