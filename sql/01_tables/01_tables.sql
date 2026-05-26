CREATE TABLE roles (
    role_code VARCHAR2(20) CONSTRAINT pk_roles PRIMARY KEY,
    role_name VARCHAR2(100) NOT NULL
);

CREATE TABLE app_users (
    user_id NUMBER GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_app_users PRIMARY KEY,
    login VARCHAR2(50) NOT NULL CONSTRAINT uq_app_users_login UNIQUE,
    password_hash VARCHAR2(64) NOT NULL,
    full_name VARCHAR2(200) NOT NULL,
    role_code VARCHAR2(20) DEFAULT 'USER' NOT NULL
        CONSTRAINT fk_app_users_role REFERENCES roles(role_code),
    is_active NUMBER(1) DEFAULT 1 NOT NULL
        CONSTRAINT ck_app_users_active CHECK (is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL
);

CREATE TABLE question_types (
    type_code VARCHAR2(30) CONSTRAINT pk_question_types PRIMARY KEY,
    type_name VARCHAR2(100) NOT NULL,
    answer_mode VARCHAR2(20) NOT NULL
        CONSTRAINT ck_question_type_mode CHECK (answer_mode IN ('OPTIONS', 'TEXT'))
);

CREATE TABLE difficulty_levels (
    difficulty_code VARCHAR2(20) CONSTRAINT pk_difficulty PRIMARY KEY,
    difficulty_name VARCHAR2(100) NOT NULL,
    level_order NUMBER NOT NULL CONSTRAINT uq_difficulty_order UNIQUE
);

CREATE TABLE topics (
    topic_id NUMBER GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_topics PRIMARY KEY,
    title VARCHAR2(150) NOT NULL CONSTRAINT uq_topics_title UNIQUE,
    description VARCHAR2(1000),
    created_by NUMBER NOT NULL CONSTRAINT fk_topics_author REFERENCES app_users(user_id),
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL
);

CREATE TABLE categories (
    category_id NUMBER GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_categories PRIMARY KEY,
    topic_id NUMBER NOT NULL CONSTRAINT fk_categories_topic REFERENCES topics(topic_id) ON DELETE CASCADE,
    title VARCHAR2(150) NOT NULL,
    CONSTRAINT uq_categories_topic_title UNIQUE (topic_id, title)
);

CREATE TABLE quizzes (
    quiz_id NUMBER GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_quizzes PRIMARY KEY,
    topic_id NUMBER NOT NULL CONSTRAINT fk_quizzes_topic REFERENCES topics(topic_id),
    author_id NUMBER NOT NULL CONSTRAINT fk_quizzes_author REFERENCES app_users(user_id),
    title VARCHAR2(200) NOT NULL,
    description VARCHAR2(1000),
    duration_minutes NUMBER DEFAULT 15 NOT NULL
        CONSTRAINT ck_quizzes_duration CHECK (duration_minutes BETWEEN 1 AND 1440),
    question_limit NUMBER
        CONSTRAINT ck_quizzes_limit CHECK (question_limit IS NULL OR question_limit > 0),
    show_feedback NUMBER(1) DEFAULT 1 NOT NULL
        CONSTRAINT ck_quizzes_feedback CHECK (show_feedback IN (0, 1)),
    access_mode VARCHAR2(15) DEFAULT 'PUBLIC' NOT NULL
        CONSTRAINT ck_quizzes_access CHECK (access_mode IN ('PUBLIC', 'RESTRICTED')),
    status VARCHAR2(15) DEFAULT 'DRAFT' NOT NULL
        CONSTRAINT ck_quizzes_status CHECK (status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')),
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT uq_quizzes_topic_title UNIQUE (topic_id, title)
);

CREATE TABLE quiz_access (
    quiz_id NUMBER NOT NULL CONSTRAINT fk_quiz_access_quiz REFERENCES quizzes(quiz_id) ON DELETE CASCADE,
    user_id NUMBER NOT NULL CONSTRAINT fk_quiz_access_user REFERENCES app_users(user_id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT pk_quiz_access PRIMARY KEY (quiz_id, user_id)
);

CREATE TABLE questions (
    question_id NUMBER GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_questions PRIMARY KEY,
    quiz_id NUMBER NOT NULL CONSTRAINT fk_questions_quiz REFERENCES quizzes(quiz_id) ON DELETE CASCADE,
    category_id NUMBER NOT NULL CONSTRAINT fk_questions_category REFERENCES categories(category_id),
    type_code VARCHAR2(30) NOT NULL CONSTRAINT fk_questions_type REFERENCES question_types(type_code),
    difficulty_code VARCHAR2(20) NOT NULL CONSTRAINT fk_questions_difficulty REFERENCES difficulty_levels(difficulty_code),
    seq_no NUMBER NOT NULL CONSTRAINT ck_questions_seq CHECK (seq_no > 0),
    question_text VARCHAR2(2000) NOT NULL,
    expected_answer VARCHAR2(1000),
    explanation VARCHAR2(2000),
    image_path VARCHAR2(500),
    points NUMBER(6, 2) DEFAULT 1 NOT NULL CONSTRAINT ck_questions_points CHECK (points > 0),
    CONSTRAINT uq_questions_quiz_seq UNIQUE (quiz_id, seq_no)
);

CREATE TABLE question_options (
    option_id NUMBER GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_question_options PRIMARY KEY,
    question_id NUMBER NOT NULL CONSTRAINT fk_options_question REFERENCES questions(question_id) ON DELETE CASCADE,
    seq_no NUMBER NOT NULL CONSTRAINT ck_options_seq CHECK (seq_no > 0),
    option_text VARCHAR2(1000) NOT NULL,
    is_correct NUMBER(1) DEFAULT 0 NOT NULL
        CONSTRAINT ck_options_correct CHECK (is_correct IN (0, 1)),
    CONSTRAINT uq_options_question_seq UNIQUE (question_id, seq_no)
);

CREATE TABLE attempts (
    attempt_id NUMBER GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_attempts PRIMARY KEY,
    user_id NUMBER NOT NULL CONSTRAINT fk_attempts_user REFERENCES app_users(user_id),
    quiz_id NUMBER NOT NULL CONSTRAINT fk_attempts_quiz REFERENCES quizzes(quiz_id),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    deadline_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR2(20) DEFAULT 'IN_PROGRESS' NOT NULL
        CONSTRAINT ck_attempts_status CHECK (status IN ('IN_PROGRESS', 'FINISHED', 'EXPIRED')),
    awarded_points NUMBER(8, 2),
    max_points NUMBER(8, 2),
    score_percent NUMBER(6, 2)
        CONSTRAINT ck_attempts_score CHECK (score_percent IS NULL OR score_percent BETWEEN 0 AND 100)
);

CREATE TABLE attempt_questions (
    attempt_id NUMBER NOT NULL CONSTRAINT fk_attempt_questions_attempt REFERENCES attempts(attempt_id) ON DELETE CASCADE,
    question_id NUMBER NOT NULL CONSTRAINT fk_attempt_questions_question REFERENCES questions(question_id),
    display_order NUMBER NOT NULL,
    CONSTRAINT pk_attempt_questions PRIMARY KEY (attempt_id, question_id),
    CONSTRAINT uq_attempt_question_order UNIQUE (attempt_id, display_order)
);

CREATE TABLE user_answers (
    answer_id NUMBER GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_user_answers PRIMARY KEY,
    attempt_id NUMBER NOT NULL,
    question_id NUMBER NOT NULL,
    text_answer VARCHAR2(1000),
    submitted_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    is_correct NUMBER(1) CONSTRAINT ck_user_answers_correct CHECK (is_correct IN (0, 1)),
    awarded_points NUMBER(6, 2) DEFAULT 0 NOT NULL,
    CONSTRAINT uq_user_answers_attempt_question UNIQUE (attempt_id, question_id),
    CONSTRAINT fk_answers_attempt_question FOREIGN KEY (attempt_id, question_id)
        REFERENCES attempt_questions(attempt_id, question_id) ON DELETE CASCADE
);

CREATE TABLE answer_choices (
    answer_id NUMBER NOT NULL CONSTRAINT fk_answer_choices_answer REFERENCES user_answers(answer_id) ON DELETE CASCADE,
    option_id NUMBER NOT NULL CONSTRAINT fk_answer_choices_option REFERENCES question_options(option_id),
    CONSTRAINT pk_answer_choices PRIMARY KEY (answer_id, option_id)
);

CREATE TABLE audit_log (
    audit_id NUMBER GENERATED ALWAYS AS IDENTITY CONSTRAINT pk_audit_log PRIMARY KEY,
    event_type VARCHAR2(40) NOT NULL,
    entity_name VARCHAR2(40) NOT NULL,
    entity_id NUMBER,
    details VARCHAR2(1000),
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL
);
