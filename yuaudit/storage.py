from __future__ import annotations
import json
import logging
import os
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path
from .models import Result


def data_dir() -> Path:
    root = Path(os.environ.get("YUAUDIT_DATA_DIR") or Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "YuAudit")
    root.mkdir(parents=True, exist_ok=True)
    return root


def configure_logging():
    handler = RotatingFileHandler(data_dir() / "application.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger("yuaudit").addHandler(handler)
    logging.getLogger("yuaudit").setLevel(logging.INFO)


def save_json(name: str, data: dict):
    target = data_dir() / name
    fd, temp = tempfile.mkstemp(dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def load_json(name: str) -> dict:
    try:
        return json.loads((data_dir() / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_session(result: Result):
    save_json("last-session.json", result.model_dump(mode="json"))


def load_session() -> Result | None:
    data = load_json("last-session.json")
    return Result.model_validate(data) if data else None
