CREATE INDEX ix_categories_topic ON categories(topic_id);
CREATE INDEX ix_quizzes_topic_status ON quizzes(topic_id, status);
CREATE INDEX ix_attempts_user_date ON attempts(user_id, started_at DESC);
CREATE INDEX ix_answers_attempt ON user_answers(attempt_id);
CREATE INDEX ix_audit_entity ON audit_log(entity_name, entity_id, created_at);
