"""One chat turn: route -> cache -> retrieve -> (maybe) generate -> check citations.

At most one LLM generation call per turn, none in the low band or for template routes
(docs/ai-design.md §3.2). The caller passes an already redacted message.
"""

import logging
import re
import secrets
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.ai import prompts, routing, templates
from app.config import Settings, get_settings
from app.llm import LLMGateway, LLMUnavailable, get_llm_provider
from app.rag.cache import ResponseCache, cache_key
from app.rag.retriever import RetrievalResult, Retriever, ScoredChunk
from app.rag.store import KBStore, collection_name, make_client

log = logging.getLogger(__name__)

_PHT = timezone(timedelta(hours=8))
_CITATION = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
_FOLLOW_UP = re.compile(r"^\s*(it|that|this|same|still)\b", re.I)
HISTORY_TURNS = 6
DEGRADED_SOURCES = 3
OFFER_HELP = ["create_ticket", "escalate_to_agent"]


@dataclass(frozen=True)
class Caller:
    """Who is asking. Built from the JWT user once auth (PR #15) is wired in."""

    role: str
    first_name: str = "there"
    club_name: str = "not set"
    job_title: str = "not set"


@dataclass(frozen=True)
class HistoryTurn:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class Citation:
    n: int
    doc_id: str
    title: str
    section: str
    chunk_id: str


@dataclass
class RagAnswer:
    content: str
    answer_mode: Literal["generated", "cached", "template", "degraded"]
    action: Literal["answer", "clarify", "escalate"]
    intent: str | None
    confidence: float
    retrieval_confidence: float | None = None
    band: str | None = None
    citations: list[Citation] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    # True when policy requires a hand-off (security, privacy, person requested); the tool
    # executor (issue #7) turns it into an escalate_to_agent call. False = only offered.
    escalate: bool = False
    model: str | None = None
    prompt_version: str = prompts.PROMPT_VERSION
    kb_version: str | None = None
    retrieved_chunk_ids: list[str] = field(default_factory=list)
    latency_ms: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def apply_citations(text: str, n_sources: int) -> tuple[str, list[int], list[int]]:
    """Keep `[n]` markers that point at a supplied source; drop the others.

    Returns (clean text, valid numbers used, invalid numbers dropped).
    """
    used: list[int] = []
    invalid: list[int] = []

    def replace(match: re.Match[str]) -> str:
        numbers = [int(n) for n in re.split(r"\s*,\s*", match.group(1))]
        kept = []
        for n in numbers:
            if 1 <= n <= n_sources:
                kept.append(n)
                if n not in used:
                    used.append(n)
            else:
                invalid.append(n)
        return "".join(f"[{n}]" for n in kept)

    clean = _CITATION.sub(replace, text)
    clean = re.sub(r"[ \t]+([.,;:])", r"\1", clean)
    return clean.strip(), sorted(used), invalid


def build_query(message: str, history: Sequence[HistoryTurn]) -> str:
    """Prepend the previous user message to a short follow-up (no LLM rewrite call)."""
    previous = next((t.content for t in reversed(history) if t.role == "user"), None)
    if previous and (len(message.split()) <= 6 or _FOLLOW_UP.match(message)):
        return f"{previous} / {message}"
    return message


class RagService:
    def __init__(
        self,
        settings: Settings,
        gateway: LLMGateway,
        retriever: Retriever,
        cache: ResponseCache,
    ) -> None:
        self.settings = settings
        self.gateway = gateway
        self.retriever = retriever
        self.cache = cache
        self.canary = f"DD-{secrets.token_hex(4)}"

    def answer(
        self,
        message: str,
        caller: Caller,
        history: Sequence[HistoryTurn] = (),
        *,
        cacheable: bool = True,
    ) -> RagAnswer:
        """`message` must already be PII-redacted. `cacheable=False` when it contained PII."""
        started = time.monotonic()
        result = self._answer(message, caller, list(history)[-HISTORY_TURNS:], cacheable)
        result.latency_ms = int((time.monotonic() - started) * 1000)
        return result

    def _answer(
        self, message: str, caller: Caller, history: list[HistoryTurn], cacheable: bool
    ) -> RagAnswer:
        intent = routing.rule_intent(message)
        if intent == routing.AMBIGUOUS and history:
            intent = None  # a short follow-up; build_query adds the previous question
        if intent == routing.GREETING:
            return RagAnswer(templates.GREETING, "template", "answer", intent, 1.0)
        if intent == routing.AMBIGUOUS:
            return RagAnswer(routing.clarify_question(message), "template", "clarify", intent, 0.0)
        if intent in (routing.HUMAN_REQUEST, routing.PRIVACY_REQUEST):
            text = (
                templates.HUMAN_REQUEST
                if intent == routing.HUMAN_REQUEST
                else templates.PRIVACY_REQUEST
            )
            return RagAnswer(
                text, "template", "escalate", intent, 0.0,
                suggested_actions=["escalate_to_agent"], escalate=True,
            )  # fmt: skip

        forced = intent in routing.ALWAYS_ESCALATE
        kb_version = self.retriever.kb_version
        key = None
        if cacheable and not history and not forced:
            key = cache_key(message, caller.role, kb_version, prompts.PROMPT_VERSION)
            hit = self.cache.get(key)
            if hit is not None:
                cached = RagAnswer(
                    **{**hit, "citations": [Citation(**c) for c in hit["citations"]]}
                )
                cached.answer_mode = "cached"
                return cached

        retrieval = self.retriever.search(build_query(message, history), caller.role)
        base = {
            "intent": intent,
            "retrieval_confidence": retrieval.retrieval_confidence,
            "band": retrieval.band,
            "kb_version": kb_version,
            "retrieved_chunk_ids": [c.chunk.chunk_id for c in retrieval.chunks],
        }
        if retrieval.band == "low":
            return self._low_confidence(retrieval, forced, base)

        try:
            generation = self.gateway.generate(self._messages(message, caller, history, retrieval))
        except LLMUnavailable as exc:
            log.warning("serving degraded answer: %s", exc)
            return self._degraded(retrieval, forced, base)

        text = generation.text.strip()
        if self.canary in text:
            log.error("guardrail: system prompt canary in model output; answer replaced")
            return self._low_confidence(retrieval, forced, base, model=generation.model)
        if text.startswith(prompts.NO_ANSWER):
            return self._low_confidence(retrieval, forced, base, model=generation.model)

        clean, used, invalid = apply_citations(text, len(retrieval.chunks))
        if invalid:
            # TODO: write a guardrail_events row (stage output, invalid_citation, flagged).
            log.warning("guardrail: dropped invalid citations %s", invalid)
        confidence = retrieval.retrieval_confidence * (1.0 if used else 0.5)
        if confidence < self.settings.rag_medium_threshold:
            return self._low_confidence(retrieval, forced, base, model=generation.model)

        answer = RagAnswer(
            content=clean,
            answer_mode="generated",
            action="escalate" if forced else "answer",
            confidence=round(confidence, 4),
            citations=[self._citation(n, retrieval.chunks[n - 1]) for n in used],
            suggested_actions=self._suggestions(retrieval.band, forced),
            escalate=forced,
            model=generation.model,
            **base,
        )
        if key is not None:
            self.cache.put(key, answer.to_dict())
        return answer

    # ---- helpers --------------------------------------------------------------

    def _messages(
        self,
        message: str,
        caller: Caller,
        history: list[HistoryTurn],
        retrieval: RetrievalResult,
    ) -> list[BaseMessage]:
        system = prompts.SYSTEM_PROMPT_V1.format(
            first_name=caller.first_name,
            role=caller.role,
            club_name=caller.club_name,
            job_title=caller.job_title,
            now_pht=datetime.now(_PHT).strftime("%A %d %B %Y, %I:%M %p"),
            confidence_note=prompts.MEDIUM_CONFIDENCE_NOTE if retrieval.band == "medium" else "",
            allowed_tools=prompts.NO_TOOLS,
            canary=self.canary,
        )
        messages: list[BaseMessage] = [SystemMessage(system)]
        for turn in history:
            if turn.role == "user":
                messages.append(HumanMessage(f"<history>\n{turn.content}\n</history>"))
            else:
                messages.append(AIMessage(turn.content))
        context = prompts.build_context(
            [(c.context_header, c.chunk.text) for c in retrieval.chunks]
        )
        messages.append(HumanMessage(prompts.build_user_turn(context, message)))
        return messages

    @staticmethod
    def _citation(n: int, item: ScoredChunk) -> Citation:
        c = item.chunk
        return Citation(n=n, doc_id=c.doc_id, title=c.title, section=c.section, chunk_id=c.chunk_id)

    @staticmethod
    def _suggestions(band: str, forced: bool) -> list[str]:
        if forced:
            return ["escalate_to_agent"]
        return [] if band == "high" else list(OFFER_HELP)

    def _low_confidence(
        self, retrieval: RetrievalResult, forced: bool, base: dict, *, model: str | None = None
    ) -> RagAnswer:
        if forced and base["intent"] == routing.SECURITY_INCIDENT:
            text = templates.SECURITY_ESCALATION
        elif self.retriever.chunk_count == 0:
            text = templates.NOT_INDEXED
        else:
            text = templates.LOW_CONFIDENCE
        return RagAnswer(
            content=text,
            answer_mode="template",
            action="escalate",
            confidence=0.0,
            suggested_actions=["escalate_to_agent"] if forced else list(OFFER_HELP),
            escalate=forced,
            model=model,
            **base,
        )

    def _degraded(self, retrieval: RetrievalResult, forced: bool, base: dict) -> RagAnswer:
        sources = retrieval.chunks[:DEGRADED_SOURCES]
        body = "\n\n".join(
            f"[{n}] {item.context_header}\n{item.chunk.text}"
            for n, item in enumerate(sources, start=1)
        )
        return RagAnswer(
            content=f"{templates.DEGRADED_INTRO}\n\n{body}",
            answer_mode="degraded",
            action="escalate" if forced else "answer",
            confidence=retrieval.retrieval_confidence,
            citations=[self._citation(n, item) for n, item in enumerate(sources, start=1)],
            suggested_actions=["escalate_to_agent"] if forced else list(OFFER_HELP),
            escalate=forced,
            **base,
        )


@lru_cache
def get_rag_service() -> RagService:
    """Process-wide service built from settings (FastAPI dependency; tests override it)."""
    settings = get_settings()
    provider = get_llm_provider(settings)
    gateway = LLMGateway(provider, settings)
    store = KBStore(
        lambda: make_client(settings), collection_name(settings, provider.embedding_model_name())
    )
    retriever = Retriever(store, gateway.embed_query, settings)
    cache = ResponseCache(settings.response_cache_path or None, settings.response_cache_ttl_s)
    return RagService(settings, gateway, retriever, cache)
