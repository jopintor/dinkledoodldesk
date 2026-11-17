"""LLM gateway: the one place that calls the provider (docs/architecture.md §5.2).

Wraps an `LLMProvider` with what the Gemini free tier needs:

- token-bucket limiter at `LLM_RPM_LIMIT` plus a concurrency cap and a bounded wait;
- retry on 429 / RESOURCE_EXHAUSTED, honouring the server's retry delay, else exponential
  backoff with full jitter, never past the request budget;
- one attempt on the fallback model after that, or straight away on 5xx / timeout / 404;
- daily quota guard (switch to the fallback model at 90 % of `LLM_RPD_LIMIT`);
- circuit breaker (5 consecutive failures -> open for 60 s, then one probe);
- LRU cache of query embeddings, with L2 normalisation of every vector.

When none of that produces an answer it raises `LLMUnavailable`, and the caller serves
degraded mode instead of an error page.
"""

import logging
import math
import random
import re
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TypeVar
from zoneinfo import ZoneInfo

from langchain_core.messages import BaseMessage

from app.config import Settings
from app.llm.base import LLMProvider, LLMProviderError

log = logging.getLogger(__name__)

T = TypeVar("T")

# Gemini quotas reset at midnight Pacific time.
_QUOTA_TZ = ZoneInfo("America/Los_Angeles")
_RETRY_DELAY = re.compile(
    r"(?:retry_?delay['\"]?\s*[:=]\s*['\"]?|retry in\s+)(\d+(?:\.\d+)?)\s*s", re.IGNORECASE
)
_MAX_RETRY_ATTEMPTS = 3
_BACKOFF_BASE_S = 1.0
_QUERY_CACHE_SIZE = 2000


class LLMUnavailable(RuntimeError):
    """No model call succeeded within the budget; serve cache or degraded mode instead."""


@dataclass(frozen=True)
class ToolRequest:
    """A function call the model asked for. Nothing runs until the user confirms it."""

    name: str
    args: dict


@dataclass(frozen=True)
class Generation:
    text: str
    model: str
    tool_requests: tuple[ToolRequest, ...] = field(default=())


def normalise(vector: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def classify_error(exc: BaseException) -> tuple[str, float | None]:
    """Return (kind, server retry delay in seconds).

    kind is `rate_limit` (retry), `daily_quota` (go to the fallback model), `fatal`
    (bad key or bad request: retrying or falling back won't help) or `transient`
    (5xx, timeout, retired model: try the fallback model).
    """
    chain: list[BaseException] = []
    current: BaseException | None = exc
    while current is not None and current not in chain:
        chain.append(current)
        current = current.__cause__ or current.__context__
    if any(isinstance(e, LLMProviderError) for e in chain):
        return "fatal", None

    text = " ".join(f"{type(e).__name__}: {e}" for e in chain)
    codes = {getattr(e, attr, None) for e in chain for attr in ("code", "status_code")}
    match = _RETRY_DELAY.search(text)
    delay = float(match.group(1)) if match else None
    lowered = text.lower()

    if (
        429 in codes
        or "resource_exhausted" in lowered
        or re.search(r"\b429\b", text)
        or "rate limit" in lowered
    ):
        squashed = lowered.replace(" ", "").replace("_", "")
        if "perday" in squashed or "daily" in lowered:
            return "daily_quota", delay
        return "rate_limit", delay
    if codes & {400, 401, 403} or any(
        marker in text for marker in ("API key not valid", "PERMISSION_DENIED", "INVALID_ARGUMENT")
    ):
        return "fatal", None
    return "transient", None


class RateLimiter:
    """Thread-safe token bucket: `per_minute` calls per minute, small bursts allowed."""

    def __init__(
        self,
        per_minute: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._rate = max(per_minute, 0.1) / 60.0
        self._capacity = max(1.0, per_minute / 2)
        self._tokens = self._capacity
        self._clock = clock
        self._sleep = sleep
        self._updated = clock()
        self._lock = threading.Lock()

    def acquire(self, timeout: float) -> bool:
        """Take one token, waiting at most `timeout` seconds. False if that is not enough."""
        deadline = self._clock() + timeout
        while True:
            with self._lock:
                now = self._clock()
                self._tokens = min(
                    self._capacity, self._tokens + (now - self._updated) * self._rate
                )
                self._updated = now
                if self._tokens >= 1:
                    self._tokens -= 1
                    return True
                wait = (1 - self._tokens) / self._rate
            if now + wait > deadline:
                return False
            self._sleep(wait)


class DailyQuota:
    """Counts generation calls per model per quota day (in memory; resets on restart)."""

    def __init__(self, *, wall: Callable[[], float] = time.time) -> None:
        self._wall = wall
        self._day: date | None = None
        self._counts: dict[str, int] = {}
        self._lock = threading.Lock()

    def _roll(self) -> None:
        today = datetime.fromtimestamp(self._wall(), _QUOTA_TZ).date()
        if today != self._day:
            self._day, self._counts = today, {}

    def used(self, model: str) -> int:
        with self._lock:
            self._roll()
            return self._counts.get(model, 0)

    def record(self, model: str) -> None:
        with self._lock:
            self._roll()
            self._counts[model] = self._counts.get(model, 0) + 1


class CircuitBreaker:
    def __init__(
        self,
        threshold: int = 5,
        cooldown_s: float = 60,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._threshold = threshold
        self._cooldown = cooldown_s
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None
        self._probing = False
        self._lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        return self._opened_at is not None

    def allow(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return True
            if self._clock() - self._opened_at >= self._cooldown and not self._probing:
                self._probing = True  # half-open: let exactly one probe through
                return True
            return False

    def success(self) -> None:
        with self._lock:
            self._failures, self._opened_at, self._probing = 0, None, False

    def failure(self) -> None:
        with self._lock:
            self._failures += 1
            self._probing = False
            if self._failures >= self._threshold:
                self._opened_at = self._clock()


class _CallFailed(Exception):
    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind


class LLMGateway:
    def __init__(
        self,
        provider: LLMProvider,
        settings: Settings,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        wall: Callable[[], float] = time.time,
        rng: Callable[[], float] = random.random,
    ) -> None:
        self.provider = provider
        self._settings = settings
        self._clock = clock
        self._sleep = sleep
        self._rng = rng
        self.chat_limiter = RateLimiter(settings.llm_rpm_limit, clock=clock, sleep=sleep)
        self.embed_limiter = RateLimiter(settings.embedding_rpm_limit, clock=clock, sleep=sleep)
        # Ingestion uses at most half the embedding quota so live chat is not starved.
        self.ingest_limiter = RateLimiter(
            settings.embedding_rpm_limit / 2, clock=clock, sleep=sleep
        )
        self._slots = threading.BoundedSemaphore(settings.llm_max_concurrency)
        self.quota = DailyQuota(wall=wall)
        self.breaker = CircuitBreaker(clock=clock)
        self._chat_models: dict[bool, object] = {}
        self._embedder = None
        self._query_cache: OrderedDict[str, list[float]] = OrderedDict()
        self._cache_lock = threading.Lock()

    # ---- chat -----------------------------------------------------------------

    def generate(self, messages: list[BaseMessage], tools: Sequence = ()) -> Generation:
        """One chat call. `tools` (function definitions) are bound for function calling."""
        s = self._settings
        deadline = self._clock() + s.llm_request_timeout_s
        if not self.breaker.allow():
            raise LLMUnavailable("circuit breaker open")

        primary = self.provider.chat_model_name()
        fallback = self.provider.chat_model_name(fallback=True)
        has_fallback = self.provider.has_fallback
        use_fallback = has_fallback and self.quota.used(primary) >= 0.9 * s.llm_rpd_limit
        if self.quota.used(primary) >= s.llm_rpd_limit and (
            not has_fallback or self.quota.used(fallback) >= s.llm_rpd_limit
        ):
            raise LLMUnavailable("daily LLM quota used up")

        if not self._slots.acquire(timeout=s.llm_queue_max_wait_s):
            raise LLMUnavailable("no free LLM slot")
        try:
            if not self.chat_limiter.acquire(min(s.llm_queue_max_wait_s, deadline - self._clock())):
                raise LLMUnavailable("LLM rate limit queue is full")
            try:
                gen = self._retrying(lambda: self._invoke(messages, use_fallback, tools), deadline)
            except _CallFailed as exc:
                if use_fallback or not has_fallback or exc.kind == "fatal":
                    self.breaker.failure()
                    raise LLMUnavailable(f"LLM call failed ({exc.kind})") from exc
                log.warning("primary model failed (%s); trying %s once", exc.kind, fallback)
                try:
                    gen = self._retrying(lambda: self._invoke(messages, True, tools), deadline, 1)
                except _CallFailed as fb_exc:
                    self.breaker.failure()
                    raise LLMUnavailable(f"fallback model failed ({fb_exc.kind})") from fb_exc
        finally:
            self._slots.release()
        self.breaker.success()
        return gen

    def _chat(self, fallback: bool):
        if fallback not in self._chat_models:
            self._chat_models[fallback] = self.provider.chat_model(fallback=fallback)
        return self._chat_models[fallback]

    def _invoke(
        self, messages: list[BaseMessage], fallback: bool, tools: Sequence = ()
    ) -> Generation:
        name = self.provider.chat_model_name(fallback=fallback)
        model = self._chat(fallback)
        if tools:
            model = model.bind_tools(list(tools))
        self.quota.record(name)
        reply = model.invoke(messages)
        requests = tuple(
            ToolRequest(name=call["name"], args=dict(call.get("args") or {}))
            for call in getattr(reply, "tool_calls", None) or []
        )
        return Generation(text=message_text(reply), model=name, tool_requests=requests)

    # ---- embeddings -----------------------------------------------------------

    def _embeddings(self):
        if self._embedder is None:
            self._embedder = self.provider.embeddings()
        return self._embedder

    def embed_query(self, text: str) -> list[float]:
        with self._cache_lock:
            cached = self._query_cache.get(text)
            if cached is not None:
                self._query_cache.move_to_end(text)
                return cached
        s = self._settings
        deadline = self._clock() + s.llm_request_timeout_s
        if not self.embed_limiter.acquire(min(s.llm_queue_max_wait_s, s.llm_request_timeout_s)):
            raise LLMUnavailable("embedding rate limit queue is full")
        try:
            vector = normalise(
                self._retrying(lambda: self._embeddings().embed_query(text), deadline)
            )
        except _CallFailed as exc:
            raise LLMUnavailable(f"query embedding failed ({exc.kind})") from exc
        with self._cache_lock:
            self._query_cache[text] = vector
            if len(self._query_cache) > _QUERY_CACHE_SIZE:
                self._query_cache.popitem(last=False)
        return vector

    def embed_documents(self, texts: list[str], *, budget_s: float = 180) -> list[list[float]]:
        """Embed one ingestion batch (≤ 100 texts), paced at half the embedding RPM.

        Ingestion is a batch job, so it waits longer than chat for quota to come back.
        """
        deadline = self._clock() + budget_s
        self.ingest_limiter.acquire(budget_s)
        self.embed_limiter.acquire(budget_s)
        try:
            vectors = self._retrying(
                lambda: self._embeddings().embed_documents(texts), deadline, attempts=6
            )
        except _CallFailed as exc:
            raise LLMUnavailable(f"document embedding failed ({exc.kind})") from exc
        return [normalise(v) for v in vectors]

    # ---- shared retry loop ----------------------------------------------------

    def _retrying(
        self, call: Callable[[], T], deadline: float, attempts: int = _MAX_RETRY_ATTEMPTS
    ) -> T:
        for attempt in range(attempts):
            try:
                return call()
            except Exception as exc:
                kind, delay = classify_error(exc)
                log.warning("LLM call failed: %s (%s)", kind, type(exc).__name__)
                if kind != "rate_limit" or attempt == attempts - 1:
                    raise _CallFailed(kind) from exc
                if delay is None:
                    delay = self._rng() * _BACKOFF_BASE_S * 2 ** (attempt + 1)
                if self._clock() + delay > deadline:
                    raise _CallFailed(kind) from exc
                self._sleep(delay)
        raise _CallFailed("transient")  # only reached with attempts == 0


def message_text(message) -> str:
    """Plain text of a LangChain message whose content may be a list of parts."""
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    parts = []
    for part in content or []:
        if isinstance(part, str):
            parts.append(part)
        elif isinstance(part, dict) and part.get("type") == "text":
            parts.append(part.get("text", ""))
    return "".join(parts)
