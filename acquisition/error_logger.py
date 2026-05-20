from __future__ import annotations

import os
import json
import threading
import traceback
from collections import deque
from datetime import datetime, timezone
from typing import Deque


LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "system.log")
HARDWARE_LOG_FILE = os.path.join(LOG_DIR, "hardware_log.jsonl")
ERROR_KNOWLEDGE_FILE = os.path.join(LOG_DIR, "error_knowledge_base.md")
MAX_ERRORS = 50
MAX_HARDWARE_EVENTS = 250

_errors: Deque[dict] = deque(maxlen=MAX_ERRORS)
_hardware_events: Deque[dict] = deque(maxlen=MAX_HARDWARE_EVENTS)
_lock = threading.RLock()
_loaded_from_disk = False
_hardware_loaded_from_disk = False


def initialize_error_log(load_existing: bool = True) -> None:
    global _loaded_from_disk, _hardware_loaded_from_disk

    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8"):
            pass
        with open(HARDWARE_LOG_FILE, "a", encoding="utf-8"):
            pass
        if not os.path.isfile(ERROR_KNOWLEDGE_FILE):
            with open(ERROR_KNOWLEDGE_FILE, "w", encoding="utf-8") as fh:
                fh.write(
                    "# HSI-Core Error Knowledge Base\n\n"
                    "This file is updated automatically whenever the app records a system, camera, stage, scan, upload, or UI error.\n\n"
                    "| Time | Module | Severity | Type/Code | Message | Likely Action |\n"
                    "| --- | --- | --- | --- | --- | --- |\n"
                )

        if load_existing and not _loaded_from_disk:
            with open(LOG_FILE, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()[-MAX_ERRORS:]

            parsed = [_parse_log_line(line.strip()) for line in lines if line.strip()]
            with _lock:
                _errors.clear()
                _errors.extend(record for record in parsed if record)
            _loaded_from_disk = True

        if load_existing and not _hardware_loaded_from_disk:
            with open(HARDWARE_LOG_FILE, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()[-MAX_HARDWARE_EVENTS:]
            parsed_events = []
            for line in lines:
                try:
                    parsed_events.append(json.loads(line))
                except Exception:
                    continue
            with _lock:
                _hardware_events.clear()
                _hardware_events.extend(parsed_events)
            _hardware_loaded_from_disk = True
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
            _append_error_knowledge(timestamp, module_name, severity_name, error_type, message)
        except Exception:
            pass


def log_hardware_event(
    module: str,
    message: str,
    error: Exception | None = None,
    error_code: str = "",
    severity: str = "ERROR",
    extra: dict | None = None,
) -> None:
    """Persist a structured hardware diagnostic record as JSONL."""

    timestamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")
    module_name = (module or "system").strip().lower()
    severity_name = (severity or "ERROR").strip().upper()
    friendly = message or (str(error) if error else "Hardware event")
    record = {
        "timestamp": timestamp,
        "module": module_name,
        "error_code": error_code or (type(error).__name__ if error else ""),
        "message": friendly,
        "severity": severity_name,
        "trace": "".join(traceback.format_exception(type(error), error, error.__traceback__)) if error else "",
        "extra": extra or {},
    }

    with _lock:
        _hardware_events.append(record)
        try:
            initialize_error_log(load_existing=False)
            with open(HARDWARE_LOG_FILE, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            _append_error_knowledge(
                timestamp,
                f"{module_name.upper()}_EVENT",
                severity_name,
                error_code or (type(error).__name__ if error else "EVENT"),
                friendly,
            )
        except Exception:
            pass

    if severity_name in {"ERROR", "CRITICAL"}:
        log_error(f"{module_name.upper()}_ERROR", RuntimeError(friendly), severity=severity_name)


def get_recent_errors() -> list[dict]:
    with _lock:
        return list(_errors)


def get_latest_hardware_events(limit: int = 50) -> list[dict]:
    initialize_error_log(load_existing=True)
    with _lock:
        return list(_hardware_events)[-max(1, int(limit)):]


def get_hardware_errors(limit: int = 50) -> list[dict]:
    initialize_error_log(load_existing=True)
    with _lock:
        events = [
            event for event in _hardware_events
            if str(event.get("severity", "")).upper() in {"ERROR", "CRITICAL"}
        ]
    return events[-max(1, int(limit)):]


def _append_error_knowledge(timestamp: str, module: str, severity: str, code: str, message: str) -> None:
    safe = lambda value: str(value).replace("|", "\\|").replace("\n", " ").strip()
    action = _suggest_action(module, message)
    with open(ERROR_KNOWLEDGE_FILE, "a", encoding="utf-8") as fh:
        fh.write(
            f"| {safe(timestamp)} | {safe(module)} | {safe(severity)} | "
            f"{safe(code)} | {safe(message)} | {safe(action)} |\n"
        )


def _suggest_action(module: str, message: str) -> str:
    text = f"{module} {message}".lower()
    if "camera" in text and ("busy" in text or "exclusively" in text or "lock" in text):
        return "Close other camera apps/old servers, then press Detect Hardware."
    if "camera" in text:
        return "Check Basler connection, exposure/gain limits, and press Start Stream or Detect Hardware."
    if "stage" in text and "outside limits" in text:
        return "Reduce start/end/goto position inside configured stage travel."
    if "stage" in text:
        return "Check Thorlabs power/USB/Kinesis, then press Detect Hardware or Home Stage."
    if "scan" in text:
        return "Review scan parameters, camera stream, and last failed image index."
    if "upload" in text:
        return "Check file format, size, and ENVI/TIFF metadata."
    if "ui" in text:
        return "Refresh the browser and check the latest UI action."
    return "Inspect logs/hardware_log.jsonl and repeat the operation after correcting the cause."
