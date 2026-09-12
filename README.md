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
      diagnostics.py
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

## Подбор вопросов по параметрам

В студии откройте вкладку **Подбор**, выберите черновик и режим «Случайные N по категории и сложности».
Укажите категорию, сложность и количество, нажмите **Сохранить подбор**, затем публикуйте тест.
Источник: только вопросы выбранного теста. Oracle выбирает ровно N вопросов без повторов
при каждой новой попытке; набор и порядок сохраняются в `attempt_questions`.
По умолчанию используются все вопросы по порядку. [Подробное описание](docs/07_question_selection.md).

## Обновление установленной схемы

Закройте клиент перед обновлением и сделайте резервную копию схемы.
В Docker выполните `powershell -ExecutionPolicy Bypass -File .\docker\upgrade.ps1`.
На учебном сервере откройте **файл** `sql/upgrade_question_selection.sql` в SQL Developer,
выберите подключение своего пользователя БД и запустите F5. Папка `sql` должна быть перенесена целиком:
скрипт использует относительные `@@`-подключения. Он рассчитан на актуальную установленную версию проекта
(с режимами таймера и лимитом попыток), добавляет поля подбора, пересоздаёт пакеты и все представления,
включая сравнение результатов. SYS и создание пользователя не нужны.
Затем запустите `sql/tests/question_selection_smoke_test.sql` и `sql/tests/comparison_smoke_test.sql`
через F5 и замените EXE. Пароли, тесты и результаты не сбрасываются.
`sql/install.sql` повторно не запускайте: это установка с удалением данных приложения.

## Запуск из исходников

```powershell
.\.venv\Scripts\python.exe .\app\quiz_app.py
```

## Сборка EXE

На новом компьютере создайте отдельное окружение из установленного Python
(проверено на Python 3.12 x64). Команды выполняются из корня проекта:

```powershell
python -m venv .venv
powershell -ExecutionPolicy Bypass -File .\build\build_exe.ps1 -Python .\.venv\Scripts\python.exe
```

Если `.venv` уже создана на этом компьютере, первая команда не нужна.
Не переносите `.venv` с другой машины. Скрипт устанавливает зависимости в выбранный
Python, проверяет их импорт, собирает EXE и проверяет зависимости внутри него.
Успешное окончание: `EXE verified`. При ошибке не используйте оставшийся старый EXE.

Артефакт: `dist\OracleQuizPlatform.exe`. Отчёты: `build\pyinstaller\source-check-*.json`
и `build\pyinstaller\exe-check-*.json`.

Проверка нового EXE на другом компьютере без подключения к Oracle:

```powershell
$report = Join-Path $PWD ('dependency-check-' + [guid]::NewGuid().ToString('N') + '.json')
$process = Start-Process -FilePath .\dist\OracleQuizPlatform.exe -ArgumentList @('--self-check', ('"{0}"' -f $report)) -WindowStyle Hidden -Wait -PassThru
$process.ExitCode
Get-Content -LiteralPath $report -Raw -Encoding UTF8
```

`0` означает успешную проверку зависимостей, но не доступность БД.
Режим `--connection-check DSN SCHEMA_USER SCHEMA_PASSWORD LOGIN PASSWORD` также сохранён;
он действительно подключается и выполняет вход (включая серверные действия `pr_login`).
Не публикуйте команды с действующими паролями. Для оконного EXE ожидайте завершения
через `Start-Process -Wait -PassThru` и читайте `ExitCode`, а не старый `$LASTEXITCODE`.

Подробные шаги для удалённого Windows, ошибки импорта и состав переносимых файлов:
[Сборка и диагностика зависимостей](docs/08_build_and_dependencies.md).

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
- `docs/07_question_selection.md` — подбор N вопросов выбранного теста по категории и сложности.
- `docs/08_build_and_dependencies.md` — сборка EXE на Windows и диагностика зависимостей без подключения к БД.
