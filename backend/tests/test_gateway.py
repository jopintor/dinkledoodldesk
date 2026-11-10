import math

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from tests_support import FakeClock

from app.llm import LLMGateway, LLMProviderError, LLMUnavailable
from app.llm.base import LLMProvider
from app.llm.gateway import CircuitBreaker, RateLimiter, classify_error, message_text, normalise


class ScriptedModel:
    """Each item is a reply string or an exception to raise."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def invoke(self, _messages):
        self.calls += 1
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return AIMessage(content=item)


class ScriptedProvider(LLMProvider):
    name = "scripted"

    def __init__(self, primary=(), fallback=(), embed=None):
        self.models = {False: ScriptedModel(primary), True: ScriptedModel(fallback)}
        self._embed = embed

    def chat_model(self, *, fallback=False):
        return self.models[fallback]

    def chat_model_name(self, *, fallback=False):
        return "fallback-model" if fallback else "primary-model"

    def embeddings(self):
        return self._embed

    def embedding_model_name(self):
        return "scripted-embed"

    def is_configured(self):
        return True


def gateway(settings, provider, clock=None, **overrides):
    clock = clock or FakeClock()
    s = settings.model_copy(update={"llm_rpm_limit": 600, **overrides})
    return LLMGateway(provider, s, clock=clock, sleep=clock.sleep, wall=clock, rng=lambda: 0.5)


MESSAGES = [HumanMessage("hi")]


def test_rate_limit_retries_honour_server_delay(settings):
    clock = FakeClock()
    provider = ScriptedProvider(
        primary=[RuntimeError("429 RESOURCE_EXHAUSTED retryDelay: '3s'"), "ok"]
    )
    result = gateway(settings, provider, clock).generate(MESSAGES)
    assert (result.text, result.model) == ("ok", "primary-model")
    assert clock.sleeps == [3.0]


def test_falls_back_once_after_retries_are_used_up(settings):
    rate_limited = RuntimeError("429 RESOURCE_EXHAUSTED")
    provider = ScriptedProvider(primary=[rate_limited] * 3, fallback=["from fallback"])
    clock = FakeClock()
    result = gateway(settings, provider, clock).generate(MESSAGES)
    assert result.model == "fallback-model"
    assert provider.models[False].calls == 3
    assert clock.sleeps == [1.0, 2.0]  # full jitter with rng=0.5: 0.5 × 2, 0.5 × 4


def test_server_error_goes_straight_to_fallback(settings):
    provider = ScriptedProvider(primary=[RuntimeError("503 UNAVAILABLE")], fallback=["ok"])
    assert gateway(settings, provider).generate(MESSAGES).model == "fallback-model"
    assert provider.models[False].calls == 1


def test_bad_key_does_not_fall_back(settings):
    provider = ScriptedProvider(primary=[LLMProviderError("GEMINI_API_KEY is not set")])
    with pytest.raises(LLMUnavailable):
        gateway(settings, provider).generate(MESSAGES)
    assert provider.models[True].calls == 0


def test_backoff_never_exceeds_the_request_budget(settings):
    provider = ScriptedProvider(primary=[RuntimeError("429 retry in 60s")], fallback=["ok"])
    clock = FakeClock()
    result = gateway(settings, provider, clock).generate(MESSAGES)
    assert result.model == "fallback-model" and clock.sleeps == []


def test_daily_quota_switches_to_fallback(settings):
    provider = ScriptedProvider(primary=["primary"] * 3, fallback=["fallback"])
    gw = gateway(settings, provider, llm_rpd_limit=2)  # fallback from 90 % = 1.8 calls
    assert [gw.generate(MESSAGES).model for _ in range(3)] == ["primary-model"] * 2 + [
        "fallback-model"
    ]


def test_circuit_breaker_opens_and_probes():
    clock = FakeClock()
    breaker = CircuitBreaker(threshold=2, cooldown_s=60, clock=clock)
    breaker.failure()
    breaker.failure()
    assert not breaker.allow()
    clock.t += 61
    assert breaker.allow() and not breaker.allow()  # exactly one probe
    breaker.success()
    assert breaker.allow()


def test_gateway_reports_unavailable_while_breaker_is_open(settings):
    failures = [RuntimeError("503")] * 10
    provider = ScriptedProvider(primary=failures, fallback=failures)
    gw = gateway(settings, provider)
    for _ in range(5):
        with pytest.raises(LLMUnavailable):
            gw.generate(MESSAGES)
    calls = provider.models[False].calls
    with pytest.raises(LLMUnavailable, match="circuit"):
        gw.generate(MESSAGES)
    assert provider.models[False].calls == calls


def test_rate_limiter_waits_then_gives_up():
    clock = FakeClock()
    limiter = RateLimiter(2, clock=clock, sleep=clock.sleep)  # capacity 1, one token per 30 s
    assert limiter.acquire(timeout=0)
    assert not limiter.acquire(timeout=10)
    assert limiter.acquire(timeout=40)
    assert clock.sleeps == [pytest.approx(30)]


def test_query_embeddings_are_normalised_and_cached(settings):
    class Embed:
        calls = 0

        def embed_query(self, _text):
            Embed.calls += 1
            return [3.0, 4.0]

    gw = gateway(settings, ScriptedProvider(embed=Embed()))
    assert gw.embed_query("q") == [0.6, 0.8]
    gw.embed_query("q")
    assert Embed.calls == 1


@pytest.mark.parametrize(
    ("message", "kind", "delay"),
    [
        ("429 RESOURCE_EXHAUSTED. Please retry in 12.5s.", "rate_limit", 12.5),
        (
            "RESOURCE_EXHAUSTED quotaId: GenerateRequestsPerDayPerProjectPerModel",
            "daily_quota",
            None,
        ),
        ("400 INVALID_ARGUMENT", "fatal", None),
        ("404 models/gemini-x is not found", "transient", None),
        ("Request id 4291 timed out", "transient", None),
    ],
)
def test_classify_error(message, kind, delay):
    assert classify_error(RuntimeError(message)) == (kind, delay)


def test_message_text_and_normalise_helpers():
    assert message_text(AIMessage(content=[{"type": "text", "text": "a"}, "b"])) == "ab"
    assert math.isclose(sum(v * v for v in normalise([1.0, 2.0, 2.0])), 1.0)
