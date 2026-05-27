CREATE OR REPLACE PACKAGE pkg_testing AS
    PROCEDURE start_attempt (
        p_user_id IN NUMBER,
        p_quiz_id IN NUMBER,
        p_attempt_id OUT NUMBER
    );

    PROCEDURE submit_answer (
        p_attempt_id IN NUMBER,
        p_question_id IN NUMBER,
        p_selected_option_ids IN VARCHAR2,
        p_text_answer IN VARCHAR2
    );

    PROCEDURE expire_question (
        p_attempt_id IN NUMBER
    );

    PROCEDURE finish_attempt (
        p_attempt_id IN NUMBER
    );

    PROCEDURE abandon_attempt (
        p_attempt_id IN NUMBER
    );

    PROCEDURE abandon_user_attempts (
        p_user_id IN NUMBER
    );
END pkg_testing;
/
