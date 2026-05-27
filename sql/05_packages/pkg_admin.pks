CREATE OR REPLACE PACKAGE pkg_admin AS
    PROCEDURE create_topic (
        p_actor_id IN NUMBER,
        p_title IN VARCHAR2,
        p_description IN VARCHAR2,
        p_topic_id OUT NUMBER
    );

    PROCEDURE create_category (
        p_actor_id IN NUMBER,
        p_topic_id IN NUMBER,
        p_title IN VARCHAR2,
        p_category_id OUT NUMBER
    );

    PROCEDURE create_quiz (
        p_actor_id IN NUMBER,
        p_topic_id IN NUMBER,
        p_title IN VARCHAR2,
        p_description IN VARCHAR2,
        p_duration_minutes IN NUMBER,
        p_show_feedback IN NUMBER,
        p_access_mode IN VARCHAR2,
        p_quiz_id OUT NUMBER
    );

    PROCEDURE add_question (
        p_actor_id IN NUMBER,
        p_quiz_id IN NUMBER,
        p_category_id IN NUMBER,
        p_type_code IN VARCHAR2,
        p_difficulty_code IN VARCHAR2,
        p_question_text IN VARCHAR2,
        p_expected_answer IN VARCHAR2,
        p_explanation IN VARCHAR2,
        p_points IN NUMBER,
        p_question_id OUT NUMBER
    );

    PROCEDURE update_question (
        p_actor_id IN NUMBER,
        p_question_id IN NUMBER,
        p_category_id IN NUMBER,
        p_type_code IN VARCHAR2,
        p_difficulty_code IN VARCHAR2,
        p_question_text IN VARCHAR2,
        p_expected_answer IN VARCHAR2,
        p_explanation IN VARCHAR2,
        p_points IN NUMBER
    );

    PROCEDURE add_option (
        p_actor_id IN NUMBER,
        p_question_id IN NUMBER,
        p_option_text IN VARCHAR2,
        p_is_correct IN NUMBER,
        p_option_id OUT NUMBER
    );

    PROCEDURE publish_quiz (
        p_actor_id IN NUMBER,
        p_quiz_id IN NUMBER
    );

    PROCEDURE grant_access (
        p_actor_id IN NUMBER,
        p_quiz_id IN NUMBER,
        p_user_id IN NUMBER
    );

    PROCEDURE delete_category (
        p_admin_id IN NUMBER,
        p_category_id IN NUMBER
    );

    PROCEDURE delete_topic (
        p_admin_id IN NUMBER,
        p_topic_id IN NUMBER
    );

    PROCEDURE delete_question (
        p_admin_id IN NUMBER,
        p_question_id IN NUMBER
    );

    PROCEDURE delete_quiz (
        p_admin_id IN NUMBER,
        p_quiz_id IN NUMBER
    );

    PROCEDURE archive_quiz (
        p_admin_id IN NUMBER,
        p_quiz_id IN NUMBER
    );

    PROCEDURE reset_user_quiz_attempts (
        p_admin_id IN NUMBER,
        p_user_id IN NUMBER,
        p_quiz_id IN NUMBER
    );

    PROCEDURE reset_user_progress (
        p_admin_id IN NUMBER,
        p_user_id IN NUMBER
    );

    PROCEDURE create_author (
        p_admin_id IN NUMBER,
        p_login IN VARCHAR2,
        p_password IN VARCHAR2,
        p_full_name IN VARCHAR2,
        p_user_id OUT NUMBER
    );

    PROCEDURE set_user_role (
        p_admin_id IN NUMBER,
        p_user_id IN NUMBER,
        p_role_code IN VARCHAR2
    );
END pkg_admin;
/
