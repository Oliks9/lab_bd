# Oracle Quiz Platform

Платформа онлайн-тестирования, где ключевая логика реализована в Oracle (SQL/PLSQL), а Python (Tkinter) используется как GUI-клиент.

## Ключевая идея

- Oracle отвечает за бизнес-логику: права, валидацию, таймеры, оценивание, публикацию, удаление, ограничения целостности.
- Python отображает формы, проверяет ввод и вызывает API Oracle. Оценивание, ограничения и изменения данных выполняются в БД; SQL-запросы из `database.py` тоже исполняются сервером Oracle.

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
- Сравнение результата попытки со средним по завершённым и прерванным попыткам других участников этого теста: средний процент, разница в процентных пунктах, размер выборки. Расчёт выполняется в Oracle.
- Удаление тестов/вопросов с пересчетом связанных данных.
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
Schema password: P@ssw0rd
```

Если Docker-том создан со старым паролем схемы, один раз выполните смену пароля,
затем обновите модули. Данные сохраняются:

```powershell
powershell -ExecutionPolicy Bypass -File .\docker\change_schema_password.ps1
powershell -ExecutionPolicy Bypass -File .\docker\upgrade.ps1
```

Скрипт меняет только пароль Oracle-схемы `quiz_app`. Пароли пользователей приложения
хранятся отдельно в `app_users`; существующий пароль администратора не сбрасывается.
`admin / Admin123!` выше относится к новой установке. Для существующей базы используйте
пароль администратора, который установили ранее.

## Обновление сравнения результатов

При обновлении уже установленной схемы на учебном сервере для функции сравнения
выполните `sql/06_views/01_views.sql` под своим пользователем через F5 в SQL Developer,
затем `sql/tests/comparison_smoke_test.sql` и замените EXE. `sql/install.sql` повторно
запускать не нужно: он удаляет данные приложения. В Docker используйте `docker/upgrade.ps1`.

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
.\dist\OracleQuizPlatform.exe --connection-check "localhost:1521/FREEPDB1" "quiz_app" "P@ssw0rd" "admin" "Admin123!"
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
- `docs/06_oracle_logic_audit.md` — распределение логики между Oracle и Python, исправления и границы архитектуры.
