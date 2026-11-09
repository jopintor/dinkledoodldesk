"""RAG endpoints.

- `POST /rag/ask` — one stateless chat turn. Its response has the same shape as
  `POST /conversations/{id}/messages` in docs/api.md §4, so the frontend can build the chat
  widget against it now. When conversations exist, that endpoint calls
  `RagService.answer()` the same way and this route can be removed.
- `POST /kb/search` — retrieval debug for agents and admins (docs/api.md §8).

Integration seams (kept small on purpose):
- `get_caller`: until JWT auth (PR #15) is merged, the role comes from the `X-Dev-Role`
  header and only when `RAG_DEV_AUTH=true`. After #15, replace its body with
  `Depends(get_current_user)` and map the user's role, first name, club and job title.
- `redact_input`: returns the text unchanged until the PII redaction guardrail (PR #16) is
  merged; then call `app.guardrails.pii.redact()` here. Nothing else changes.
"""

from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.config import get_settings
from app.rag.kb import ROLES
from app.rag.service import Caller, HistoryTurn, RagService, get_rag_service

router = APIRouter(tags=["rag"])

Role = Literal["member", "staff", "agent", "admin"]


def get_caller(x_dev_role: str | None = Header(default=None)) -> Caller:
    if not get_settings().rag_dev_auth:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    role = (x_dev_role or "member").strip().lower()
    if role not in ROLES:
        raise HTTPException(422, f"unknown role {role!r}")
    return Caller(role=role)


def redact_input(text: str) -> tuple[str, bool]:
    """(redacted text, PII found). Placeholder until PR #16; see module docstring."""
    return text, False


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
    as_role: Role | None = None
    k: int = Field(default=5, ge=1, le=5)


@router.post("/rag/ask")
def ask(
    body: AskRequest,
    caller: Caller = Depends(get_caller),
    service: RagService = Depends(get_rag_service),
) -> dict:
    content, pii_found = redact_input(body.content)
    history = [HistoryTurn(h.role, redact_input(h.content)[0]) for h in body.history]
    answer = service.answer(content, caller, history, cacheable=not pii_found)
    return {
        "user_message": {"content": content, "pii_detected": pii_found},
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
    }


@router.post("/kb/search")
def kb_search(
    body: SearchRequest,
    caller: Caller = Depends(get_caller),
    service: RagService = Depends(get_rag_service),
) -> dict:
    if caller.role not in ("agent", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
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
