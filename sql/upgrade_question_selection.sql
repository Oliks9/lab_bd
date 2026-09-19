WHENEVER SQLERROR EXIT SQL.SQLCODE
SET DEFINE OFF
SET SERVEROUTPUT ON

PROMPT === Update the currently connected application schema; no users or data are deleted ===
@@08_migrations/20260912_question_selection.sql
@@02_functions/fn_quiz_pool_count.sql
@@05_packages/pkg_testing.pks
@@05_packages/pkg_testing.pkb
@@03_procedures/pr_login.sql
@@05_packages/pkg_admin.pks
@@05_packages/pkg_admin.pkb
@@05_packages/pkg_reports.pks
@@05_packages/pkg_reports.pkb
@@tests/check_invalid_objects.sql
COMMIT;
PROMPT === Question selection update complete ===
