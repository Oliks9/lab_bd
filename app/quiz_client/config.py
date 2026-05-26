import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


APP_NAME = "OracleQuizPlatform"


@dataclass
class ConnectionSettings:
    dsn: str = "localhost:1521/FREEPDB1"
    schema_user: str = "quiz_app"


def settings_path() -> Path:
    root = Path(os.getenv("APPDATA", Path.home()))
    return root / APP_NAME / "connection.json"


def load_settings() -> ConnectionSettings:
    path = settings_path()
    if not path.exists():
        return ConnectionSettings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return ConnectionSettings(
            dsn=data.get("dsn", ConnectionSettings.dsn),
            schema_user=data.get("schema_user", ConnectionSettings.schema_user),
        )
    except (OSError, ValueError):
        return ConnectionSettings()


def save_settings(settings: ConnectionSettings) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8")
