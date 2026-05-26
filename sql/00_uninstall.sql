SET SERVEROUTPUT ON

DECLARE
    PROCEDURE drop_if_exists(p_statement VARCHAR2) IS
    BEGIN
        EXECUTE IMMEDIATE p_statement;
        DBMS_OUTPUT.PUT_LINE('Dropped: ' || p_statement);
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLCODE NOT IN (-942, -4043, -4080) THEN
                RAISE;
            END IF;
    END;
BEGIN
    drop_if_exists('DROP VIEW v_leaderboard');
    drop_if_exists('DROP VIEW v_question_statistics');
    drop_if_exists('DROP VIEW v_attempt_details');
    drop_if_exists('DROP VIEW v_attempt_history');
    drop_if_exists('DROP VIEW v_quiz_catalog');
    drop_if_exists('DROP VIEW v_attempt_results');

    drop_if_exists('DROP PACKAGE pkg_testing');
    drop_if_exists('DROP PACKAGE pkg_admin');
    drop_if_exists('DROP PACKAGE quiz_pkg');

    drop_if_exists('DROP PROCEDURE pr_login');
    drop_if_exists('DROP PROCEDURE pr_register_user');
    drop_if_exists('DROP FUNCTION fn_attempt_percent');
    drop_if_exists('DROP FUNCTION fn_can_access_quiz');
    drop_if_exists('DROP FUNCTION fn_hash_password');

    drop_if_exists('DROP TABLE audit_log CASCADE CONSTRAINTS PURGE');
    drop_if_exists('DROP TABLE answer_choices CASCADE CONSTRAINTS PURGE');
    drop_if_exists('DROP TABLE user_answers CASCADE CONSTRAINTS PURGE');
    drop_if_exists('DROP TABLE attempt_answers CASCADE CONSTRAINTS PURGE');
    drop_if_exists('DROP TABLE attempt_questions CASCADE CONSTRAINTS PURGE');
    drop_if_exists('DROP TABLE attempts CASCADE CONSTRAINTS PURGE');
    drop_if_exists('DROP TABLE quiz_access CASCADE CONSTRAINTS PURGE');
    drop_if_exists('DROP TABLE question_options CASCADE CONSTRAINTS PURGE');
    drop_if_exists('DROP TABLE questions CASCADE CONSTRAINTS PURGE');
    drop_if_exists('DROP TABLE categories CASCADE CONSTRAINTS PURGE');
    drop_if_exists('DROP TABLE quizzes CASCADE CONSTRAINTS PURGE');
    drop_if_exists('DROP TABLE topics CASCADE CONSTRAINTS PURGE');
    drop_if_exists('DROP TABLE difficulty_levels CASCADE CONSTRAINTS PURGE');
    drop_if_exists('DROP TABLE question_types CASCADE CONSTRAINTS PURGE');
    drop_if_exists('DROP TABLE app_users CASCADE CONSTRAINTS PURGE');
    drop_if_exists('DROP TABLE quiz_users CASCADE CONSTRAINTS PURGE');
    drop_if_exists('DROP TABLE roles CASCADE CONSTRAINTS PURGE');
END;
/
