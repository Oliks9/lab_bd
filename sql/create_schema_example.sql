-- Run this example as a DBA user before install.sql.
-- Change the schema password before using the project outside a demonstration environment.
CREATE USER quiz_app IDENTIFIED BY QuizSchema2026;
GRANT CREATE SESSION, CREATE TABLE, CREATE VIEW, CREATE PROCEDURE, CREATE TRIGGER TO quiz_app;
ALTER USER quiz_app QUOTA UNLIMITED ON USERS;

-- Then connect as QUIZ_APP and execute:
-- @install.sql
