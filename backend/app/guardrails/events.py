"""Guardrail event log: every block, flag, redaction and escalation (guardrails doc §0).

The RAG service writes through the small `GuardrailLog` protocol; the admin Guardrail Log
panel reads it through `GET /api/v1/guardrail-events`. Two backends:

- `InMemoryGuardrailLog` — a bounded ring buffer. Default; needs no database, which is
  enough for one uvicorn process during the demo.
- `SqlGuardrailLog` — rows in the `guardrail_events` table (`app.models.GuardrailEvent`).
  The current model has `rule`, `action_taken` and a text `details` column, so the
  structured fields go into `details` as JSON. When the model grows the columns from
  docs/database.md §6 (stage, type, detector, score, user_id), only `_to_row` / `_from_row`
  change.

Select with `GUARDRAIL_LOG_BACKEND=memory|db`. Events never contain message text or
matched values — only rule ids and entity types.
"""

from __future__ import annotations

import itertools
import json
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
from functools import lru_cache
from typing import Literal, Protocol

Stage = Literal["input", "retrieval", "output", "tool", "auth"]
EventAction = Literal["allowed_redacted", "blocked", "escalated", "flagged"]
Detector = Literal["regex", "heuristic", "canary", "policy", "confidence", "rbac", "llm"]


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class GuardrailEventRecord:
    stage: Stage
    type: str
    action: EventAction
    detector: Detector
    score: float | None = None
    rule_ids: tuple[str, ...] = ()
    user_id: int | None = None
    user_role: str | None = None
    conversation_id: int | None = None
    message_id: int | None = None
    id: int | None = None
    created_at: datetime = field(default_factory=_now)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["rule_ids"] = list(self.rule_ids)
        data["created_at"] = self.created_at.isoformat()
        return data


class GuardrailLog(Protocol):
    def record(self, event: GuardrailEventRecord) -> GuardrailEventRecord: ...

    def recent(
        self, *, since: datetime | None = None, limit: int = 100
    ) -> list[GuardrailEventRecord]:
        """Newest first."""
        ...

    def for_user(self, user_id: int, since: datetime) -> list[GuardrailEventRecord]:
        """One user's events since `since`, oldest first (repeat / cooldown checks)."""
        ...


class InMemoryGuardrailLog:
    def __init__(self, max_events: int = 1000) -> None:
        self._events: deque[GuardrailEventRecord] = deque(maxlen=max_events)
        self._ids = itertools.count(1)
        self._lock = threading.Lock()

    def record(self, event: GuardrailEventRecord) -> GuardrailEventRecord:
        with self._lock:
            stored = replace(event, id=next(self._ids))
            self._events.append(stored)
        return stored

    def recent(
        self, *, since: datetime | None = None, limit: int = 100
    ) -> list[GuardrailEventRecord]:
        with self._lock:
            events = list(self._events)
        if since is not None:
            events = [e for e in events if e.created_at > since]
        return list(reversed(events))[:limit]

    def for_user(self, user_id: int, since: datetime) -> list[GuardrailEventRecord]:
        with self._lock:
            return [e for e in self._events if e.user_id == user_id and e.created_at >= since]


class SqlGuardrailLog:
    """Backed by `app.models.GuardrailEvent`. `session_factory` is e.g. `SessionLocal`."""

    _DETAIL_FIELDS = ("stage", "type", "detector", "score", "rule_ids", "user_id", "user_role")

    def __init__(self, session_factory: Callable) -> None:
        self._session_factory = session_factory

    def record(self, event: GuardrailEventRecord) -> GuardrailEventRecord:
        from app.models import GuardrailEvent

        with self._session_factory() as session:
            row = GuardrailEvent(**self._to_row(event))
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._from_row(row)

    def recent(
        self, *, since: datetime | None = None, limit: int = 100
    ) -> list[GuardrailEventRecord]:
        from sqlalchemy import select

        from app.models import GuardrailEvent

        query = select(GuardrailEvent).order_by(GuardrailEvent.id.desc()).limit(limit)
        if since is not None:
            query = query.where(GuardrailEvent.created_at > since)
        with self._session_factory() as session:
            return [self._from_row(r) for r in session.scalars(query)]

    def for_user(self, user_id: int, since: datetime) -> list[GuardrailEventRecord]:
        events = self.recent(since=since, limit=500)
        return [e for e in reversed(events) if e.user_id == user_id]

    @classmethod
    def _to_row(cls, event: GuardrailEventRecord) -> dict:
        details = {k: getattr(event, k) for k in cls._DETAIL_FIELDS}
        details["rule_ids"] = list(event.rule_ids)
        return {
            "conversation_id": event.conversation_id,
            "message_id": event.message_id,
            "rule": f"{event.stage}:{event.type}"[:120],
            "action_taken": event.action,
            "details": json.dumps(details),
            "created_at": event.created_at,
        }

    @staticmethod
    def _from_row(row) -> GuardrailEventRecord:
        details = json.loads(row.details or "{}")
        stage, _, type_ = (row.rule or "").partition(":")
        created = row.created_at
        if created is not None and created.tzinfo is None:
            created = created.replace(tzinfo=UTC)  # SQLite drops the timezone
        return GuardrailEventRecord(
            stage=details.get("stage", stage or "input"),
            type=details.get("type", type_ or row.rule),
            action=row.action_taken,
            detector=details.get("detector", "heuristic"),
            score=details.get("score"),
            rule_ids=tuple(details.get("rule_ids", ())),
            user_id=details.get("user_id"),
            user_role=details.get("user_role"),
            conversation_id=row.conversation_id,
            message_id=row.message_id,
            id=row.id,
            created_at=created or _now(),
        )


@lru_cache
def get_guardrail_log() -> GuardrailLog:
    """Process-wide log chosen by `GUARDRAIL_LOG_BACKEND` (FastAPI dependency)."""
    from app.config import get_settings

    if get_settings().guardrail_log_backend == "db":
        from app.db import SessionLocal

        return SqlGuardrailLog(SessionLocal)
    return InMemoryGuardrailLog()
