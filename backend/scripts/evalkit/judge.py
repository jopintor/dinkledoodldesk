"""LLM-as-judge (prompt P8 in docs/ai-design.md §8), one call per answered question.

The single call returns the claims with SUPPORTED / UNSUPPORTED verdicts (faithfulness),
a 0-1 answer-relevance score and a 0-1 correctness score against the reference answer.
Faithfulness is computed here from the verdicts, not taken from the model's arithmetic.

The judge only needs a `generate(prompt) -> text` function, so tests pass a fake one and
the runner passes the backend's `LLMGateway` (rate limiter, retries, model fallback).
On top of that the judge waits and retries when the gateway reports the quota queue is
full, and stops judging for the rest of the run once the daily quota is gone.
"""

import json
import logging
import re
import time
from collections.abc import Callable

log = logging.getLogger(__name__)

JUDGE_VERSION = "j1"

JUDGE_PROMPT = """\
You are grading one reply from DinkDesk, an IT helpdesk assistant. Reply with JSON only.

1. Split the ANSWER into short factual claims (steps, numbers, names, rules). Skip greetings,
   offers of further help and questions back to the user. For each claim give the verdict
   SUPPORTED if the CONTEXT states it, otherwise UNSUPPORTED. A number, time limit, URL or
   phone number that differs from the CONTEXT is UNSUPPORTED.
2. relevance: from 0 to 1, how well the ANSWER addresses the QUESTION (1 = fully,
   0.5 = partly or padded with unrelated steps, 0 = off-topic or no answer). Judge only
   relevance here, not truth.
3. correctness: from 0 to 1, how much of the REFERENCE answer's key facts the ANSWER gets
   right without contradicting it (1 = all key facts, 0 = none or contradicts it).

Return exactly:
{{"claims": [{{"claim": "...", "verdict": "SUPPORTED"}}],
 "relevance": 0.0, "correctness": 0.0, "note": "one short sentence"}}

QUESTION:
{question}

REFERENCE:
{reference}

CONTEXT:
{context}

ANSWER:
{answer}
"""

_JSON = re.compile(r"\{.*\}", re.DOTALL)
# Errors from the gateway that mean "wait and try again" vs "stop for today".
_DAILY = re.compile(r"daily", re.I)


class JudgeQuotaExhausted(RuntimeError):
    """The daily LLM quota is used up: skip judging for the rest of the run."""


def _clamp(value) -> float | None:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return None


def parse_verdict(text: str) -> dict | None:
    """Scores from the judge's reply, or None when it is not usable JSON."""
    match = _JSON.search(text or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    claims = [
        c
        for c in data.get("claims") or []
        if isinstance(c, dict) and str(c.get("verdict", "")).upper() in ("SUPPORTED", "UNSUPPORTED")
    ]
    supported = sum(str(c["verdict"]).upper() == "SUPPORTED" for c in claims)
    return {
        "faithfulness": round(supported / len(claims), 4) if claims else None,
        "claims": len(claims),
        "unsupported_claims": [
            str(c.get("claim", ""))[:200]
            for c in claims
            if str(c["verdict"]).upper() == "UNSUPPORTED"
        ],
        "relevance": _clamp(data.get("relevance")),
        "correctness": _clamp(data.get("correctness")),
        "note": str(data.get("note", ""))[:300],
    }


class Judge:
    def __init__(
        self,
        generate: Callable[[str], str],
        *,
        model: str | None = None,
        max_calls: int | None = None,
        retry_waits_s: tuple[float, ...] = (15, 30, 60),
        sleep: Callable[[float], None] = time.sleep,
        is_unavailable: Callable[[BaseException], bool] = lambda exc: True,
    ) -> None:
        """`generate(prompt)` returns the model's text. `is_unavailable(exc)` says whether
        an exception is a quota / availability error worth waiting for."""
        self._generate = generate
        self.model = model
        self.max_calls = max_calls
        self.calls = 0
        self.stopped: str | None = None
        self._waits = retry_waits_s
        self._sleep = sleep
        self._is_unavailable = is_unavailable

    def score(self, *, question: str, reference: str, context: str, answer: str) -> dict | None:
        """Judge one answer. None when the judge is stopped, out of budget or unparseable."""
        if self.stopped:
            return None
        if self.max_calls is not None and self.calls >= self.max_calls:
            self.stopped = f"--max-judge-calls={self.max_calls} reached"
            return None
        prompt = JUDGE_PROMPT.format(
            question=question,
            reference=reference or "(none)",
            context=context or "(no context was retrieved)",
            answer=answer,
        )
        text = self._call(prompt)
        if text is None:
            return None
        verdict = parse_verdict(text)
        if verdict is None:
            log.warning("judge reply was not JSON: %.120s", text)
            return None
        verdict["judge_model"] = self.model
        verdict["judge_version"] = JUDGE_VERSION
        return verdict

    def _call(self, prompt: str) -> str | None:
        for attempt in range(len(self._waits) + 1):
            self.calls += 1
            try:
                return self._generate(prompt)
            except Exception as exc:
                if not self._is_unavailable(exc):
                    raise
                if _DAILY.search(str(exc)):
                    self.stopped = f"daily quota: {exc}"
                    log.warning("judge stopped: %s", exc)
                    return None
                if attempt == len(self._waits):
                    log.warning("judge gave up on this item: %s", exc)
                    return None
                wait = self._waits[attempt]
                log.warning("judge call unavailable (%s); waiting %ss", exc, wait)
                self._sleep(wait)
        return None
