WHENEVER SQLERROR EXIT SQL.SQLCODE
SET DEFINE OFF
SET SERVEROUTPUT ON

PROMPT === Installing reports without CREATE VIEW; existing data is preserved ===
@@upgrade_question_selection.sql
PROMPT === Reports update complete; restart with the new client ===
