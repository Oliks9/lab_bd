WHENEVER SQLERROR EXIT SQL.SQLCODE
SET SERVEROUTPUT ON

CONNECT quiz_app/"P@ssw0rd"@//localhost:1521/FREEPDB1
@/opt/quiz-project/sql/tests/check_invalid_objects.sql
@/opt/quiz-project/sql/tests/timezone_smoke_test.sql
@/opt/quiz-project/sql/tests/auth_smoke_test.sql
@/opt/quiz-project/sql/tests/content_management_smoke_test.sql
@/opt/quiz-project/sql/tests/smoke_test.sql

@/opt/quiz-project/sql/tests/server_logic_smoke_test.sql
@/opt/quiz-project/sql/tests/comparison_smoke_test.sql
@/opt/quiz-project/sql/tests/question_selection_smoke_test.sql
@/opt/quiz-project/sql/tests/reports_smoke_test.sql

EXIT
