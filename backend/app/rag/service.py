"""One chat turn: guard -> route -> cache -> retrieve -> (maybe) generate -> check output.

At most one LLM generation call per turn, none in the low band, for template routes or
for blocked input (docs/ai-design.md §3.2). The caller passes an already redacted message.

Guardrails (docs/guardrails-and-security.md §2): the injection heuristics run first and
block (refusal template), flag (tools disabled) or allow; user and KB text are escaped so
they cannot close our prompt tags; the answer is checked for the canary, a prompt echo,
exfiltration links and PII. Every block, flag, redaction and escalation is written to the
guardrail log that the admin Guardrail Log panel reads.
"""

import logging
import re
import secrets
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from functools import lru_cache
from typing import Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.ai import prompts, routing, templates
from app.config import Settings, get_settings
from app.guardrails import injection
from app.guardrails.events import (
    GuardrailEventRecord,
    GuardrailLog,
    InMemoryGuardrailLog,
    get_guardrail_log,
)
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

# escalate_to_agent `reason` values (ai-design.md §6.4) per always-escalate intent.
ESCALATION_REASONS = {
    routing.HUMAN_REQUEST: "user_requested",
    routing.PRIVACY_REQUEST: "sensitive_topic",
    routing.SECURITY_INCIDENT: "sensitive_topic",
    routing.HIGH_PRIORITY: "high_priority",
}
# Input events that count towards INJ-REPEAT and the cooldown.
_ABUSE_TYPES = {
    "prompt_injection",
    "personal_data_request",
    "secret_request",
    "other_account_request",
}


class GuardrailCooldown(Exception):
    """Too many blocked messages from this user; the API answers 429."""

    def __init__(self, retry_after_s: int) -> None:
        super().__init__(f"chat cooldown, retry after {retry_after_s}s")
        self.retry_after_s = retry_after_s


@dataclass(frozen=True)
class Caller:
    """Who is asking, from the signed-in user (see app.rag.api.caller_for)."""

    role: str
    first_name: str = "there"
    club_name: str = "not set"
    job_title: str = "not set"
    user_id: int | None = None


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
    action: Literal["answer", "clarify", "escalate", "refuse"]
    intent: str | None
    confidence: float
    retrieval_confidence: float | None = None
    band: str | None = None
    citations: list[Citation] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    # True when policy requires a hand-off (security, privacy, person requested); the tool
    # executor (issue #7) turns it into an escalate_to_agent call. False = only offered.
    escalate: bool = False
    # escalate_to_agent reason when action == "escalate" (low_confidence, sensitive_topic, ...)
    escalation_reason: str | None = None
    # Capability limiting: False on a flagged turn, so the tool executor offers no tools.
    tools_allowed: bool = True
    # Input guardrail outcome shown to the user: {"type", "action", "rule_ids", "score"}.
    guardrail: dict | None = None
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
        guardrail_log: GuardrailLog | None = None,
        redactor: injection.Redactor | None = None,
    ) -> None:
        self.settings = settings
        self.gateway = gateway
        self.retriever = retriever
        self.cache = cache
        self.guardrail_log = guardrail_log if guardrail_log is not None else InMemoryGuardrailLog()
        # PII redactor for the output check (app.guardrails.pii.redact once PR #16 is merged).
        self.redactor = redactor
        self.canary = f"DD-{secrets.token_hex(4)}"

    def answer(
        self,
        message: str,
        caller: Caller,
        history: Sequence[HistoryTurn] = (),
        *,
        cacheable: bool = True,
        pii_types: Sequence[str] = (),
    ) -> RagAnswer:
        """`message` must already be PII-redacted; `pii_types` = entity types that were masked.

        Raises GuardrailCooldown when the user has had too many blocked messages.
        """
        started = time.monotonic()
        if pii_types:
            self._record(caller, "input", "pii_redacted", "allowed_redacted", "regex",
                         rule_ids=tuple(pii_types))  # fmt: skip
        recent = self._recent_abuse(caller)
        self._check_cooldown(caller, recent)

        verdict = injection.scan_input(message, recent_flags=len(recent))
        guardrail = None
        if verdict.action != "allow":
            event_action = "blocked" if verdict.blocked else "flagged"
            self._record(caller, "input", verdict.type or "prompt_injection", event_action,
                         "heuristic", verdict.score, verdict.rule_ids)  # fmt: skip
            guardrail = {
                "type": verdict.type,
                "action": event_action,
                "rule_ids": list(verdict.rule_ids),
                "score": verdict.score,
            }

        if verdict.blocked:
            result = self._refusal(verdict)
        else:
            history_list = list(history)[-HISTORY_TURNS:]
            result = self._answer(verdict.text, caller, history_list, cacheable and not pii_types)
            result.tools_allowed = verdict.tools_allowed
        result.guardrail = guardrail
        if result.action == "escalate" and result.escalation_reason != "output_blocked":
            self._record_escalation(caller, result)
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
                escalation_reason=ESCALATION_REASONS[intent],
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
        checked = injection.check_output(text, self.canary, self.redactor)
        if checked.action == "block":
            log.error("guardrail: system prompt leak in model output; answer replaced")
            self._record(caller, "output", checked.type or "system_prompt_leak", "blocked",
                         "canary", rule_ids=checked.rule_ids)  # fmt: skip
            return self._low_confidence(
                retrieval, forced, base, model=generation.model, reason="output_blocked"
            )
        if checked.action == "sanitize":
            pii_only = checked.type == "pii_redacted"
            self._record(caller, "output", checked.type or "exfiltration",
                         "allowed_redacted" if pii_only else "flagged", "regex",
                         rule_ids=checked.rule_ids + checked.pii_types)  # fmt: skip
            text = checked.text
            key = None  # never cache an answer the model had to be corrected on
        if text.startswith(prompts.NO_ANSWER):
            return self._low_confidence(retrieval, forced, base, model=generation.model)

        clean, used, invalid = apply_citations(text, len(retrieval.chunks))
        if invalid:
            log.warning("guardrail: dropped invalid citations %s", invalid)
            self._record(caller, "output", "invalid_citation", "flagged", "regex",
                         rule_ids=("OUT-CITATION",))  # fmt: skip
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
            escalation_reason=ESCALATION_REASONS.get(intent) if forced else None,
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
        # User, history and KB text can't open or close our <context>/<history>/<user_message>
        # blocks (guardrails doc §2.2).
        esc = injection.escape_delimiters
        messages: list[BaseMessage] = [SystemMessage(system)]
        for turn in history:
            if turn.role == "user":
                messages.append(HumanMessage(f"<history>\n{esc(turn.content)}\n</history>"))
            else:
                messages.append(AIMessage(esc(turn.content)))
        context = prompts.build_context(
            [(c.context_header, esc(c.chunk.text)) for c in retrieval.chunks]
        )
        messages.append(HumanMessage(prompts.build_user_turn(context, esc(message))))
        return messages

    # ---- guardrail helpers ----------------------------------------------------

    def _record(
        self,
        caller: Caller,
        stage: str,
        type_: str,
        action: str,
        detector: str,
        score: float | None = None,
        rule_ids: Sequence[str] = (),
    ) -> None:
        event = GuardrailEventRecord(
            stage=stage, type=type_, action=action, detector=detector, score=score,
            rule_ids=tuple(rule_ids), user_id=caller.user_id, user_role=caller.role,
        )  # fmt: skip
        try:
            self.guardrail_log.record(event)
        except Exception:  # the log must never break a chat turn
            log.exception("could not write guardrail event %s/%s", stage, type_)

    def _record_escalation(self, caller: Caller, result: RagAnswer) -> None:
        reason = result.escalation_reason or "low_confidence"
        if reason == "low_confidence":
            rule_ids: tuple[str, ...] = ("RAG-LOW-CONFIDENCE",)
            detector = "confidence"
        else:
            rule_ids = (f"INTENT-{(result.intent or 'unknown').upper()}",)
            detector = "policy"
        # A forced hand-off is "escalated"; a low-confidence reply only offers one.
        action = "escalated" if result.escalate else "flagged"
        self._record(caller, "retrieval", reason, action, detector,
                     result.retrieval_confidence, rule_ids)  # fmt: skip

    def _recent_abuse(self, caller: Caller) -> list[GuardrailEventRecord]:
        """This user's flagged/blocked input events in the last 10 minutes, oldest first."""
        if caller.user_id is None:
            return []
        since = datetime.now(UTC) - timedelta(seconds=injection.REPEAT_WINDOW_S)
        try:
            events = self.guardrail_log.for_user(caller.user_id, since)
        except Exception:
            log.exception("could not read guardrail events")
            return []
        return [
            e for e in events
            if e.stage == "input" and e.type in _ABUSE_TYPES and e.action in ("blocked", "flagged")
        ]  # fmt: skip

    def _check_cooldown(self, caller: Caller, recent: list[GuardrailEventRecord]) -> None:
        limit = self.settings.guardrail_cooldown_blocks
        blocks = [e for e in recent if e.action == "blocked"]
        if limit <= 0 or len(blocks) < limit:
            return
        until = blocks[-1].created_at + timedelta(seconds=injection.COOLDOWN_S)
        retry_after = max(1, int((until - datetime.now(UTC)).total_seconds()))
        self._record(caller, "input", "rate_limited", "blocked", "policy",
                     rule_ids=("INJ-COOLDOWN",))  # fmt: skip
        raise GuardrailCooldown(retry_after)

    @staticmethod
    def _refusal(verdict: injection.InputVerdict) -> RagAnswer:
        text = {
            "secret_request": templates.REFUSE_LEAK,
            "personal_data_request": templates.REFUSE_PERSONAL_DATA,
        }.get(verdict.type or "", templates.REFUSE_INJECTION)
        return RagAnswer(text, "template", "refuse", "abuse", 0.0, tools_allowed=False)

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
        self,
        retrieval: RetrievalResult,
        forced: bool,
        base: dict,
        *,
        model: str | None = None,
        reason: str | None = None,
    ) -> RagAnswer:
        if reason is None:
            reason = ESCALATION_REASONS.get(base["intent"], "low_confidence")
            reason = reason if forced else "low_confidence"
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
            escalation_reason=reason,
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
            escalation_reason=ESCALATION_REASONS.get(base["intent"]) if forced else None,
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
    return RagService(
        settings, gateway, retriever, cache, get_guardrail_log(), injection.load_pii_redactor()
    )
