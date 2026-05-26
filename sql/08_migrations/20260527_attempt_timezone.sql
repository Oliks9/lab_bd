WHENEVER SQLERROR EXIT SQL.SQLCODE
SET SERVEROUTPUT ON

PROMPT === Migrating attempt timestamps to timezone-aware values ===

DECLARE
    v_data_type USER_TAB_COLUMNS.DATA_TYPE%TYPE;
    v_timezone VARCHAR2(10);
BEGIN
    SELECT data_type
      INTO v_data_type
      FROM user_tab_columns
     WHERE table_name = 'ATTEMPTS'
       AND column_name = 'STARTED_AT';

    IF INSTR(v_data_type, 'WITH TIME ZONE') > 0 THEN
        DBMS_OUTPUT.PUT_LINE('Attempt timestamps are already timezone-aware. Migration skipped.');
    ELSE
        v_timezone := TO_CHAR(SYSTIMESTAMP, 'TZH:TZM');
        DBMS_OUTPUT.PUT_LINE('Interpreting existing server-generated timestamps in timezone ' || v_timezone || '.');

        EXECUTE IMMEDIATE '
            ALTER TABLE attempts ADD (
                started_at_with_tz TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP,
                deadline_at_with_tz TIMESTAMP WITH TIME ZONE,
                finished_at_with_tz TIMESTAMP WITH TIME ZONE
            )';

        EXECUTE IMMEDIATE q'[
            UPDATE attempts
               SET started_at_with_tz = FROM_TZ(CAST(started_at AS TIMESTAMP), TO_CHAR(SYSTIMESTAMP, 'TZH:TZM')),
                   deadline_at_with_tz = CASE
                       WHEN deadline_at IS NULL THEN NULL
                       ELSE FROM_TZ(CAST(deadline_at AS TIMESTAMP), TO_CHAR(SYSTIMESTAMP, 'TZH:TZM'))
                   END,
                   finished_at_with_tz = CASE
                       WHEN finished_at IS NULL THEN NULL
                       ELSE FROM_TZ(CAST(finished_at AS TIMESTAMP), TO_CHAR(SYSTIMESTAMP, 'TZH:TZM'))
                   END
        ]';

        EXECUTE IMMEDIATE 'ALTER TABLE attempts MODIFY (started_at_with_tz NOT NULL)';
        EXECUTE IMMEDIATE 'DROP INDEX ix_attempts_user_date';
        EXECUTE IMMEDIATE 'ALTER TABLE attempts RENAME COLUMN started_at TO started_at_without_tz';
        EXECUTE IMMEDIATE 'ALTER TABLE attempts RENAME COLUMN deadline_at TO deadline_at_without_tz';
        EXECUTE IMMEDIATE 'ALTER TABLE attempts RENAME COLUMN finished_at TO finished_at_without_tz';
        EXECUTE IMMEDIATE 'ALTER TABLE attempts RENAME COLUMN started_at_with_tz TO started_at';
        EXECUTE IMMEDIATE 'ALTER TABLE attempts RENAME COLUMN deadline_at_with_tz TO deadline_at';
        EXECUTE IMMEDIATE 'ALTER TABLE attempts RENAME COLUMN finished_at_with_tz TO finished_at';
        EXECUTE IMMEDIATE 'ALTER TABLE attempts DROP COLUMN started_at_without_tz';
        EXECUTE IMMEDIATE 'ALTER TABLE attempts DROP COLUMN deadline_at_without_tz';
        EXECUTE IMMEDIATE 'ALTER TABLE attempts DROP COLUMN finished_at_without_tz';
        EXECUTE IMMEDIATE 'CREATE INDEX ix_attempts_user_date ON attempts(user_id, started_at DESC)';

        DBMS_OUTPUT.PUT_LINE('Attempt timestamp migration completed without deleting application data.');
    END IF;
END;
/
