# Полная карта серверной логики Oracle

Дата актуализации: 27.05.2026

## 1. Зона ответственности Oracle и Python

- Oracle (SQL/PLSQL) реализует бизнес-логику, права, валидацию, таймеры, оценивание, публикацию, удаление и консистентность данных.
- Python (`app/quiz_client`) работает как GUI-клиент: вызывает процедуры/пакеты и отображает результат.
- Критичные правила проверяются только на стороне БД, GUI не является источником истины.

## 2. Инвентарь объектов схемы

| Тип объекта | Кол-во | Файлы |
|---|---:|---|
| Таблицы | 15 | `sql/01_tables/01_tables.sql` |
| Индексы | 5 | `sql/01_tables/02_indexes.sql` |
| Standalone функции | 3 | `sql/02_functions/*.sql` |
| Standalone процедуры | 2 | `sql/03_procedures/*.sql` |
| Процедуры в `pkg_admin` | 22 | `sql/05_packages/pkg_admin.pks/.pkb` |
| Процедуры в `pkg_testing` | 6 | `sql/05_packages/pkg_testing.pks/.pkb` |
| Триггеры | 5 | `sql/04_triggers/*.sql` |
| Представления | 5 | `sql/06_views/01_views.sql` |
| Seed-скрипты | 2 | `sql/07_seed/*.sql` |
| Миграции | 4 | `sql/08_migrations/*.sql` |
| Smoke-тесты | 5 | `sql/tests/*.sql` |

## 3. Порядок установки и обновления

1. `sql/install.sql` удаляет старые объекты (`00_uninstall.sql`), затем создаёт схему в порядке:
   - таблицы и индексы;
   - функции;
   - standalone-процедуры;
   - триггеры;
   - пакеты;
   - представления;
   - seed-данные.
2. Для обновления без полной переустановки применяются миграции из `sql/08_migrations`.

## 4. Таблицы и связи

## 4.1. `roles`

Назначение: справочник ролей.

- `role_code VARCHAR2(20)` PK.
- `role_name VARCHAR2(100)` NOT NULL.

## 4.2. `app_users`

Назначение: учетные записи пользователей.

- `user_id NUMBER` IDENTITY, PK.
- `login VARCHAR2(50)` NOT NULL, UNIQUE (`uq_app_users_login`), хранится в lowercase.
- `password_hash VARCHAR2(64)` NOT NULL (SHA256).
- `full_name VARCHAR2(200)` NOT NULL.
- `role_code VARCHAR2(20)` NOT NULL, FK `fk_app_users_role -> roles.role_code`, default `USER`.
- `is_active NUMBER(1)` NOT NULL, CHECK `IN (0,1)`, default `1`.
- `created_at TIMESTAMP` NOT NULL.
- `updated_at TIMESTAMP` NOT NULL.

## 4.3. `question_types`

Назначение: типы вопросов и режим ответа.

- `type_code VARCHAR2(30)` PK.
- `type_name VARCHAR2(100)` NOT NULL.
- `answer_mode VARCHAR2(20)` NOT NULL, CHECK `IN ('OPTIONS','TEXT')`.

## 4.4. `difficulty_levels`

Назначение: уровни сложности.

- `difficulty_code VARCHAR2(20)` PK.
- `difficulty_name VARCHAR2(100)` NOT NULL.
- `level_order NUMBER` NOT NULL, UNIQUE (`uq_difficulty_order`).

## 4.5. `topics`

Назначение: тематики тестов.

- `topic_id NUMBER` IDENTITY, PK.
- `title VARCHAR2(150)` NOT NULL, UNIQUE (`uq_topics_title`).
- `description VARCHAR2(1000)` NULL.
- `created_by NUMBER` NOT NULL, FK `fk_topics_author -> app_users.user_id`.
- `created_at TIMESTAMP` NOT NULL.

## 4.6. `categories`

Назначение: категории вопросов внутри тематики.

- `category_id NUMBER` IDENTITY, PK.
- `topic_id NUMBER` NOT NULL, FK `fk_categories_topic -> topics.topic_id` ON DELETE CASCADE.
- `title VARCHAR2(150)` NOT NULL.
- UNIQUE `(topic_id, title)` (`uq_categories_topic_title`).

## 4.7. `quizzes`

Назначение: тесты и их настройки публикации/таймера.

- `quiz_id NUMBER` IDENTITY, PK.
- `topic_id NUMBER` NOT NULL, FK `fk_quizzes_topic -> topics.topic_id`.
- `author_id NUMBER` NOT NULL, FK `fk_quizzes_author -> app_users.user_id`.
- `title VARCHAR2(200)` NOT NULL.
- `description VARCHAR2(1000)` NULL.
- `timer_mode VARCHAR2(15)` NOT NULL, default `QUIZ`, CHECK `IN ('QUIZ','QUESTION')`.
- `duration_minutes NUMBER` NOT NULL, default `15`, CHECK `BETWEEN 1 AND 1440`.
- `question_limit NUMBER` NULL, CHECK `question_limit IS NULL OR question_limit > 0`.
- `attempt_limit NUMBER` NULL, CHECK `attempt_limit IS NULL OR attempt_limit > 0`.
- `show_feedback NUMBER(1)` NOT NULL, default `1`, CHECK `IN (0,1)`.
- `access_mode VARCHAR2(15)` NOT NULL, default `PUBLIC`, CHECK `IN ('PUBLIC','RESTRICTED')`.
- `status VARCHAR2(15)` NOT NULL, default `DRAFT`, CHECK `IN ('DRAFT','PUBLISHED','ARCHIVED')`.
- `created_at TIMESTAMP` NOT NULL.
- `updated_at TIMESTAMP` NOT NULL.
- UNIQUE `(topic_id, title)` (`uq_quizzes_topic_title`).

## 4.8. `quiz_access`

Назначение: индивидуальный доступ к закрытым тестам.

- `quiz_id NUMBER` NOT NULL, FK `fk_quiz_access_quiz -> quizzes.quiz_id` ON DELETE CASCADE.
- `user_id NUMBER` NOT NULL, FK `fk_quiz_access_user -> app_users.user_id` ON DELETE CASCADE.
- `granted_at TIMESTAMP` NOT NULL.
- PK `(quiz_id, user_id)`.

## 4.9. `questions`

Назначение: вопросы теста.

- `question_id NUMBER` IDENTITY, PK.
- `quiz_id NUMBER` NOT NULL, FK `fk_questions_quiz -> quizzes.quiz_id` ON DELETE CASCADE.
- `category_id NUMBER` NOT NULL, FK `fk_questions_category -> categories.category_id`.
- `type_code VARCHAR2(30)` NOT NULL, FK `fk_questions_type -> question_types.type_code`.
- `difficulty_code VARCHAR2(20)` NOT NULL, FK `fk_questions_difficulty -> difficulty_levels.difficulty_code`.
- `seq_no NUMBER` NOT NULL, CHECK `> 0`, UNIQUE с `quiz_id` (`uq_questions_quiz_seq`).
- `question_text VARCHAR2(2000)` NOT NULL.
- `expected_answer VARCHAR2(1000)` NULL.
- `explanation VARCHAR2(2000)` NULL.
- `image_path VARCHAR2(500)` NULL.
- `points NUMBER(6,2)` NOT NULL, default `1`, CHECK `> 0`.

## 4.10. `question_options`

Назначение: варианты ответа для option-вопросов (включая `ORDERING`).

- `option_id NUMBER` IDENTITY, PK.
- `question_id NUMBER` NOT NULL, FK `fk_options_question -> questions.question_id` ON DELETE CASCADE.
- `seq_no NUMBER` NOT NULL, CHECK `> 0`.
- `option_text VARCHAR2(1000)` NOT NULL.
- `is_correct NUMBER(1)` NOT NULL, default `0`, CHECK `IN (0,1)`.
- UNIQUE `(question_id, seq_no)` (`uq_options_question_seq`).

## 4.11. `attempts`

Назначение: попытки прохождения тестов.

- `attempt_id NUMBER` IDENTITY, PK.
- `user_id NUMBER` NOT NULL, FK `fk_attempts_user -> app_users.user_id`.
- `quiz_id NUMBER` NOT NULL, FK `fk_attempts_quiz -> quizzes.quiz_id`.
- `started_at TIMESTAMP WITH TIME ZONE` NOT NULL.
- `deadline_at TIMESTAMP WITH TIME ZONE` NULL.
- `timer_mode VARCHAR2(15)` NOT NULL, default `QUIZ`, CHECK `IN ('QUIZ','QUESTION')`.
- `question_duration_minutes NUMBER` NULL, CHECK `BETWEEN 1 AND 1440`.
- `active_question_order NUMBER` NULL, CHECK `> 0`.
- `question_started_at TIMESTAMP WITH TIME ZONE` NULL.
- `finished_at TIMESTAMP WITH TIME ZONE` NULL.
- `status VARCHAR2(20)` NOT NULL, default `IN_PROGRESS`, CHECK `IN ('IN_PROGRESS','FINISHED','EXPIRED')`.
- `awarded_points NUMBER(8,2)` NULL.
- `max_points NUMBER(8,2)` NULL.
- `score_percent NUMBER(6,2)` NULL, CHECK `BETWEEN 0 AND 100`.

## 4.12. `attempt_questions`

Назначение: состав вопросов конкретной попытки.

- `attempt_id NUMBER` NOT NULL, FK `fk_attempt_questions_attempt -> attempts.attempt_id` ON DELETE CASCADE.
- `question_id NUMBER` NOT NULL, FK `fk_attempt_questions_question -> questions.question_id`.
- `display_order NUMBER` NOT NULL.
- PK `(attempt_id, question_id)`.
- UNIQUE `(attempt_id, display_order)` (`uq_attempt_question_order`).

## 4.13. `user_answers`

Назначение: ответ пользователя на вопрос в попытке.

- `answer_id NUMBER` IDENTITY, PK.
- `attempt_id NUMBER` NOT NULL.
- `question_id NUMBER` NOT NULL.
- `text_answer VARCHAR2(1000)` NULL.
- `submitted_at TIMESTAMP` NOT NULL.
- `is_correct NUMBER(1)` NULL, CHECK `IN (0,1)`.
- `awarded_points NUMBER(6,2)` NOT NULL, default `0`.
- UNIQUE `(attempt_id, question_id)` (`uq_user_answers_attempt_question`).
- Составной FK `(attempt_id, question_id) -> attempt_questions(attempt_id, question_id)` ON DELETE CASCADE.

## 4.14. `answer_choices`

Назначение: выбранные option-варианты в ответе.

- `answer_id NUMBER` NOT NULL, FK `fk_answer_choices_answer -> user_answers.answer_id` ON DELETE CASCADE.
- `option_id NUMBER` NOT NULL, FK `fk_answer_choices_option -> question_options.option_id`.
- PK `(answer_id, option_id)`.

## 4.15. `audit_log`

Назначение: журнал событий.

- `audit_id NUMBER` IDENTITY, PK.
- `event_type VARCHAR2(40)` NOT NULL.
- `entity_name VARCHAR2(40)` NOT NULL.
- `entity_id NUMBER` NULL.
- `details VARCHAR2(1000)` NULL.
- `created_at TIMESTAMP` NOT NULL.

## 4.16. Ключевые каскады

- `topics -> categories` (ON DELETE CASCADE).
- `quizzes -> quiz_access` (ON DELETE CASCADE).
- `quizzes -> questions` (ON DELETE CASCADE).
- `questions -> question_options` (ON DELETE CASCADE).
- `attempts -> attempt_questions` (ON DELETE CASCADE).
- `attempt_questions -> user_answers` (через составной FK, ON DELETE CASCADE).
- `user_answers -> answer_choices` (ON DELETE CASCADE).

## 5. Индексы

- `ix_categories_topic ON categories(topic_id)` — быстрый отбор категорий по тематике.
- `ix_quizzes_topic_status ON quizzes(topic_id, status)` — каталог и фильтрация тестов.
- `ix_attempts_user_date ON attempts(user_id, started_at DESC)` — история пользователя.
- `ix_answers_attempt ON user_answers(attempt_id)` — детали попытки.
- `ix_audit_entity ON audit_log(entity_name, entity_id, created_at)` — поиск по журналу.

## 6. Standalone функции

## 6.1. `fn_hash_password(p_login, p_password) RETURN VARCHAR2`

- Возвращает SHA256 в `RAWTOHEX`.
- Соль: `lower(trim(login)) || ':' || password`.
- Используется при регистрации, входе, смене пароля.

## 6.2. `fn_can_access_quiz(p_user_id, p_quiz_id) RETURN NUMBER`

- Возвращает `1`, если пользователь может запустить тест, иначе `0`.
- Условия: `quizzes.status = 'PUBLISHED'` и одно из:
  - `access_mode = 'PUBLIC'`;
  - пользователь — автор;
  - роль `ADMIN`;
  - есть запись в `quiz_access`.
- Проверяет `app_users.is_active = 1`.

## 6.3. `fn_attempt_percent(p_attempt_id) RETURN NUMBER`

- Считает процент `SUM(awarded_points) / SUM(points) * 100`.
- Результат округляется до 2 знаков.
- При `max_points = 0` возвращает `0`.

## 7. Standalone процедуры

## 7.1. `pr_register_user`

Сигнатура:

- `p_login IN VARCHAR2`
- `p_password IN VARCHAR2`
- `p_full_name IN VARCHAR2`
- `p_user_id OUT NUMBER`

Логика:

- Проверяет логин regex `^[a-z0-9_.-]{3,50}$`.
- Проверяет длину пароля `>= 6`.
- Проверяет, что `full_name` не пуст.
- Создает `app_users` с ролью `USER`.

Коды ошибок:

- `-20010` — некорректный логин.
- `-20011` — короткий пароль.
- `-20012` — пустое имя.
- `-20013` — логин уже существует.

## 7.2. `pr_login`

Сигнатура:

- `p_login IN VARCHAR2`
- `p_password IN VARCHAR2`
- `p_user_id OUT NUMBER`
- `p_full_name OUT VARCHAR2`
- `p_role_code OUT VARCHAR2`

Логика:

- Ищет активного пользователя по логину и `fn_hash_password`.
- Возвращает идентификатор, имя, роль.

Коды ошибок:

- `-20014` — неверный логин/пароль или отключенная учетная запись.

## 8. Пакет `pkg_admin`

Назначение: администрирование контента, публикации и пользователей.

## 8.1. Внутренние guard-проверки

- `actor_role(p_actor_id)` — роль активного пользователя, иначе `-20100`.
- `require_editor` — только `AUTHOR/ADMIN`, иначе `-20101`.
- `require_admin` — только `ADMIN`, иначе `-20111`.
- `require_quiz_owner` — редактирование только своего `DRAFT` (или `ADMIN`), иначе `-20102`.
- `require_quiz_manager` — удаление/архивирование только своего теста (или `ADMIN`), иначе `-20125`.

## 8.2. Процедуры контента и публикации

### `create_topic(p_actor_id, p_title, p_description, p_topic_id OUT)`
- Кто: `AUTHOR/ADMIN`.
- Что делает: создает тему.
- Ошибки: `-20103` (дубликат названия).

### `create_category(p_actor_id, p_topic_id, p_title, p_category_id OUT)`
- Кто: `AUTHOR/ADMIN`.
- Что делает: создает категорию в теме.
- Ошибки: `-20104` (дубликат в теме).

### `create_quiz(p_actor_id, p_topic_id, p_title, p_description, p_timer_mode, p_duration_minutes, p_attempt_limit, p_show_feedback, p_access_mode, p_quiz_id OUT)`
- Кто: `AUTHOR/ADMIN`.
- Проверки: `timer_mode` в `QUIZ|QUESTION`; `attempt_limit` > 0 или `NULL`.
- Ошибки: `-20124`, `-20129`, `-20105`.

### `add_question(p_actor_id, p_quiz_id, p_category_id, p_type_code, p_difficulty_code, p_question_text, p_expected_answer, p_explanation, p_points, p_question_id OUT)`
- Кто: владелец `DRAFT` теста или `ADMIN`.
- Проверки: категория должна принадлежать теме теста.
- Что делает: присваивает следующий `seq_no`, создает вопрос.
- Ошибки: `-20106`.

### `update_question(p_actor_id, p_question_id, p_category_id, p_type_code, p_difficulty_code, p_question_text, p_expected_answer, p_explanation, p_points)`
- Кто: владелец `DRAFT` теста или `ADMIN`.
- Проверки: категория принадлежит теме теста.
- Что делает: обновляет вопрос, очищает старые `question_options`.
- Ошибки: `-20106`, `-20123`.

### `add_option(p_actor_id, p_question_id, p_option_text, p_is_correct, p_option_id OUT)`
- Кто: владелец `DRAFT` теста или `ADMIN`.
- Проверки: у типа вопроса `answer_mode = 'OPTIONS'`.
- Что делает: добавляет вариант с очередным `seq_no`.
- Ошибки: `-20107`.

### `publish_quiz(p_actor_id, p_quiz_id)`
- Кто: владелец `DRAFT` теста или `ADMIN`.
- Проверки:
  - в тесте есть минимум 1 вопрос;
  - для `TEXT/NUMBER` заполнен `expected_answer`;
  - для option-вопросов есть >= 2 вариантов и хотя бы 1 правильный;
  - для `SINGLE_CHOICE`/`BOOLEAN` ровно 1 правильный вариант.
- Что делает: `quizzes.status = 'PUBLISHED'`.
- Ошибки: `-20108`, `-20109`.

### `archive_quiz(p_admin_id, p_quiz_id)`
- Кто: владелец теста или `ADMIN`.
- Что делает: переводит `PUBLISHED/ARCHIVED` -> `DRAFT` (используется как черновик).
- Ошибки: `-20120`.

### `set_quiz_feedback(p_actor_id, p_quiz_id, p_show_feedback)`
- Кто: владелец `DRAFT` теста или `ADMIN`.
- Проверки: `p_show_feedback` = 0/1.
- Что делает: сохраняет флаг показа пояснений/правильных ответов.
- Ошибки: `-20127`, `-20128`.

### `set_quiz_attempt_limit(p_actor_id, p_quiz_id, p_attempt_limit)`
- Кто: владелец `DRAFT` теста или `ADMIN`.
- Проверки: `p_attempt_limit` > 0 или `NULL`.
- Что делает: сохраняет лимит попыток на пользователя.
- Ошибки: `-20130`, `-20131`.

### `grant_access(p_actor_id, p_quiz_id, p_user_id)`
- Кто: автор теста или `ADMIN`.
- Что делает: добавляет/подтверждает доступ в `quiz_access` через `MERGE`.
- Ошибка: `-20110`.

## 8.3. Процедуры удаления контента

### `delete_question(p_admin_id, p_question_id)`
- Кто: владелец теста или `ADMIN`.
- Проверки: нет `IN_PROGRESS` попыток по тесту.
- Действия:
  - удаляет связь вопроса в `attempt_questions`;
  - удаляет вопрос;
  - пересчитывает `questions.seq_no`;
  - пересчитывает `attempt_questions.display_order`;
  - пересчитывает `attempts.awarded_points`, `attempts.max_points`, `attempts.score_percent`.
- Ошибки: `-20126`, `-20118`.

### `delete_quiz(p_admin_id, p_quiz_id)`
- Кто: владелец теста или `ADMIN`.
- Действия:
  - удаляет все `attempts` по тесту;
  - удаляет тест (дочерние сущности удаляются каскадно).
- Ошибка: `-20119`.

### `delete_category(p_admin_id, p_category_id)`
- Кто: только `ADMIN`.
- Проверки: категория не используется вопросами.
- Ошибки: `-20114`, `-20115`.

### `delete_topic(p_admin_id, p_topic_id)`
- Кто: только `ADMIN`.
- Проверки: у темы нет категорий и тестов.
- Ошибки: `-20116`, `-20117`.

## 8.4. Процедуры администрирования пользователей

### `create_author(p_admin_id, p_login, p_password, p_full_name, p_user_id OUT)`
- Кто: `ADMIN`.
- Что делает: регистрирует пользователя и назначает роль `AUTHOR`.

### `set_user_role(p_admin_id, p_user_id, p_role_code)`
- Кто: `ADMIN`.
- Что делает: меняет роль пользователя.
- Защита: нельзя снять `ADMIN` с текущего администратора (`-20113`).
- Ошибка отсутствия пользователя: `-20112`.

### `set_user_password(p_admin_id, p_user_id, p_new_password)`
- Кто: `ADMIN`.
- Что делает: задает новый пароль, пересчитывает `password_hash`.
- Проверка: длина >= 6 (`-20132`).
- Ошибка отсутствия пользователя: `-20112`.

### `set_user_active(p_admin_id, p_user_id, p_is_active)`
- Кто: `ADMIN`.
- Что делает: отключает (`0`) или включает (`1`) учетную запись.
- Проверки:
  - `p_is_active` должен быть 0 или 1 (`-20135`);
  - нельзя отключить текущего администратора (`-20136`);
  - нельзя отключить аккаунт с ролью `ADMIN` (`-20137`).
- Дополнительно:
  - при отключении пользователя незавершенные попытки принудительно закрываются через `pkg_testing.abandon_user_attempts`.
- Ошибка отсутствия пользователя: `-20112`.

### `delete_user(p_admin_id, p_user_id)`
- Кто: `ADMIN`.
- Проверки:
  - нельзя удалить самого себя (`-20133`);
  - нельзя удалить аккаунт с ролью `ADMIN` (`-20134`).
- Действия:
  - удаляет попытки по тестам пользователя-автора;
  - удаляет попытки, где пользователь проходил тесты;
  - удаляет тесты пользователя;
  - переносит `topics.created_by` на администратора;
  - удаляет запись пользователя из `app_users`.
- Ошибка отсутствия пользователя: `-20112`.

### `reset_user_quiz_attempts(p_admin_id, p_user_id, p_quiz_id)`
- Кто: `ADMIN`.
- Что делает: удаляет попытки пользователя по конкретному тесту.
- Логирует событие в `audit_log` (`PROGRESS_RESET_QUIZ`).
- Ошибка: `-20121`.

### `reset_user_progress(p_admin_id, p_user_id)`
- Кто: `ADMIN`.
- Что делает: удаляет все попытки пользователя.
- Логирует событие в `audit_log` (`PROGRESS_RESET_ALL`).
- Ошибка: `-20122`.

## 9. Пакет `pkg_testing`

Назначение: прохождение теста, проверка ответов, таймеры и финализация.

## 9.1. Внутренняя процедура `advance_active_question`

- Смещает `active_question_order` на следующий вопрос.
- Если вопросы закончились, выставляет `active_question_order = total + 1` и `question_started_at = NULL`.

## 9.2. Публичные процедуры

### `start_attempt(p_user_id, p_quiz_id, p_attempt_id OUT)`
- Проверяет доступ через `fn_can_access_quiz`, иначе `-20200`.
- Проверяет `attempt_limit`, иначе `-20211`.
- Создает `attempts` с учетом `timer_mode`:
  - `QUIZ`: `deadline_at = started_at + duration_minutes`;
  - `QUESTION`: `question_duration_minutes = duration_minutes`, `active_question_order = 1`.
- Формирует `attempt_questions` по `questions.seq_no`, учитывает `question_limit`.
- Ошибка пустого теста: `-20201`.

### `submit_answer(p_attempt_id, p_question_id, p_selected_option_ids, p_text_answer)`
- Проверяет, что попытка активна (`-20202`).
- В режиме `QUIZ` проверяет общий дедлайн (`-20203`).
- В режиме `QUESTION`:
  - нельзя отвечать не на текущий вопрос (`-20208`);
  - проверяется таймер текущего вопроса (`-20203`).
- Для `OPTIONS`-типов:
  - валидация формата списка `id,id,...` (`-20204`);
  - проверка корректности набора (`-20205`);
  - для `ORDERING` требуется полный список и корректный порядок (`-20209`, `-20205`).
- Для `NUMBER` сравнивает числовое значение с допуском форматов `,`/`.`.
- Для `TEXT` сравнивает `UPPER(TRIM())`.
- Сохраняет `is_correct`, `awarded_points`.
- В режиме `QUESTION` автоматически продвигает активный вопрос.
- Ошибка несоответствия вопроса попытке: `-20206`.

### `expire_question(p_attempt_id)`
- Доступно только для `QUESTION`-режима (`-20210`).
- Если попытка `IN_PROGRESS`, переводит активный вопрос на следующий.
- Если попытка не найдена: `-20207`.

### `finish_attempt(p_attempt_id)`
- Если попытка уже завершена, просто `RETURN`.
- Считает `awarded_points`, `max_points`, `score_percent`.
- Статус:
  - `EXPIRED`, если дедлайн/таймер вопроса истек;
  - иначе `FINISHED`.
- Очищает `active_question_order`, `question_started_at`.
- Ошибка отсутствия попытки: `-20207`.

### `abandon_attempt(p_attempt_id)`
- Принудительно завершает попытку при разрыве сессии клиента.
- Использует `finish_attempt`, затем переводит статус в `EXPIRED`.

### `abandon_user_attempts(p_user_id)`
- Закрывает все попытки пользователя со статусом `IN_PROGRESS`.
- Используется при входе пользователя и при админ-деактивации аккаунта.

## 10. Триггеры

## 10.1. `trg_app_users_biu`
- BEFORE INSERT/UPDATE на `app_users`.
- Нормализует `login`, `full_name`.
- Поддерживает `created_at/updated_at`.

## 10.2. `trg_quizzes_biu`
- BEFORE INSERT/UPDATE на `quizzes`.
- Нормализует `title`.
- Поддерживает `created_at/updated_at`.

## 10.3. `trg_attempts_biu`
- BEFORE INSERT/UPDATE на `attempts`.
- Проверяет:
  - `deadline_at >= started_at` (`-20020`);
  - `finished_at >= started_at` (`-20021`).
- Для статусов `FINISHED/EXPIRED` автопроставляет `finished_at`, если он `NULL`.

## 10.4. `trg_audit_users`
- AFTER INSERT/UPDATE (`role_code`, `is_active`) на `app_users`.
- Пишет события `USER_REGISTERED`/`USER_CHANGED` в `audit_log`.

## 10.5. `trg_audit_attempts`
- AFTER INSERT/UPDATE (`status`) на `attempts`.
- Пишет события `ATTEMPT_STARTED`/`ATTEMPT_<STATUS>` в `audit_log`.

## 11. Представления

## 11.1. `v_quiz_catalog`

Каталог тестов. Колонки:

- `quiz_id`, `topic_id`, `topic_title`
- `quiz_title`, `description`
- `timer_mode`, `duration_minutes`, `attempt_limit`
- `show_feedback`, `access_mode`, `status`
- `author_name`
- `question_count`, `max_points`

## 11.2. `v_attempt_history`

История попыток. Колонки:

- `attempt_id`, `user_id`, `login`, `full_name`
- `quiz_id`, `quiz_title`, `topic_title`
- `started_at`, `deadline_at`, `finished_at`
- `status`, `awarded_points`, `max_points`, `score_percent`
- `question_count`, `correct_count`

## 11.3. `v_attempt_details`

Детализация попытки по вопросам:

- текст вопроса;
- `given_answer` в человекочитаемом виде:
  - `ORDERING`: последовательность с `->`;
  - choice-типы: список выбранных вариантов;
  - text/number: текстовый ввод;
- `correct_answer` в том же формате;
- `explanation`, `awarded_points`, `is_correct`.

Физические колонки view:

- `attempt_id`, `display_order`
- `question_id`, `question_text`, `type_code`
- `explanation`, `points`
- `text_answer`, `is_correct`, `awarded_points`
- `given_answer`, `correct_answer`

## 11.4. `v_question_statistics`

Статистика по вопросу. Колонки:

- `quiz_id`, `question_id`, `question_text`
- `answer_count`, `correct_count`, `correct_percent`

## 11.5. `v_leaderboard`

Рейтинг пользователей. Колонки:

- `user_id`, `full_name`
- `attempts_finished`, `average_score`, `best_score`

## 12. Миграции (`sql/08_migrations`)

- `20260527_quiz_timer_mode.sql` — добавляет режим таймера теста/вопроса и поля для по-вопросного таймера.
- `20260527_attempt_timezone.sql` — переводит timestamps попыток в `TIMESTAMP WITH TIME ZONE`.
- `20260527_ordering_sequence_mode.sql` — нормализует `ORDERING` на option-based режим.
- `20260527_attempt_limit.sql` — добавляет `quizzes.attempt_limit` и CHECK-ограничение.

## 13. Seed-данные

`sql/07_seed/01_reference_data.sql`:

- роли: `USER`, `AUTHOR`, `ADMIN`;
- типы вопросов: `SINGLE_CHOICE`, `MULTIPLE_CHOICE`, `TEXT`, `NUMBER`, `BOOLEAN`, `ORDERING`;
- уровни сложности: `EASY`, `MEDIUM`, `HARD`.

`sql/07_seed/02_admin_and_demo_quiz.sql`:

- создается `admin / Admin123!`;
- создается демо-тест по программированию в БД;
- добавляются вопросы всех поддерживаемых типов;
- демо-тест публикуется.

## 14. SQL-проверки и smoke-тесты

- `check_invalid_objects.sql` — контроль, что объекты `VALID`.
- `auth_smoke_test.sql` — регистрация/вход/создание автора.
- `content_management_smoke_test.sql` — полный цикл авторинга, публикации, удаления, сбросов.
- `timezone_smoke_test.sql` — проверка логики в сессии `+03:00`.
- `smoke_test.sql` — сквозной тест прохождения демо-квиза на 100%.

## 15. Почему это считается «логика на Oracle»

- Все ключевые решения и проверки находятся в `pkg_admin`, `pkg_testing`, функциях и триггерах.
- Ограничения целостности (`PK/FK/UNIQUE/CHECK`) защищают данные независимо от GUI.
- Python-клиент не дублирует правила, а только вызывает API БД.

## 16. Каталог кодов ошибок (`RAISE_APPLICATION_ERROR`)

## 16.1. Регистрация и вход

- `-20010` — некорректный логин.
- `-20011` — короткий пароль.
- `-20012` — пустое имя пользователя.
- `-20013` — логин уже существует.
- `-20014` — неверный логин/пароль или учетная запись отключена.
- `-20020` — `deadline_at` раньше `started_at`.
- `-20021` — `finished_at` раньше `started_at`.

## 16.2. `pkg_admin`

- `-20100` — пользователь не найден или неактивен.
- `-20101` — операция разрешена только `AUTHOR/ADMIN`.
- `-20102` — редактировать можно только доступный `DRAFT`.
- `-20103` — тема с таким названием уже существует.
- `-20104` — категория с таким названием уже существует в теме.
- `-20105` — тест с таким названием уже существует в теме.
- `-20106` — категория не принадлежит теме теста.
- `-20107` — для text-вопроса нельзя добавлять options.
- `-20108` — в тесте нет вопросов для публикации.
- `-20109` — тест невалиден для публикации (ответы/варианты).
- `-20110` — нет прав на выдачу доступа к тесту.
- `-20111` — операция только для `ADMIN`.
- `-20112` — пользователь не найден.
- `-20113` — нельзя снять `ADMIN` с текущей учетной записи.
- `-20114` — категория используется вопросами.
- `-20115` — категория не найдена.
- `-20116` — тематика используется категориями/тестами.
- `-20117` — тематика не найдена.
- `-20118` — вопрос не найден.
- `-20119` — тест не найден.
- `-20120` — нельзя скрыть тест в текущем статусе.
- `-20121` — пользователь или тест не найден (сброс по тесту).
- `-20122` — пользователь не найден (полный сброс).
- `-20123` — вопрос не найден (update).
- `-20124` — недопустимый `timer_mode`.
- `-20125` — нет прав на удаление/управление тестом.
- `-20126` — нельзя удалить вопрос при активных попытках.
- `-20127` — некорректный `show_feedback`.
- `-20128` — менять `show_feedback` можно только в `DRAFT`.
- `-20129` — некорректный `attempt_limit` при создании теста.
- `-20130` — некорректный `attempt_limit` при обновлении.
- `-20131` — менять `attempt_limit` можно только в `DRAFT`.
- `-20132` — пароль должен содержать минимум 6 символов.
- `-20133` — нельзя удалить текущего администратора.
- `-20134` — нельзя удалить аккаунт с ролью `ADMIN`.
- `-20135` — флаг активности должен быть 0 или 1.
- `-20136` — нельзя отключить текущего администратора.
- `-20137` — нельзя отключить аккаунт с ролью `ADMIN`.

## 16.3. `pkg_testing`

- `-20200` — тест недоступен или не опубликован.
- `-20201` — опубликованный тест не содержит вопросов.
- `-20202` — попытка уже завершена.
- `-20203` — время теста/вопроса истекло.
- `-20204` — недопустимый формат выбранных option ID.
- `-20205` — некорректный набор вариантов/последовательности.
- `-20206` — вопрос не входит в текущую попытку.
- `-20207` — попытка не найдена.
- `-20208` — в режиме `QUESTION` нужно отвечать по порядку.
- `-20209` — для `ORDERING` не настроена корректная последовательность.
- `-20210` — `expire_question` доступен только для `QUESTION`.
- `-20211` — лимит попыток для теста исчерпан.
