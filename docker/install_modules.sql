WHENEVER SQLERROR EXIT SQL.SQLCODE
SET DEFINE OFF
SET SERVEROUTPUT ON

PROMPT === Removing previous application objects ===
@/opt/quiz-project/sql/00_uninstall.sql

PROMPT === Creating tables and indexes ===
@/opt/quiz-project/sql/01_tables/01_tables.sql
@/opt/quiz-project/sql/01_tables/02_indexes.sql

PROMPT === Creating standalone functions ===
@/opt/quiz-project/sql/02_functions/fn_hash_password.sql
@/opt/quiz-project/sql/02_functions/fn_can_access_quiz.sql
@/opt/quiz-project/sql/02_functions/fn_attempt_percent.sql
@/opt/quiz-project/sql/02_functions/fn_quiz_pool_count.sql

PROMPT === Creating account procedures ===
@/opt/quiz-project/sql/03_procedures/pr_register_user.sql

PROMPT === Creating validation and audit triggers ===
@/opt/quiz-project/sql/04_triggers/trg_app_users_biu.sql
@/opt/quiz-project/sql/04_triggers/trg_quizzes_biu.sql
@/opt/quiz-project/sql/04_triggers/trg_attempts_biu.sql
@/opt/quiz-project/sql/04_triggers/trg_audit.sql

PROMPT === Creating business packages ===
@/opt/quiz-project/sql/05_packages/pkg_testing.pks
@/opt/quiz-project/sql/05_packages/pkg_testing.pkb
@/opt/quiz-project/sql/03_procedures/pr_login.sql
@/opt/quiz-project/sql/05_packages/pkg_admin.pks
@/opt/quiz-project/sql/05_packages/pkg_admin.pkb

PROMPT === Creating report views ===
@/opt/quiz-project/sql/06_views/01_views.sql

PROMPT === Loading dictionaries, three accounts, three quizzes and saved demo sessions ===
@/opt/quiz-project/sql/07_seed/01_reference_data.sql
@/opt/quiz-project/sql/07_seed/02_admin_and_demo_quiz.sql
@/opt/quiz-project/sql/07_seed/03_subjects_and_users.sql
@/opt/quiz-project/sql/07_seed/04_demo_attempts.sql

COMMIT;
PROMPT === Quiz platform installed successfully ===
