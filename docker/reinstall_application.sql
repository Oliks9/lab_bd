WHENEVER SQLERROR EXIT SQL.SQLCODE
SET SERVEROUTPUT ON

CONNECT quiz_app/"P@ssw0rd"@//localhost:1521/FREEPDB1
@/opt/quiz-project/docker/install_modules.sql
@/opt/quiz-project/sql/tests/seed_installation_test.sql
@/opt/quiz-project/sql/tests/check_invalid_objects.sql
@/opt/quiz-project/sql/tests/timezone_smoke_test.sql
@/opt/quiz-project/sql/tests/auth_smoke_test.sql
@/opt/quiz-project/sql/tests/content_management_smoke_test.sql
@/opt/quiz-project/sql/tests/smoke_test.sql

EXIT
