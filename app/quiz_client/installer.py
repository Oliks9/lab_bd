import re
import sys
from dataclasses import dataclass
from pathlib import Path

from .database import OracleGateway


@dataclass(frozen=True)
class InstallStep:
    file: str
    line: int
    sql: str = ""
    message: str = ""


def sql_directory():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "sql"
    return Path(__file__).resolve().parents[2] / "sql"


def installation_steps(root=None):
    root = Path(root or sql_directory()).resolve()
    steps = []

    def read(path, parents):
        path = path.resolve()
        if not path.is_relative_to(root) or path in parents:
            raise ValueError("Недопустимое или циклическое подключение SQL-файла.")
        relative = path.relative_to(root).as_posix()
        buffer, quote, block, start = "", "", False, 1
        for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            stripped = line.strip()
            if not buffer.strip():
                buffer = ""
                start = number
                if not stripped:
                    continue
                if stripped.startswith("@@"):
                    read(path.parent / stripped[2:].strip(), parents + (path,))
                    continue
                if stripped.upper().startswith("PROMPT "):
                    steps.append(InstallStep(relative, number, message=stripped[7:]))
                    continue
                if stripped.upper() in ("SET DEFINE OFF", "SET SERVEROUTPUT ON", "WHENEVER SQLERROR EXIT SQL.SQLCODE"):
                    continue
                if re.match(r"^(SET|WHENEVER|CONNECT|EXIT|SPOOL|HOST)\b|^@", stripped, re.I):
                    raise ValueError(f"{relative}:{number}: неподдерживаемая команда SQL*Plus.")
                block = bool(re.match(r"^(DECLARE|BEGIN|CREATE\s+(OR\s+REPLACE\s+)?(PACKAGE|PROCEDURE|FUNCTION|TRIGGER))\b", stripped, re.I))
            if block:
                if stripped == "/":
                    steps.append(InstallStep(relative, start, sql=buffer.strip()))
                    buffer, block = "", False
                else:
                    buffer += line + "\n"
                continue
            index = 0
            while index < len(line):
                char = line[index]
                if quote:
                    buffer += char
                    if char == quote:
                        if index + 1 < len(line) and line[index + 1] == quote:
                            buffer += char
                            index += 1
                        else:
                            quote = ""
                elif char in ("'", '"'):
                    quote = char
                    buffer += char
                elif char == ";":
                    if buffer.strip():
                        steps.append(InstallStep(relative, start, sql=buffer.strip()))
                    buffer = ""
                    start = number
                else:
                    buffer += char
                index += 1
            buffer += "\n"
        if buffer.strip() or quote or block:
            raise ValueError(f"{relative}:{start}: незавершённая SQL-команда.")

    read(root / "install.sql", ())
    if not any(step.sql for step in steps):
        raise ValueError("install.sql не содержит команд установки.")
    return steps


def check_install_permissions(connection, schema_user):
    with connection.cursor() as cursor:
        cursor.execute("SELECT SYS_CONTEXT('USERENV', 'SESSION_USER'), SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') FROM dual")
        session_user, current_schema = cursor.fetchone()
        if session_user != schema_user.upper() or current_schema != session_user or session_user in ("SYS", "SYSTEM", "PDBADMIN"):
            raise ValueError("Установка разрешена только в собственной обычной схеме с указанным именем пользователя.")
        cursor.execute("SELECT privilege FROM session_privs")
        privileges = {row[0] for row in cursor}
        required = {"CREATE SESSION", "CREATE TABLE", "CREATE SEQUENCE", "CREATE PROCEDURE", "CREATE TRIGGER"}
        missing = required - privileges
        if missing:
            raise ValueError("Недостаточно прав: " + ", ".join(sorted(missing)))
        cursor.execute("SELECT default_tablespace FROM user_users")
        tablespace = cursor.fetchone()[0]
        if "UNLIMITED TABLESPACE" not in privileges:
            cursor.execute("SELECT bytes, max_bytes FROM user_ts_quotas WHERE tablespace_name = :name", name=tablespace)
            quota = cursor.fetchone()
            if quota is None or (quota[1] != -1 and quota[1] <= quota[0]):
                raise ValueError("Нет свободной квоты в табличном пространстве " + tablespace + ". Обратитесь к администратору БД.")


def execute_installation(connection, steps, progress):
    with connection.cursor() as cursor:
        cursor.callproc("dbms_output.enable", [1000000])
        output_line = cursor.var(str, size=32767)
        output_status = cursor.var(int)
        total = sum(bool(step.sql) for step in steps)
        done = 0
        for step in steps:
            if step.message:
                progress(step.message, done, total)
                continue
            progress(f"{step.file}:{step.line}", done, total)
            try:
                cursor.execute(step.sql)
                if cursor.description:
                    for row in cursor:
                        progress(" | ".join(str(value) for value in row), done, total)
                while True:
                    cursor.callproc("dbms_output.get_line", [output_line, output_status])
                    if output_status.getvalue() != 0:
                        break
                    progress(output_line.getvalue() or "", done, total)
                done += 1
                progress(f"Выполнено {done} из {total}", done, total)
            except Exception as exc:
                connection.rollback()
                raise RuntimeError(f"{step.file}:{step.line}: {exc}\nУстановка остановлена. Уже выполненные DDL-команды не откатываются.") from exc
    connection.commit()


def install_database(dsn, schema_user, password, progress):
    steps = installation_steps()
    gateway = OracleGateway()
    try:
        progress("Проверка подключения и прав...", 0, 1)
        gateway.connect(dsn, schema_user, password)
        check_install_permissions(gateway.connection, schema_user)
        execute_installation(gateway.connection, steps, progress)
        progress("Установка завершена. Можно подключиться и войти в приложение.", 1, 1)
    finally:
        gateway.close()
