# Oracle Quiz Platform

Учебная платформа для онлайн-квизов и тестирования, где основная бизнес-логика реализована в Oracle (SQL/PLSQL), а Python/Tkinter используется как GUI-клиент.

## Ключевые возможности

- Регистрация и вход по логину и паролю.
- Роли `USER`, `AUTHOR`, `ADMIN`.
- Начальная учетная запись: `admin / Admin123!`.
- Создание тематик, категорий, тестов и вопросов.
- Шесть типов вопросов: `SINGLE_CHOICE`, `MULTIPLE_CHOICE`, `TEXT`, `NUMBER`, `BOOLEAN`, `ORDERING`.
- Два режима таймера:
  - `QUIZ`: ограничение на весь тест.
  - `QUESTION`: ограничение на каждый вопрос с автопереходом к следующему.
- Показ правильных ответов и пояснений автора в результатах (если у теста включен `show_feedback`).
- Редактирование вопросов черновика.
- Публикация тестов и выдача доступа к закрытым тестам.
- Возврат опубликованного теста обратно в черновик (кнопка «Скрыть в черновик»).
- Удаление тестов и вопросов автором своего теста или администратором.
- При удалении теста удаляются его попытки (статистика по тесту сбрасывается).
- При удалении вопроса пересчитываются `seq_no`, `display_order` и агрегаты попыток для оставшихся вопросов.
- Администрирование пользователей, ролей и прогресса (сброс попыток по одному тесту или полностью по пользователю).

## Архитектура

- Oracle-слой:
  - таблицы, ограничения, триггеры;
  - функции и процедуры авторизации;
  - пакеты `pkg_admin` и `pkg_testing`;
  - представления отчетности и статистики.
- Python-слой:
  - окна подключения, входа и регистрации;
  - пользовательские экраны прохождения тестов;
  - экран автора для управления контентом;
  - экран администратора для пользователей, ролей и сброса прогресса.
- Принцип: критичные правила не дублируются в GUI, а исполняются в Oracle.

## Быстрый запуск через Docker

```powershell
powershell -ExecutionPolicy Bypass -File .\docker\start.ps1
powershell -ExecutionPolicy Bypass -File .\docker\check.ps1
```

Обновление существующей базы без потери пользователей и попыток:

```powershell
powershell -ExecutionPolicy Bypass -File .\docker\upgrade.ps1
```

Полная переинициализация учебной базы:

```powershell
$env:DOCKER_CONFIG="$PWD\.docker-config"
docker compose down -v
powershell -ExecutionPolicy Bypass -File .\docker\start.ps1
```

Параметры подключения для GUI/EXE по умолчанию:

```text
DSN:              localhost:1521/FREEPDB1
Пользователь БД:  quiz_app
Пароль БД:        QuizSchema2026
```

## Запуск и сборка приложения

Запуск из исходников:

```powershell
.\.venv\Scripts\python.exe .\app\quiz_app.py
```

Сборка EXE:

```powershell
powershell -ExecutionPolicy Bypass -File .\build\build_exe.ps1 -Python .\.venv\Scripts\python.exe
```

Результат сборки:

- `dist\OracleQuizPlatform.exe`

Проверка подключения EXE в headless-режиме:

```powershell
.\dist\OracleQuizPlatform.exe --connection-check "localhost:1521/FREEPDB1" "quiz_app" "QuizSchema2026" "admin" "Admin123!"
$LASTEXITCODE
```

Код `0` означает успешное подключение и вход.

## Ручная установка SQL (без Docker)

```powershell
Set-Location C:\Users\Oliks9\Documents\lb\oracle_quiz_app\sql
sqlplus quiz_app/QuizSchema2026@//localhost:1521/FREEPDB1 "@install.sql"
sqlplus quiz_app/QuizSchema2026@//localhost:1521/FREEPDB1 "@tests/check_invalid_objects.sql"
sqlplus quiz_app/QuizSchema2026@//localhost:1521/FREEPDB1 "@tests/timezone_smoke_test.sql"
sqlplus quiz_app/QuizSchema2026@//localhost:1521/FREEPDB1 "@tests/auth_smoke_test.sql"
sqlplus quiz_app/QuizSchema2026@//localhost:1521/FREEPDB1 "@tests/content_management_smoke_test.sql"
sqlplus quiz_app/QuizSchema2026@//localhost:1521/FREEPDB1 "@tests/smoke_test.sql"
```

## Структура проекта

```text
oracle_quiz_app/
  app/
    quiz_app.py
    quiz_client/
      config.py
      database.py
      theme.py
      ui.py
  build/
    build_exe.ps1
  docker/
    start.ps1
    upgrade.ps1
    check.ps1
    init/
  docs/
  sql/
    install.sql
    00_uninstall.sql
    01_tables/
    02_functions/
    03_procedures/
    04_triggers/
    05_packages/
    06_views/
    07_seed/
    08_migrations/
    tests/
  compose.yaml
  README.md
```

## Документация

- [01_project_completion_report.md](docs/01_project_completion_report.md)
- [02_database_logic_map.md](docs/02_database_logic_map.md)
- [03_validation_and_demo_scenarios.md](docs/03_validation_and_demo_scenarios.md)
- [04_role_matrix_and_permissions.md](docs/04_role_matrix_and_permissions.md)
- [05_release_notes.md](docs/05_release_notes.md)
