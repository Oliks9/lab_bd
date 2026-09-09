WHENEVER SQLERROR EXIT SQL.SQLCODE
SET SERVEROUTPUT ON

CONNECT quiz_app/"P@ssw0rd"@//localhost:1521/FREEPDB1

@/opt/quiz-project/sql/08_migrations/20260527_attempt_timezone.sql
@/opt/quiz-project/sql/08_migrations/20260527_quiz_timer_mode.sql
@/opt/quiz-project/sql/08_migrations/20260527_ordering_sequence_mode.sql
@/opt/quiz-project/sql/08_migrations/20260527_attempt_limit.sql

PROMPT === Recompiling PL/SQL application modules without deleting data ===
@/opt/quiz-project/sql/02_functions/fn_hash_password.sql
@/opt/quiz-project/sql/02_functions/fn_can_access_quiz.sql
@/opt/quiz-project/sql/02_functions/fn_attempt_percent.sql
@/opt/quiz-project/sql/03_procedures/pr_register_user.sql
@/opt/quiz-project/sql/04_triggers/trg_app_users_biu.sql
@/opt/quiz-project/sql/04_triggers/trg_quizzes_biu.sql
@/opt/quiz-project/sql/04_triggers/trg_attempts_biu.sql
@/opt/quiz-project/sql/04_triggers/trg_audit.sql
@/opt/quiz-project/sql/05_packages/pkg_testing.pks
@/opt/quiz-project/sql/05_packages/pkg_testing.pkb
@/opt/quiz-project/sql/03_procedures/pr_login.sql
@/opt/quiz-project/sql/05_packages/pkg_admin.pks
@/opt/quiz-project/sql/05_packages/pkg_admin.pkb
@/opt/quiz-project/sql/06_views/01_views.sql

@/opt/quiz-project/sql/tests/check_invalid_objects.sql
@/opt/quiz-project/sql/tests/timezone_smoke_test.sql
@/opt/quiz-project/sql/tests/auth_smoke_test.sql
@/opt/quiz-project/sql/tests/content_management_smoke_test.sql
@/opt/quiz-project/sql/tests/smoke_test.sql

@/opt/quiz-project/sql/tests/server_logic_smoke_test.sql

EXIT
