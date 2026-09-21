import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path


APP_NAME = "OracleQuizPlatform"


@dataclass
class ConnectionSettings:
    dsn: str = "localhost:1521/FREEPDB1"
    schema_user: str = "quiz_app"


@dataclass
class OracleAddress:
    host: str = "localhost"
    port: int = 1521
    database: str = "FREEPDB1"
    mode: str = "SERVICE_NAME"


def build_connection_dsn(host: str, port: str, database: str, mode: str) -> str:
    host = host.strip()
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    if not re.fullmatch(r"[A-Za-z0-9_.:%-]+", host):
        raise ValueError("Укажите адрес сервера без пробелов, скобок и строки подключения.")
    if not port.strip().isascii() or not port.strip().isdecimal() or not 1 <= int(port) <= 65535:
        raise ValueError("Порт должен быть целым числом от 1 до 65535.")
    database = database.strip()
    if mode not in ("SID", "SERVICE_NAME") or not re.fullmatch(r"[A-Za-z0-9_.$#-]+", database):
        raise ValueError("Укажите корректный SID или имя службы Oracle.")
    return f"(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST={host})(PORT={int(port)}))(CONNECT_DATA=({mode}={database})))"


def parse_connection_dsn(dsn: str) -> OracleAddress | None:
    compact = re.sub(r"\s*([()=])\s*", r"\1", dsn.strip())
    descriptor = re.fullmatch(
        r"\(DESCRIPTION=\(ADDRESS=\(PROTOCOL=TCP\)\(HOST=([^()=]+)\)\(PORT=([0-9]+)\)\)"
        r"\(CONNECT_DATA=\((SID|SERVICE_NAME)=([^()=]+)\)\)\)", compact, re.IGNORECASE,
    )
    if descriptor:
        host, port, mode, database = descriptor.groups()
    else:
        easy = re.fullmatch(r"(?://)?(\[[0-9A-Fa-f:.%]+\]|[^:/\s()=]+)(?::([0-9]+))?/([A-Za-z0-9_.$#-]+)", dsn.strip())
        if not easy:
            return None
        host, port, database = easy.groups()
        port, mode = port or "1521", "SERVICE_NAME"
    try:
        build_connection_dsn(host, port, database, mode.upper())
    except ValueError:
        return None
    return OracleAddress(host, int(port), database, mode.upper())


def connection_label(dsn: str) -> str:
    address = parse_connection_dsn(dsn)
    if address is None:
        return "расширенное подключение"
    kind = "SID" if address.mode == "SID" else "служба"
    return f"{address.host}:{address.port}, {kind}: {address.database}"


def settings_path() -> Path:
    root = Path(os.getenv("APPDATA", Path.home()))
    return root / APP_NAME / "connection.json"


def load_settings() -> ConnectionSettings:
    path = settings_path()
    if not path.exists():
        return ConnectionSettings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return ConnectionSettings()
        return ConnectionSettings(
            dsn=data["dsn"] if isinstance(data.get("dsn"), str) and data["dsn"].strip() else ConnectionSettings.dsn,
            schema_user=data["schema_user"] if isinstance(data.get("schema_user"), str) and data["schema_user"].strip() else ConnectionSettings.schema_user,
        )
    except (OSError, ValueError):
        return ConnectionSettings()


def save_settings(settings: ConnectionSettings) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8")
