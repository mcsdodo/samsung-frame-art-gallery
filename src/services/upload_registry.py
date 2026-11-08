"""Remembers which local file each TV artwork came from; the TV itself only knows its own ids."""
import json
import threading
import time
from pathlib import Path

REGISTRY_FILE = Path("/app/data/uploads.json")
_lock = threading.Lock()


def load() -> dict:
    """content_id -> {"path": str, "uploaded_at": float}"""
    try:
        return json.loads(REGISTRY_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    tmp = REGISTRY_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True))
    tmp.replace(REGISTRY_FILE)


def record(content_id: str, path: str) -> None:
    with _lock:
        data = load()
        data[content_id] = {"path": path, "uploaded_at": time.time()}
        _save(data)


def forget(content_ids) -> None:
    with _lock:
        data = load()
        if any(data.pop(c, None) for c in list(content_ids)):
            _save(data)


def prune(live_ids: set) -> dict:
    """Drop entries whose artwork was deleted on the TV itself; returns what is left."""
    with _lock:
        data = load()
        live = {c: v for c, v in data.items() if c in live_ids}
        if len(live) != len(data):
            _save(live)
        return live
