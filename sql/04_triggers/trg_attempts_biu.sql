CREATE OR REPLACE TRIGGER trg_attempts_biu
BEFORE INSERT OR UPDATE ON attempts
FOR EACH ROW
BEGIN
    IF :NEW.deadline_at IS NOT NULL AND :NEW.deadline_at < :NEW.started_at THEN
        RAISE_APPLICATION_ERROR(-20020, 'Срок попытки не может быть раньше ее начала.');
    END IF;

    IF :NEW.finished_at IS NOT NULL AND :NEW.finished_at < :NEW.started_at THEN
        RAISE_APPLICATION_ERROR(-20021, 'Время завершения не может быть раньше времени начала.');
    END IF;

    IF :NEW.status IN ('FINISHED', 'EXPIRED') AND :NEW.finished_at IS NULL THEN
        :NEW.finished_at := SYSTIMESTAMP;
    END IF;
END;
/
