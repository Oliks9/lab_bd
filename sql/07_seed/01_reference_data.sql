INSERT INTO roles (role_code, role_name) VALUES ('USER', 'Пользователь');
INSERT INTO roles (role_code, role_name) VALUES ('AUTHOR', 'Автор');
INSERT INTO roles (role_code, role_name) VALUES ('ADMIN', 'Администратор');

INSERT INTO question_types (type_code, type_name, answer_mode) VALUES ('SINGLE_CHOICE', 'Один вариант', 'OPTIONS');
INSERT INTO question_types (type_code, type_name, answer_mode) VALUES ('MULTIPLE_CHOICE', 'Несколько вариантов', 'OPTIONS');
INSERT INTO question_types (type_code, type_name, answer_mode) VALUES ('TEXT', 'Текстовый ответ', 'TEXT');
INSERT INTO question_types (type_code, type_name, answer_mode) VALUES ('NUMBER', 'Числовой ответ', 'TEXT');
INSERT INTO question_types (type_code, type_name, answer_mode) VALUES ('BOOLEAN', 'Верно / неверно', 'OPTIONS');
INSERT INTO question_types (type_code, type_name, answer_mode) VALUES ('ORDERING', 'Упорядочивание', 'TEXT');

INSERT INTO difficulty_levels (difficulty_code, difficulty_name, level_order) VALUES ('EASY', 'Начальный', 1);
INSERT INTO difficulty_levels (difficulty_code, difficulty_name, level_order) VALUES ('MEDIUM', 'Средний', 2);
INSERT INTO difficulty_levels (difficulty_code, difficulty_name, level_order) VALUES ('HARD', 'Продвинутый', 3);
