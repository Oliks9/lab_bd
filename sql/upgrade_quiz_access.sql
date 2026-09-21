WHENEVER SQLERROR EXIT SQL.SQLCODE
SET DEFINE OFF
SET SERVEROUTPUT ON

PROMPT === Updating quiz access settings; existing data is preserved ===
@@05_packages/pkg_admin.pks
@@05_packages/pkg_admin.pkb
@@tests/check_invalid_objects.sql
PROMPT === Quiz access settings updated ===
