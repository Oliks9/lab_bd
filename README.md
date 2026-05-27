# Oracle Quiz Platform

Платформа онлайн-тестирования, где ключевая логика реализована в Oracle (SQL/PLSQL), а Python (Tkinter) используется как GUI-клиент.

## Ключевая идея

- Oracle отвечает за бизнес-логику: права, валидацию, таймеры, оценивание, публикацию, удаление, ограничения целостности.
- Python не дублирует критичные правила, а вызывает процедуры/пакеты Oracle и показывает результат пользователю.

## Основные возможности

- Регистрация и вход по логину/паролю.
- Роли: `USER`, `AUTHOR`, `ADMIN`.
- Управление тематиками, категориями, тестами, вопросами, вариантами ответов.
- Типы вопросов: `SINGLE_CHOICE`, `MULTIPLE_CHOICE`, `TEXT`, `NUMBER`, `BOOLEAN`, `ORDERING`.
- Таймер: на весь тест (`QUIZ`) или на каждый вопрос (`QUESTION`).
- Автопереход на следующий вопрос по таймауту в режиме `QUESTION`.
- Публикация и возврат теста в черновик.
- Ограничение числа попыток на пользователя (`attempt_limit`).
- Настройка показа правильных ответов и пояснений (`show_feedback`).
- Удаление тестов/вопросов с пересчетом связанных данных.
- Админ-функции: создание авторов, роли, смена пароля пользователя, удаление пользователя, сброс прогресса.
- Админ-функции: создание авторов, роли, смена пароля пользователя, отключение/включение аккаунта, удаление пользователя, сброс прогресса.

## Дефолтный администратор

- `admin / Admin123!`

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
    00_uninstall.sql
    install.sql
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
  requirements.txt
```

## Быстрый старт через Docker

```powershell
powershell -ExecutionPolicy Bypass -File .\docker\start.ps1
powershell -ExecutionPolicy Bypass -File .\docker\check.ps1
```

Обновление схемы без удаления данных:

```powershell
powershell -ExecutionPolicy Bypass -File .\docker\upgrade.ps1
```

Полная переинициализация (удаляет данные):

```powershell
$env:DOCKER_CONFIG="$PWD\.docker-config"
docker compose down -v
powershell -ExecutionPolicy Bypass -File .\docker\start.ps1
```

## Подключение к БД

```text
DSN: localhost:1521/FREEPDB1
Schema user: quiz_app
Schema password: QuizSchema2026
```

## Запуск из исходников

```powershell
.\.venv\Scripts\python.exe .\app\quiz_app.py
```

## Сборка EXE

```powershell
powershell -ExecutionPolicy Bypass -File .\build\build_exe.ps1 -Python .\.venv\Scripts\python.exe
```

Артефакт:

- `dist\OracleQuizPlatform.exe`

Проверка подключения в headless-режиме:

```powershell
.\dist\OracleQuizPlatform.exe --connection-check "localhost:1521/FREEPDB1" "quiz_app" "QuizSchema2026" "admin" "Admin123!"
$LASTEXITCODE
```

`0` означает успешное подключение и вход.

## Полная документация

- `docs/01_project_completion_report.md` — итог по реализации и архитектуре.
- `docs/02_database_logic_map.md` — полный reference по Oracle-слою:
  - все таблицы и поля;
  - PK/FK/UNIQUE/CHECK и каскады;
  - индексы;
  - функции и процедуры;
  - пакеты `pkg_admin`, `pkg_testing` (сигнатуры, проверки, эффекты);
  - триггеры, представления, миграции, smoke-тесты.
- `docs/03_validation_and_demo_scenarios.md` — сценарии проверки и демонстрации на защите.
- `docs/04_role_matrix_and_permissions.md` — матрица прав и привязка к конкретным процедурам.
- `docs/05_release_notes.md` — журнал изменений по версиям.
