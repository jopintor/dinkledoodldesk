"""RAG endpoints.

- `POST /api/v1/rag/ask` — one stateless chat turn. Its response has the same shape as
  `POST /conversations/{id}/messages` in docs/api.md §4, so the frontend can build the chat
  widget against it now. When conversations exist, that endpoint calls
  `RagService.answer()` the same way and this route can be removed.
- `POST /api/v1/kb/search` — retrieval debug for agents and admins (docs/api.md §8).

- `GET /api/v1/guardrail-events` — the admin Guardrail Log feed (docs/api.md §9), polled
  by the "Try to break DinkDesk" panel.

All routes need a JWT from `POST /api/v1/auth/login`: `/rag/ask` the `chat:use`
permission, `/kb/search` the `kb:search` permission (agents and admins) and
`/guardrail-events` the `guardrail:read` permission (admins).

`redact_input` uses `app.guardrails.pii.redact()` when the PII redaction guardrail (PR #16)
is installed and returns the text unchanged until then.
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai import templates
from app.deps import get_db, require
from app.guardrails.events import GuardrailLog, get_guardrail_log
from app.guardrails.injection import load_pii_redactor
from app.models import Club, Role, User
from app.rag.kb import ROLES
from app.rag.service import (
    Caller,
    GuardrailCooldown,
    HistoryTurn,
    RagService,
    get_rag_service,
)

router = APIRouter(prefix="/api/v1", tags=["rag"])

RoleName = Literal["member", "staff", "agent", "admin"]


def caller_for(user: User, db: Session) -> Caller:
    """What the prompt and the role filter need to know about the signed-in user."""
    role = db.get(Role, user.role_id)
    club = db.get(Club, user.club_id) if user.club_id else None
    first_name = (user.full_name or "").split(" ")[0] or "there"
    return Caller(
        # A role the KB doesn't know gets the least-privileged view.
        role=role.name if role and role.name in ROLES else "member",
        first_name=first_name,
        club_name=club.name if club else "not set",
        user_id=user.id,
    )


def get_caller(user: User = Depends(require("chat:use")), db: Session = Depends(get_db)) -> Caller:
    return caller_for(user, db)


def get_search_caller(
    user: User = Depends(require("kb:search")), db: Session = Depends(get_db)
) -> Caller:
    return caller_for(user, db)


_redactor = load_pii_redactor()


def redact_input(text: str) -> tuple[str, list[str]]:
    """(redacted text, entity types found, e.g. ["PH_MOBILE", "EMAIL"])."""
    if _redactor is None:
        return text, []
    clean, found = _redactor(text)
    return clean, list(found)


class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class AskRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    client_message_id: str | None = Field(default=None, max_length=64)
    # Stand-in for stored conversation history (last 6 messages) until conversations exist.
    history: list[HistoryItem] = Field(default_factory=list, max_length=6)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    as_role: RoleName | None = None
    k: int = Field(default=5, ge=1, le=5)


@router.post("/rag/ask")
def ask(
    body: AskRequest,
    caller: Caller = Depends(get_caller),
    service: RagService = Depends(get_rag_service),
) -> dict:
    content, pii_types = redact_input(body.content)
    history = [HistoryTurn(h.role, redact_input(h.content)[0]) for h in body.history]
    try:
        answer = service.answer(content, caller, history, pii_types=pii_types)
    except GuardrailCooldown as exc:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMITED",
                "message": templates.COOLDOWN.format(minutes=max(1, exc.retry_after_s // 60)),
                "details": {"retry_after_s": exc.retry_after_s},
            },
            headers={"Retry-After": str(exc.retry_after_s)},
        ) from None
    return {
        "user_message": {
            "content": content,
            "pii_detected": bool(pii_types),
            "pii_redacted": pii_types,
        },
        "assistant_message": {
            "content": answer.content,
            "intent": answer.intent,
            "confidence": answer.confidence,
            "retrieval_confidence": answer.retrieval_confidence,
            "answer_mode": answer.answer_mode,
            "action": answer.action,
            "citations": [vars(c) for c in answer.citations],
            "model_name": answer.model,
            "prompt_version": answer.prompt_version,
            "latency_ms": answer.latency_ms,
        },
        "tool_calls": [],
        "conversation_status": "active",
        "suggested_actions": answer.suggested_actions,
        "escalation_required": answer.escalate,
        "escalation_reason": answer.escalation_reason,
        "tools_allowed": answer.tools_allowed,
        # Same payload as the SSE `guardrail` event (api.md §4) when input was blocked/flagged.
        "guardrail": (
            {**answer.guardrail, "message": answer.content}
            if answer.guardrail and answer.guardrail["action"] == "blocked"
            else answer.guardrail
        ),
    }


@router.get("/guardrail-events")
def guardrail_events(
    since: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _admin: User = Depends(require("guardrail:read")),
    db: Session = Depends(get_db),
    guardrail_log: GuardrailLog = Depends(get_guardrail_log),
) -> dict:
    """Newest first. Rule ids and entity types only — never message text."""
    events = guardrail_log.recent(since=since, limit=limit)
    users: dict[int, User | None] = {}
    items = []
    for e in events:
        if e.user_id is not None and e.user_id not in users:
            users[e.user_id] = db.get(User, e.user_id)
        user = users.get(e.user_id) if e.user_id is not None else None
        items.append(
            {
                "id": str(e.id),
                "created_at": e.created_at.isoformat(),
                "stage": e.stage,
                "type": e.type,
                "action": e.action,
                "detector": e.detector,
                "score": e.score,
                "rule_ids": list(e.rule_ids),
                "user": (
                    {"full_name": user.full_name if user else None, "role": e.user_role}
                    if e.user_id is not None or e.user_role
                    else None
                ),
            }
        )
    return {"items": items}


@router.post("/kb/search")
def kb_search(
    body: SearchRequest,
    caller: Caller = Depends(get_search_caller),
    service: RagService = Depends(get_rag_service),
) -> dict:
    result = service.retriever.search(body.query, body.as_role or caller.role)
    return {
        "confidence": result.retrieval_confidence,
        "band": result.band,
        "kb_version": service.retriever.kb_version,
        "results": [
            {
                "chunk_id": item.chunk.chunk_id,
                "doc_id": item.chunk.doc_id,
                "section": item.chunk.section,
                "vector_score": item.vector_score,
                "bm25_score": item.bm25_score,
                "rrf_score": item.rrf_score,
                "is_current": item.chunk.is_current,
                "preview": item.chunk.text[:200],
            }
            for item in result.chunks[: body.k]
        ],
    }
