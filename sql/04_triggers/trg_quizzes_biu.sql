CREATE OR REPLACE TRIGGER trg_quizzes_biu
BEFORE INSERT OR UPDATE ON quizzes
FOR EACH ROW
BEGIN
    :NEW.title := TRIM(:NEW.title);
    IF INSERTING THEN
        :NEW.created_at := NVL(:NEW.created_at, SYSTIMESTAMP);
    END IF;
    :NEW.updated_at := SYSTIMESTAMP;
END;
/
