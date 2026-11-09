"""Ask DinkDesk one golden question and record what it did (an `Observation`).

- `InProcessTarget` calls `RagService.answer()` directly (needs the KB index on this PC).
- `HttpTarget` calls the running API (`--base-url`, e.g. a Cloudflare tunnel to Jose's PC):
  it signs in as the seeded demo user for each role, sends `POST /api/v1/rag/ask`, and
  gets the ranked documents for the retrieval metrics from `POST /api/v1/kb/search` as an
  admin (`as_role` = the question's role; the query embedding is cached on the server, so
  this adds no LLM call).

Both return the same `Observation`, so scoring does not care where the answer came from.
"""

import time
from collections.abc import Callable
from pathlib import Path

import httpx

from evalkit.metrics import Observation, doc_id_of

# Seeded demo accounts (backend/app/seed.py). Override with --credentials for other data.
DEMO_USERS = {
    "member": ("member@picklehub.example", "member123!"),
    "staff": ("staff@picklehub.example", "staff123!"),
    "agent": ("agent@picklehub.example", "agent123!"),
    "admin": ("admin1@picklehub.example", "admin123!"),
}


def chunk_texts(kb_dir: Path) -> dict[str, str]:
    """chunk_id -> header + text, built from the Markdown KB (no embeddings, no network).

    Used to give the judge the full text of the chunks the server retrieved, which the
    HTTP responses only identify by id.
    """
    from app.rag.kb import chunk_document, load_knowledge_base

    docs, _errors = load_knowledge_base(kb_dir)
    return {c.chunk_id: f"{c.header}\n{c.text}" for d in docs for c in chunk_document(d)}


class InProcessTarget:
    name = "in-process"

    def __init__(self, service, *, use_cache: bool = False) -> None:
        self.service = service
        self.use_cache = use_cache

    def describe(self) -> dict:
        provider = self.service.gateway.provider
        return {
            "target": self.name,
            "provider": provider.name,
            "model_name": provider.chat_model_name(),
            "embedding_model": provider.embedding_model_name(),
            "kb_version": self.service.retriever.kb_version,
        }

    def ask(self, question: str, role: str) -> Observation:
        from app.rag.service import Caller

        started = time.monotonic()
        try:
            answer = self.service.answer(question, Caller(role=role), cacheable=self.use_cache)
            # Retrieval metrics come from a separate search so they exist for every item,
            # including template routes that never search (query embedding is cached).
            retrieval = self.service.retriever.search(question, role)
        except Exception as exc:  # report the item as an error, keep the run going
            return Observation(
                error=f"{type(exc).__name__}: {exc}",
                latency_ms=int((time.monotonic() - started) * 1000),
            )
        return Observation(
            content=answer.content,
            answer_mode=answer.answer_mode,
            action=answer.action,
            intent=answer.intent,
            escalate=answer.escalate,
            tool_calls=[],
            cited_doc_ids=[c.doc_id for c in answer.citations],
            retrieved_doc_ids=retrieval.doc_ids,
            retrieved_chunk_ids=[c.chunk.chunk_id for c in retrieval.chunks],
            confidence=answer.confidence,
            retrieval_confidence=retrieval.retrieval_confidence,
            band=retrieval.band,
            model=answer.model,
            prompt_version=answer.prompt_version,
            server_latency_ms=answer.latency_ms,
            latency_ms=answer.latency_ms,
        )


class HttpTarget:
    name = "http"

    def __init__(
        self,
        base_url: str,
        *,
        users: dict[str, tuple[str, str]] | None = None,
        client: httpx.Client | None = None,
        timeout_s: float = 90,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.users = users or DEMO_USERS
        self.client = client or httpx.Client(base_url=self.base_url, timeout=timeout_s)
        self._tokens: dict[str, str] = {}
        self._sleep = sleep
        self._clock = clock

    def describe(self) -> dict:
        health = self._request("GET", "/health", None).json()
        return {
            "target": f"{self.name} {self.base_url}",
            "provider": health.get("llm_provider"),
            "server_version": health.get("version"),
            "llm_configured": health.get("llm_configured"),
        }

    def _token(self, role: str) -> str:
        if role not in self._tokens:
            email, password = self.users[role]
            resp = self._request(
                "POST", "/api/v1/auth/login", None, json={"email": email, "password": password}
            )
            self._tokens[role] = resp.json()["access_token"]
        return self._tokens[role]

    def _request(self, method: str, path: str, role: str | None, **kwargs) -> httpx.Response:
        """One call, retried on 429/502/503/504 (tunnel hiccups, server rate limit)."""
        headers = {"Authorization": f"Bearer {self._token(role)}"} if role else {}
        for attempt in range(4):
            resp = self.client.request(method, path, headers=headers, **kwargs)
            if resp.status_code not in (429, 502, 503, 504) or attempt == 3:
                break
            retry_after = resp.headers.get("retry-after", "")
            self._sleep(float(retry_after) if retry_after.isdigit() else 5 * (attempt + 1))
        resp.raise_for_status()
        return resp

    def ask(self, question: str, role: str) -> Observation:
        started = self._clock()
        try:
            body = self._request("POST", "/api/v1/rag/ask", role, json={"content": question}).json()
            latency = int((self._clock() - started) * 1000)
            search = self._request(
                "POST", "/api/v1/kb/search", "admin", json={"query": question, "as_role": role}
            ).json()
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            return Observation(
                error=f"{type(exc).__name__}: {exc}",
                latency_ms=int((self._clock() - started) * 1000),
            )
        return observation_from_response(body, search, latency)


def observation_from_response(body: dict, search: dict | None, latency_ms: int) -> Observation:
    """Build an Observation from `/rag/ask` (and optionally `/kb/search`) JSON.

    Tolerant on purpose: a guardrail block may come back as `answer_mode: "refusal"`, a
    top-level `guardrail` object (docs/api.md §4 SSE event) or `blocked: true`.
    """
    msg = body.get("assistant_message") or {}
    guardrail = body.get("guardrail") or msg.get("guardrail") or {}
    tool_calls = [
        t.get("name") or t.get("tool") or t.get("tool_name")
        for t in body.get("tool_calls") or []
        if isinstance(t, dict)
    ]
    results = (search or {}).get("results") or []
    chunk_ids = [r["chunk_id"] for r in results if "chunk_id" in r]
    return Observation(
        content=msg.get("content") or "",
        answer_mode=msg.get("answer_mode"),
        action=msg.get("action"),
        intent=msg.get("intent"),
        escalate=bool(body.get("escalation_required")),
        tool_calls=[t for t in tool_calls if t],
        refused=bool(body.get("blocked") or guardrail.get("action") == "blocked"),
        cited_doc_ids=[c.get("doc_id") for c in msg.get("citations") or [] if c.get("doc_id")],
        retrieved_doc_ids=list(dict.fromkeys(doc_id_of(c) for c in chunk_ids)),
        retrieved_chunk_ids=chunk_ids,
        confidence=msg.get("confidence"),
        retrieval_confidence=(search or {}).get("confidence", msg.get("retrieval_confidence")),
        band=(search or {}).get("band"),
        model=msg.get("model_name"),
        prompt_version=msg.get("prompt_version"),
        server_latency_ms=msg.get("latency_ms"),
        latency_ms=latency_ms,
    )
