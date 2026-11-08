"""User labels on TV artwork, and which label the slideshow is playing.

The TV has no custom categories, so a label slideshow is played through the TV's Favourites
list: the labelled artwork becomes exactly the favourites, and the slideshow runs on Favourites.
"""
import json
import threading
from pathlib import Path

LABELS_FILE = Path("/app/data/labels.json")
_lock = threading.Lock()


def _load() -> dict:
    try:
        data = json.loads(LABELS_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data.setdefault("labels", {})          # content_id -> [label, ...]
    data.setdefault("slideshow_label", None)
    return data


def _save(data: dict) -> None:
    tmp = LABELS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True))
    tmp.replace(LABELS_FILE)


def get_all() -> dict:
    return _load()["labels"]


def ids_with(label: str) -> set:
    return {cid for cid, labels in get_all().items() if label in labels}


def change(content_ids, add=(), remove=()) -> dict:
    add = [a.strip() for a in add if a and a.strip()]
    with _lock:
        data = _load()
        for cid in content_ids:
            current = [l for l in data["labels"].get(cid, []) if l not in remove]
            current += [a for a in add if a not in current]
            if current:
                data["labels"][cid] = sorted(current, key=str.lower)
            else:
                data["labels"].pop(cid, None)
        _save(data)
        return data["labels"]


def forget(content_ids) -> None:
    with _lock:
        data = _load()
        if any(data["labels"].pop(c, None) for c in list(content_ids)):
            _save(data)


def prune(live_ids: set) -> dict:
    with _lock:
        data = _load()
        live = {c: v for c, v in data["labels"].items() if c in live_ids}
        if len(live) != len(data["labels"]):
            data["labels"] = live
            _save(data)
        return live


def get_slideshow_label():
    return _load()["slideshow_label"]


def set_slideshow_label(label) -> None:
    with _lock:
        data = _load()
        data["slideshow_label"] = label
        _save(data)
