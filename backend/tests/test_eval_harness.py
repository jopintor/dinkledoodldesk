"""Eval harness (scripts/evalkit): metric maths, judge parsing, targets, end-to-end run.

All offline: fake LLM provider, hashed embeddings, in-memory Chroma, httpx MockTransport.
"""

import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from evalkit import report, runner  # noqa: E402
from evalkit.golden import load_items  # noqa: E402
from evalkit.judge import Judge, parse_verdict  # noqa: E402
from evalkit.metrics import (  # noqa: E402
    Observation,
    aggregate,
    classify_behavior,
    doc_id_of,
    item_passed,
    percentile,
    retrieval_scores,
)
from evalkit.targets import HttpTarget, InProcessTarget, chunk_texts  # noqa: E402

from app.llm import LLMUnavailable  # noqa: E402
from app.rag.cache import ResponseCache  # noqa: E402
from app.rag.service import RagService  # noqa: E402

# ---- metric maths -------------------------------------------------------------


def test_percentile_matches_numpy_linear():
    values = [100, 200, 300, 400, 1000]
    assert percentile(values, 50) == 300
    assert percentile(values, 95) == pytest.approx(880)  # 400 + 0.8 * 600
    assert percentile([42], 95) == 42
    assert percentile([], 50) is None


def test_retrieval_scores():
    s = retrieval_scores(["KB-001", "KB-002"], ["KB-003", "KB-001", "KB-009", "KB-002"])
    assert (s["hit@1"], s["hit@3"], s["hit@5"]) == (False, True, True)
    assert s["recall@5"] == 1.0
    assert s["rr"] == 0.5
    # relevant at ranks 2 and 4: (1/2 + 2/4) / 2
    assert s["context_precision"] == pytest.approx(0.5)

    miss = retrieval_scores(["KB-007"], ["KB-001", "KB-002"])
    assert not miss["hit@5"] and miss["rr"] == 0 and miss["context_precision"] == 0


def test_doc_id_of():
    assert doc_id_of("KB-011-c03") == "KB-011"


@pytest.mark.parametrize(
    ("obs", "expected"),
    [
        (Observation(action="answer", answer_mode="generated"), "answer"),
        (Observation(action="answer", answer_mode="cached"), "answer"),
        (Observation(action="clarify", answer_mode="template"), "clarify"),
        (Observation(action="escalate", escalate=True), "escalate"),
        (Observation(action="escalate", escalate=False), "escalate"),  # low-confidence hand-off
        (Observation(answer_mode="refusal"), "refuse"),
        (Observation(refused=True, action="answer"), "refuse"),
        (Observation(tool_calls=["create_ticket"], action="answer"), "call_tool:create_ticket"),
        (Observation(tool_calls=["escalate_to_agent"], action="answer"), "escalate"),
        (Observation(error="boom"), "error"),
    ],
)
def test_classify_behavior(obs, expected):
    assert classify_behavior(obs) == expected


def _row(id_, category, expected, actual, *, mode="generated", latency=1000, retrieval=None,
         judge=None):  # fmt: skip
    row = {
        "id": id_,
        "category": category,
        "expected_behavior": expected,
        "actual_behavior": actual,
        "answer_mode": mode,
        "latency_ms": latency,
        "retrieval": retrieval,
        "judge": judge,
    }
    row["passed"] = item_passed(row)
    return row


HIT = retrieval_scores(["KB-001"], ["KB-001", "KB-002"])
MISS = retrieval_scores(["KB-001"], ["KB-005"])


def test_aggregate():
    results = [
        _row("A", "normal", "answer", "answer", retrieval=HIT,
             judge={"faithfulness": 1.0, "relevance": 1.0, "correctness": 0.8}),
        _row("B", "normal", "answer", "escalate", mode="template", latency=200, retrieval=MISS),
        _row("C", "normal", "answer", "answer", mode="cached", latency=50, retrieval=HIT,
             judge={"faithfulness": 0.5, "relevance": 0.6, "correctness": None}),
        _row("D", "malicious_prompt_injection", "refuse", "refuse", mode="refusal", latency=10),
        _row("E", "unsupported", "refuse", "escalate", mode="template", latency=150),
        _row("F", "low_confidence", "escalate", "answer", latency=3000),
        _row("G", "action_request", "call_tool:create_ticket", "call_tool:create_ticket"),
        _row("H", "ambiguous", "clarify", "call_tool:reset_password"),
    ]  # fmt: skip
    m = aggregate(results)
    assert m["questions"] == 8
    assert m["behavior_accuracy"] == pytest.approx(4 / 8)
    assert m["behavior_by_category"]["normal"] == {"n": 3, "correct": 2, "accuracy": 0.6667}
    # D refused, E escalated: both count for refusal accuracy, only D is a guardrail block.
    assert m["refusal_accuracy"] == 1.0
    assert m["guardrail_block_rate"] == 1.0
    # answer/call_tool items: A, B, C, G -> A, C, G resolved by DinkDesk
    assert m["deflection_rate"] == 0.75
    assert m["tool_success_rate"] == 1.0
    assert m["faithfulness"] == 0.75
    assert m["answer_relevance"] == 0.8
    assert m["answer_correctness"] == 0.8  # None is skipped
    assert m["retrieval"]["n"] == 3
    assert m["retrieval_hit_rate"] == pytest.approx(0.6667)
    assert m["safety_misses"] == ["F"]
    assert m["over_escalations"] == ["B"]
    assert m["false_tool_calls"] == ["H"]
    assert m["confusion"]["answer"] == {"answer": 2, "escalate": 1}
    assert m["cache_hit_rate"] == 0.125
    assert m["p50_uncached_ms"] is not None and m["p50_ms"] == 600  # median of 8 latencies
    # A passes; C fails on faithfulness 0.5 < 0.8; B wrong behaviour.
    assert [r["id"] for r in results if r["passed"]] == ["A", "D", "G"]


# ---- judge ----------------------------------------------------------------------


def test_parse_verdict_counts_claims_itself():
    text = """```json
    {"claims": [{"claim": "locks after 5 tries", "verdict": "SUPPORTED"},
                {"claim": "unlocks after 30 minutes", "verdict": "UNSUPPORTED"},
                {"claim": "junk", "verdict": "MAYBE"}],
     "faithfulness": 0.99, "relevance": 1.4, "correctness": "0.5", "note": "ok"}
    ```"""
    v = parse_verdict(text)
    assert v["faithfulness"] == 0.5  # 1 of 2 valid claims, not the model's 0.99
    assert v["claims"] == 2
    assert v["unsupported_claims"] == ["unlocks after 30 minutes"]
    assert v["relevance"] == 1.0  # clamped
    assert v["correctness"] == 0.5


def test_parse_verdict_rejects_garbage():
    assert parse_verdict("I think it is fine") is None
    assert parse_verdict("{not json}") is None
    assert parse_verdict('{"claims": [], "relevance": 1}')["faithfulness"] is None


def test_judge_waits_and_retries_when_quota_queue_is_full():
    sleeps, replies = [], [LLMUnavailable("LLM rate limit queue is full"), '{"claims": []}']

    def generate(prompt):
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        assert "QUESTION:\nq" in prompt
        return reply

    judge = Judge(generate, sleep=sleeps.append, retry_waits_s=(7,),
                  is_unavailable=lambda e: isinstance(e, LLMUnavailable))  # fmt: skip
    assert judge.score(question="q", reference="r", context="c", answer="a") is not None
    assert sleeps == [7]
    assert judge.calls == 2


def test_judge_stops_on_daily_quota_and_budget():
    def exhausted(prompt):
        raise LLMUnavailable("daily LLM quota used up")

    judge = Judge(exhausted, sleep=lambda s: None)
    assert judge.score(question="q", reference="r", context="c", answer="a") is None
    assert "daily" in judge.stopped
    assert judge.score(question="q", reference="r", context="c", answer="a") is None
    assert judge.calls == 1  # no more calls once stopped

    budget = Judge(lambda p: '{"claims": []}', max_calls=1)
    assert budget.score(question="q", reference="", context="", answer="a") is not None
    assert budget.score(question="q", reference="", context="", answer="a") is None
    assert "max-judge-calls" in budget.stopped


def test_judge_does_not_swallow_programming_errors():
    def broken(prompt):
        raise KeyError("bug")

    judge = Judge(broken, is_unavailable=lambda e: isinstance(e, LLMUnavailable))
    with pytest.raises(KeyError):
        judge.score(question="q", reference="", context="", answer="a")


# ---- HTTP target ------------------------------------------------------------------


def _fake_api(calls: list):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path, request.headers.get("authorization")))
        body = json.loads(request.content or b"{}")
        if request.url.path == "/api/v1/auth/login":
            return httpx.Response(200, json={"access_token": f"tok-{body['email']}"})
        if request.url.path == "/api/v1/rag/ask":
            if len([c for c in calls if c[1] == "/api/v1/rag/ask"]) == 1:
                return httpx.Response(503, headers={"retry-after": "0"})  # tunnel hiccup
            return httpx.Response(
                200,
                json={
                    "assistant_message": {
                        "content": "Reset it at the portal [1].",
                        "answer_mode": "generated",
                        "action": "answer",
                        "intent": None,
                        "confidence": 0.8,
                        "citations": [{"n": 1, "doc_id": "KB-001", "chunk_id": "KB-001-c01"}],
                        "model_name": "gemini-x",
                        "prompt_version": "v1",
                        "latency_ms": 1234,
                    },
                    "tool_calls": [],
                    "escalation_required": False,
                },
            )
        if request.url.path == "/api/v1/kb/search":
            assert body["as_role"] == "staff"
            return httpx.Response(
                200,
                json={
                    "confidence": 0.81,
                    "band": "high",
                    "results": [{"chunk_id": "KB-001-c01"}, {"chunk_id": "KB-001-c02"},
                                {"chunk_id": "KB-002-c00"}],
                },
            )  # fmt: skip
        return httpx.Response(404)

    return handler


def test_http_target_signs_in_per_role_and_reads_the_response():
    calls: list = []
    client = httpx.Client(base_url="https://tunnel.test", transport=httpx.MockTransport(
        _fake_api(calls)))  # fmt: skip
    target = HttpTarget("https://tunnel.test/", client=client, sleep=lambda s: None)
    obs = target.ask("I forgot my StaffID password", "staff")

    assert obs.error is None
    assert classify_behavior(obs) == "answer"
    assert obs.retrieved_doc_ids == ["KB-001", "KB-002"]
    assert obs.cited_doc_ids == ["KB-001"]
    assert obs.server_latency_ms == 1234 and obs.prompt_version == "v1"
    ask_calls = [c for c in calls if c[1] == "/api/v1/rag/ask"]
    assert len(ask_calls) == 2  # retried after the 503
    assert ask_calls[0][2] == "Bearer tok-staff@picklehub.example"
    search = next(c for c in calls if c[1] == "/api/v1/kb/search")
    assert search[2] == "Bearer tok-admin1@picklehub.example"


def test_http_target_reports_errors_instead_of_crashing():
    client = httpx.Client(
        base_url="https://t.test", transport=httpx.MockTransport(lambda r: httpx.Response(500))
    )
    obs = HttpTarget("https://t.test", client=client, sleep=lambda s: None).ask("q", "member")
    assert obs.error and classify_behavior(obs) == "error"


# ---- end to end, in-process with the fake provider -------------------------------


def test_end_to_end_run_writes_metrics_and_report(indexed_kb, tmp_path):
    settings, store, gateway = indexed_kb
    from app.rag.retriever import Retriever

    # Hashed fake embeddings have low cosines; rescale so the top hits land in the high band.
    settings = settings.model_copy(update={"rag_cosine_floor": 0.0, "rag_cosine_ceiling": 0.25})

    service = RagService(settings, gateway, Retriever(store, gateway.embed_query, settings),
                         ResponseCache(None, 0))  # fmt: skip
    items = load_items(ids=["GS-001", "GS-002", "GS-004"]) + load_items(
        categories=["ambiguous"], limit=1
    )
    lines: list[str] = []
    results = runner.ask_all(items, InProcessTarget(service), echo=lines.append)
    assert len(results) == len(lines) == 4
    assert results[-1]["actual_behavior"] == "clarify"
    assert all(r["retrieval"] for r in results[:3])

    replies = iter(
        ['{"claims": [{"claim": "x", "verdict": "SUPPORTED"}], "relevance": 1, '
         '"correctness": 0.5}'] * 10
    )  # fmt: skip
    prompts: list[str] = []
    judge = Judge(lambda p: prompts.append(p) or next(replies), model="fake-judge")
    runner.judge_all(results, {i["id"]: i for i in items}, judge,
                     chunk_texts(settings.kb_dir), echo=lines.append)  # fmt: skip
    judged = [r for r in results if r["judge"]]
    assert judged and all(r["actual_behavior"] == "answer" for r in judged)
    assert "text not found" not in prompts[0]  # chunk text came from the local KB

    run = runner.build_run({"label": "test", "target": "in-process"}, results)
    paths = runner.write_outputs(run, tmp_path / "run")
    metrics = json.loads(paths["metrics"].read_text())["metrics"]
    for key in ("faithfulness", "answer_relevance", "behavior_accuracy", "retrieval_hit_rate",
                "p50_ms", "p95_ms", "deflection_rate"):  # fmt: skip
        assert key in metrics
    assert metrics["faithfulness"] == 1.0
    payload = json.loads(paths["payload"].read_text())
    assert payload["results"][0]["question_id"] == "GS-001"
    md = paths["report"].read_text(encoding="utf-8")
    assert "## Headline metrics" in md and "| Normal | 3 |" in md


def test_report_renders_without_judge_or_results():
    run = runner.build_run({"label": "empty"}, [])
    text = report.render(run)
    assert "not run (optional" in text
    assert "all items passed" in text
