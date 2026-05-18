from __future__ import annotations

import os
import threading
from collections import deque
from datetime import datetime
from typing import Deque


LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "system.log")
MAX_ERRORS = 50

_errors: Deque[dict] = deque(maxlen=MAX_ERRORS)
_lock = threading.RLock()
_loaded_from_disk = False


def initialize_error_log(load_existing: bool = True) -> None:
    global _loaded_from_disk

    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8"):
            pass

        if load_existing and not _loaded_from_disk:
            with open(LOG_FILE, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()[-MAX_ERRORS:]

            parsed = [_parse_log_line(line.strip()) for line in lines if line.strip()]
            with _lock:
                _errors.clear()
                _errors.extend(record for record in parsed if record)
            _loaded_from_disk = True
    except Exception:
        pass


def _normalise_module(module: str) -> str:
    name = (module or "SYSTEM_ERROR").strip().upper()
    if not name.endswith("_ERROR"):
        name = f"{name}_ERROR"
    return name


def _parse_log_line(line: str) -> dict | None:
    try:
        timestamp, module, payload, severity = [part.strip() for part in line.split("|", 3)]
        error_type, message = payload.split(":", 1) if ":" in payload else ("Error", payload)
        return {
            "timestamp": timestamp,
            "module": _normalise_module(module),
            "category": _normalise_module(module).replace("_ERROR", "").lower(),
            "error_type": error_type.strip(),
            "message": message.strip(),
            "severity": severity.strip().upper(),
            "line": line,
        }
    except Exception:
        return None


def log_error(module: str, error: Exception, severity: str = "ERROR") -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    module_name = _normalise_module(module)
    error_type = type(error).__name__
    message = str(error) or error_type
    severity_name = (severity or "ERROR").strip().upper()
    line = f"{timestamp} | {module_name} | {error_type}: {message} | {severity_name}"

    record = {
        "timestamp": timestamp,
        "module": module_name,
        "category": module_name.replace("_ERROR", "").lower(),
        "error_type": error_type,
        "message": message,
        "severity": severity_name,
        "line": line,
    }

    with _lock:
        _errors.append(record)
        try:
            initialize_error_log(load_existing=False)
            with open(LOG_FILE, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except Exception:
            pass


def get_recent_errors() -> list[dict]:
    with _lock:
        return list(_errors)
