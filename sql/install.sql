WHENEVER SQLERROR EXIT SQL.SQLCODE
SET DEFINE OFF
SET SERVEROUTPUT ON

PROMPT === Removing previous application objects ===
@@00_uninstall.sql

PROMPT === Creating tables and indexes ===
@@01_tables/01_tables.sql
@@01_tables/02_indexes.sql

PROMPT === Creating standalone functions ===
@@02_functions/fn_hash_password.sql
@@02_functions/fn_can_access_quiz.sql
@@02_functions/fn_attempt_percent.sql
@@02_functions/fn_quiz_pool_count.sql

PROMPT === Creating account procedures ===
@@03_procedures/pr_register_user.sql

PROMPT === Creating validation and audit triggers ===
@@04_triggers/trg_app_users_biu.sql
@@04_triggers/trg_quizzes_biu.sql
@@04_triggers/trg_attempts_biu.sql
@@04_triggers/trg_audit.sql

PROMPT === Creating business packages ===
@@05_packages/pkg_testing.pks
@@05_packages/pkg_testing.pkb
@@03_procedures/pr_login.sql
@@05_packages/pkg_admin.pks
@@05_packages/pkg_admin.pkb

PROMPT === Creating report views ===
@@06_views/01_views.sql

PROMPT === Loading initial roles, dictionary values, admin and demo quiz ===
@@07_seed/01_reference_data.sql
@@07_seed/02_admin_and_demo_quiz.sql

COMMIT;
PROMPT === Quiz platform installed successfully ===
