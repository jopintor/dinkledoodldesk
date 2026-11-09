"""Exact-match response cache for generated KB answers (docs/architecture.md §5.2 step 2).

Key = SHA-256 of the normalised question + role + kb_version + prompt_version, so any KB
or prompt change invalidates it. Stored in a JSON file so answers warmed before the demo
(`scripts/warm_cache.py`) survive a restart. Only history-free, PII-free generated answers
are cached; the service decides that.

TODO: move to the `response_cache` table (docs/database.md) once the models land.
"""

import hashlib
import json
import logging
import os
import re
import threading
import time
from collections.abc import Callable
from pathlib import Path

log = logging.getLogger(__name__)

_SPACES = re.compile(r"\s+")


def cache_key(question: str, role: str, kb_version: str, prompt_version: str) -> str:
    normalised = _SPACES.sub(" ", question.strip().lower()).rstrip(" ?!.")
    raw = "\x1f".join([normalised, role, kb_version, prompt_version])
    return hashlib.sha256(raw.encode()).hexdigest()


class ResponseCache:
    def __init__(
        self,
        path: str | Path | None,
        ttl_s: float,
        *,
        wall: Callable[[], float] = time.time,
    ) -> None:
        self._path = Path(path) if path else None
        self._ttl = ttl_s
        self._wall = wall
        self._lock = threading.Lock()
        self._entries: dict[str, dict] | None = None

    def _load(self) -> dict[str, dict]:
        if self._entries is None:
            self._entries = {}
            if self._path and self._path.exists():
                try:
                    self._entries = json.loads(self._path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    log.warning("ignoring unreadable response cache %s", self._path)
        return self._entries

    def get(self, key: str) -> dict | None:
        with self._lock:
            entry = self._load().get(key)
            if entry is None or self._wall() - entry["stored_at"] > self._ttl:
                return None
            return entry["value"]

    def put(self, key: str, value: dict) -> None:
        with self._lock:
            entries = self._load()
            now = self._wall()
            entries[key] = {"stored_at": now, "value": value}
            for stale in [k for k, e in entries.items() if now - e["stored_at"] > self._ttl]:
                del entries[stale]
            if self._path is None:
                return
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self._path.with_suffix(".tmp")
                tmp.write_text(json.dumps(entries), encoding="utf-8")
                os.replace(tmp, self._path)
            except OSError:
                log.warning("could not write response cache %s", self._path, exc_info=True)
