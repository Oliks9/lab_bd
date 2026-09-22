WHENEVER SQLERROR EXIT SQL.SQLCODE
SET DEFINE OFF
SET SERVEROUTPUT ON
PROMPT === Updating invitation listing and revocation; existing data is preserved ===
@@upgrade_quiz_access.sql
PROMPT === Invitation management updated ===
