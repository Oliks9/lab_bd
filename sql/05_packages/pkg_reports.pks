CREATE OR REPLACE PACKAGE pkg_reports AUTHID DEFINER AS
    TYPE catalog_row IS RECORD (
        quiz_id quizzes.quiz_id%TYPE,
        topic_id quizzes.topic_id%TYPE,
        topic_title topics.title%TYPE,
        quiz_title quizzes.title%TYPE,
        description quizzes.description%TYPE,
        timer_mode quizzes.timer_mode%TYPE,
        duration_minutes NUMBER,
        attempt_limit NUMBER,
        show_feedback NUMBER,
        access_mode quizzes.access_mode%TYPE,
        status quizzes.status%TYPE,
        author_name app_users.full_name%TYPE,
        question_count NUMBER,
        max_points NUMBER,
        selection_category_id NUMBER,
        selection_category_title categories.title%TYPE,
        selection_difficulty_name difficulty_levels.difficulty_name%TYPE,
        pool_count NUMBER
    );

    TYPE result_row IS RECORD (
        attempt_id attempts.attempt_id%TYPE,
        user_id attempts.user_id%TYPE,
        login app_users.login%TYPE,
        full_name app_users.full_name%TYPE,
        quiz_id attempts.quiz_id%TYPE,
        quiz_title quizzes.title%TYPE,
        topic_title topics.title%TYPE,
        started_at attempts.started_at%TYPE,
        deadline_at attempts.deadline_at%TYPE,
        finished_at attempts.finished_at%TYPE,
        status attempts.status%TYPE,
        awarded_points NUMBER,
        max_points NUMBER,
        score_percent NUMBER,
        question_count NUMBER,
        correct_count NUMBER,
        peer_average_percent NUMBER,
        difference_pp NUMBER,
        peer_attempt_count NUMBER,
        peer_user_count NUMBER,
        comparison_code VARCHAR2(20)
    );

    TYPE detail_row IS RECORD (
        attempt_id attempts.attempt_id%TYPE,
        display_order attempt_questions.display_order%TYPE,
        question_id questions.question_id%TYPE,
        question_text questions.question_text%TYPE,
        type_code questions.type_code%TYPE,
        explanation questions.explanation%TYPE,
        points NUMBER,
        text_answer user_answers.text_answer%TYPE,
        is_correct NUMBER,
        awarded_points NUMBER,
        given_answer VARCHAR2(32767),
        correct_answer VARCHAR2(32767)
    );

    PROCEDURE catalog(p_user_id IN NUMBER, p_topic_id IN NUMBER, p_rows OUT SYS_REFCURSOR);
    PROCEDURE history(p_user_id IN NUMBER, p_rows OUT SYS_REFCURSOR);
    PROCEDURE attempt_result(p_attempt_id IN NUMBER, p_rows OUT SYS_REFCURSOR);
    PROCEDURE attempt_details(p_attempt_id IN NUMBER, p_rows OUT SYS_REFCURSOR);
    PROCEDURE quiz_statistics(p_actor_id IN NUMBER, p_rows OUT SYS_REFCURSOR);
    PROCEDURE question_statistics(p_quiz_id IN NUMBER, p_rows OUT SYS_REFCURSOR);
    PROCEDURE leaderboard(p_rows OUT SYS_REFCURSOR);
END pkg_reports;
/
