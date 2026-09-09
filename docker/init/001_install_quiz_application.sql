WHENEVER SQLERROR EXIT SQL.SQLCODE
SET SERVEROUTPUT ON

PROMPT === Creating application schema in FREEPDB1 ===
ALTER SESSION SET CONTAINER = FREEPDB1;

CREATE USER quiz_app IDENTIFIED BY "P@ssw0rd";
GRANT CREATE SESSION, CREATE TABLE, CREATE VIEW, CREATE PROCEDURE, CREATE TRIGGER, CREATE SEQUENCE TO quiz_app;
ALTER USER quiz_app QUOTA UNLIMITED ON USERS;

PROMPT === Installing quiz application objects as QUIZ_APP ===
CONNECT quiz_app/"P@ssw0rd"@//localhost:1521/FREEPDB1
@/opt/quiz-project/docker/install_modules.sql

PROMPT === Checking compiled Oracle objects ===
@/opt/quiz-project/sql/tests/check_invalid_objects.sql
@/opt/quiz-project/sql/tests/timezone_smoke_test.sql

PROMPT === Running database smoke test ===
@/opt/quiz-project/sql/tests/auth_smoke_test.sql
@/opt/quiz-project/sql/tests/content_management_smoke_test.sql
@/opt/quiz-project/sql/tests/smoke_test.sql

@/opt/quiz-project/sql/tests/server_logic_smoke_test.sql

EXIT
