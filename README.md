# Oracle Quiz Platform

Полноценное настольное приложение для онлайн-тестирования по курсовой работе. Бизнес-правила исполняются в Oracle PL/SQL; Python/Tkinter отвечает за окна и вызовы БД.

## Возможности

- Регистрация и вход пользователей приложения по логину и паролю.
- Роли `USER`, `AUTHOR`, `ADMIN`; стартовая учетная запись только одна: `admin`.
- Тематики, категории, сложность и шесть типов вопросов: один ответ, несколько ответов, текст, число, истина/ложь, упорядочивание.
- Публичные и закрытые тесты, выдача доступа зарегистрированным пользователям.
- Таймер попытки с учетом часовых поясов, проверка ответов и расчет баллов в Oracle.
- История попыток, обратная связь, статистика вопросов и средний результат.
- Рабочая студия автора: тематики, категории, отдельные шаги создания теста и наполнения вопросами.
- Редактирование вопросов черновика и динамические поля ответа в зависимости от выбранного типа вопроса.
- Панель администратора для создания авторов, назначения ролей, удаления чернового контента и архивирования опубликованных тестов.
- Отдельное управление прогрессом: сброс попыток пользователя по одному тесту или полной истории без удаления аккаунта.
- Новые категории сразу доступны в конструкторе вопросов без повторного входа.

## Быстрый запуск через Docker

Docker-контур поднимает Oracle Database Free и при первом создании контейнера автоматически создает схему, устанавливает PL/SQL-модули и запускает smoke-test:

```powershell
powershell -ExecutionPolicy Bypass -File .\docker\start.ps1
powershell -ExecutionPolicy Bypass -File .\docker\check.ps1
```

Для EXE используются параметры:

```text
DSN:              localhost:1521/FREEPDB1
Пользователь БД:  quiz_app
Пароль БД:        QuizSchema2026
```

Файлы Docker:

- [compose.yaml](compose.yaml) — контейнер Oracle Free и volume данных.
- [001_install_quiz_application.sql](docker/init/001_install_quiz_application.sql) — автоматическое создание схемы и установка проекта.
- [reinstall.ps1](docker/reinstall.ps1) — повторная установка SQL-объектов после изменений.
- [upgrade.ps1](docker/upgrade.ps1) — безопасное обновление уже заполненной базы без удаления пользователей и попыток.
- [check.ps1](docker/check.ps1) — проверка компиляции объектов, часового пояса, регистрации/входа и всех типов вопросов.

Если контейнер уже использовался, применяйте обновление с сохранением данных:

```powershell
powershell -ExecutionPolicy Bypass -File .\docker\upgrade.ps1
```

При необходимости полностью очистить учебную базу и выполнить первичную инициализацию заново:

```powershell
$env:DOCKER_CONFIG="$PWD\.docker-config"
docker compose down -v
powershell -ExecutionPolicy Bypass -File .\docker\start.ps1
```

## Структура

```text
oracle_quiz_app/
  compose.yaml                    # Oracle Free в Docker
  docker/                         # автозапуск установки и проверки контейнера
  app/
    quiz_app.py                  # точка запуска GUI
    quiz_client/
      config.py                  # настройки соединения
      database.py                # тонкий клиент PL/SQL/SQL
      theme.py                   # оформление
      ui.py                      # экраны приложения
  sql/
    install.sql                  # главный установочный сценарий
    00_uninstall.sql
    01_tables/                   # таблицы и индексы
    02_functions/                # хэширование, доступ, процент
    03_procedures/               # регистрация и вход
    04_triggers/                 # контроль данных и аудит
    05_packages/                 # администрирование и прохождение
    06_views/                    # отчеты и статистика
    07_seed/                     # справочники, admin и демо-тест
    08_migrations/               # обновления существующей базы без потери данных
    tests/smoke_test.sql
  build/build_exe.ps1
  dist/                          # собранный EXE
  reference/                     # исходный шаблон оформления
```

## Установка Oracle

Для новой схемы можно выполнить под пользователем DBA пример [create_schema_example.sql](sql/create_schema_example.sql), предварительно сменив пароль. При ручной установке запускайте `SQL*Plus` из каталога `sql`, чтобы вложенные сценарии разрешались относительно этого каталога:

```powershell
Set-Location C:\Users\Oliks9\Documents\lb\oracle_quiz_app\sql
sqlplus quiz_app/QuizSchema2026@//localhost:1521/FREEPDB1 "@install.sql"
sqlplus quiz_app/QuizSchema2026@//localhost:1521/FREEPDB1 "@tests/check_invalid_objects.sql"
sqlplus quiz_app/QuizSchema2026@//localhost:1521/FREEPDB1 "@tests/timezone_smoke_test.sql"
sqlplus quiz_app/QuizSchema2026@//localhost:1521/FREEPDB1 "@tests/auth_smoke_test.sql"
sqlplus quiz_app/QuizSchema2026@//localhost:1521/FREEPDB1 "@tests/content_management_smoke_test.sql"
sqlplus quiz_app/QuizSchema2026@//localhost:1521/FREEPDB1 "@tests/smoke_test.sql"
```

Начальные учетные данные внутри приложения:

```text
Логин:  admin
Пароль: Admin123!
```

Они созданы в [02_admin_and_demo_quiz.sql](sql/07_seed/02_admin_and_demo_quiz.sql). В учебной демонстрации пароль видим в seed-скрипте; при развертывании его следует заменить.

## Запуск EXE

Запустите `dist\OracleQuizPlatform.exe`. На первом экране вводятся параметры технической схемы Oracle:

```text
DSN:              localhost:1521/FREEPDB1
Пользователь БД:  quiz_app
Пароль БД:        пароль схемы Oracle
```

После подключения приложение показывает обычный экран входа/регистрации пользователей платформы. Для проверки нужен запущенный Oracle с выполненным `install.sql`: EXE является клиентом и не содержит встроенную БД.

## Где находится логика БД

- [pr_register_user.sql](sql/03_procedures/pr_register_user.sql) и [pr_login.sql](sql/03_procedures/pr_login.sql) создают и аутентифицируют учетные записи.
- [pkg_admin.pkb](sql/05_packages/pkg_admin.pkb) разрешает авторам добавлять материалы, создает тесты и вопросы, валидирует публикацию и выполняет защищенное администраторское удаление.
- [pkg_testing.pkb](sql/05_packages/pkg_testing.pkb) создает попытки, принимает ответы, проверяет их и завершает тест.
- [trg_audit.sql](sql/04_triggers/trg_audit.sql) и остальные триггеры контролируют изменения и журналируют события.
- [01_views.sql](sql/06_views/01_views.sql) предоставляет историю, детализацию, статистику и рейтинг.

## Сборка EXE

```powershell
powershell -ExecutionPolicy Bypass -File .\build\build_exe.ps1 -Python python
```

Сценарий устанавливает `oracledb` и `PyInstaller`, затем создает `dist\OracleQuizPlatform.exe`.

Проверка соединения у собранного EXE без открытия окон:

```powershell
.\dist\OracleQuizPlatform.exe --connection-check "localhost:1521/FREEPDB1" "quiz_app" "QuizSchema2026" "admin" "Admin123!"
$LASTEXITCODE
```

Код `0` означает, что упакованный клиент подключился к Oracle и выполнил вход пользователя приложения.
