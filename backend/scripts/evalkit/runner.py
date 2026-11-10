"""Run the golden set against a target, judge the answers, and write the outputs.

Two phases, so the judge never competes with DinkDesk for the same per-minute quota:
1. ask every question (`ask_all`), 2. judge the answered ones (`judge_all`).
"""

import json
import subprocess
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from evalkit import report
from evalkit.golden import DATASET_VERSION
from evalkit.judge import Judge
from evalkit.metrics import Observation, aggregate, classify_behavior, item_passed, retrieval_scores

JUDGED_MODES = ("generated", "cached")
MAX_JUDGE_CONTEXT_CHUNKS = 5


def score_item(item: dict, obs: Observation) -> dict:
    """One result row: the golden item, what DinkDesk did, and the deterministic scores."""
    actual = classify_behavior(obs)
    expected = item["expected_source_ids"]
    result = {
        "id": item["id"],
        "user_role": item["user_role"],
        "category": item["category"],
        "question": item["question"],
        "expected_behavior": item["expected_behavior"],
        "actual_behavior": actual,
        "behavior_ok": actual == item["expected_behavior"],
        "expected_source_ids": expected,
        "retrieved_doc_ids": obs.retrieved_doc_ids,
        "retrieval": retrieval_scores(expected, obs.retrieved_doc_ids) if expected else None,
        # The KPI uses the service's own latency (messages.latency_ms); wall_ms adds network.
        "latency_ms": obs.server_latency_ms
        if obs.server_latency_ms is not None
        else obs.latency_ms,
        "wall_ms": obs.latency_ms,
        "answer_mode": obs.answer_mode,
        "predicted_intent": obs.intent,
        "observation": obs.to_dict(),
        "judge": None,
    }
    result["passed"] = item_passed(result)
    return result


def ask_all(
    items: list[dict],
    target,
    *,
    pace_s: float = 0,
    sleep: Callable[[float], None] = time.sleep,
    echo: Callable[[str], None] = print,
) -> list[dict]:
    results = []
    for n, item in enumerate(items, start=1):
        if n > 1 and pace_s:
            sleep(pace_s)
        obs = target.ask(item["question"], item["user_role"])
        row = score_item(item, obs)
        results.append(row)
        mark = "ok  " if row["behavior_ok"] else "FAIL"
        hit = ""
        if row["retrieval"] is not None:
            hit = " hit@5" if row["retrieval"]["hit@5"] else " MISS@5"
        echo(
            f"[{n:>2}/{len(items)}] {mark} {row['id']} {row['category'][:12]:<12} "
            f"expected={row['expected_behavior']:<26} got={row['actual_behavior']:<26} "
            f"{row['answer_mode'] or '-':<9} {row['latency_ms']:>6} ms{hit}"
            + (f"  ERROR {obs.error}" if obs.error else "")
        )
    return results


def judge_context(result: dict, texts: dict[str, str]) -> str:
    chunk_ids = result["observation"]["retrieved_chunk_ids"][:MAX_JUDGE_CONTEXT_CHUNKS]
    return "\n\n".join(
        f"[{n}] {texts.get(cid, f'({cid}: text not found in local KB)')}"
        for n, cid in enumerate(chunk_ids, start=1)
    )


def should_judge(result: dict) -> bool:
    return (
        result["actual_behavior"] == "answer"
        and result["answer_mode"] in JUDGED_MODES
        and result["judge"] is None
        and bool(result["observation"]["content"])
    )


def judge_all(
    results: list[dict],
    items_by_id: dict[str, dict],
    judge: Judge,
    texts: dict[str, str],
    *,
    echo: Callable[[str], None] = print,
) -> None:
    todo = [r for r in results if should_judge(r)]
    echo(f"\nJudging {len(todo)} answered items with {judge.model or 'the judge model'} ...")
    for n, result in enumerate(todo, start=1):
        item = items_by_id.get(result["id"], {})
        verdict = judge.score(
            question=result["question"],
            reference=item.get("reference_answer", ""),
            context=judge_context(result, texts),
            answer=result["observation"]["content"],
        )
        if judge.stopped and verdict is None:
            echo(f"Judge stopped: {judge.stopped}. {len(todo) - n + 1} items left unjudged.")
            break
        result["judge"] = verdict
        result["passed"] = item_passed(result)
        if verdict:
            f = verdict["faithfulness"]
            echo(
                f"[{n:>2}/{len(todo)}] {result['id']} faithfulness="
                f"{'-' if f is None else f'{f:.2f}'} relevance={verdict['relevance']} "
                f"correctness={verdict['correctness']}"
            )
        else:
            echo(f"[{n:>2}/{len(todo)}] {result['id']} judge gave no usable verdict")


def git_sha() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).parent,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip() or None


def build_run(meta: dict, results: list[dict]) -> dict:
    prompt_versions = {r["observation"].get("prompt_version") for r in results} - {None}
    models = {r["observation"].get("model") for r in results} - {None}
    return {
        "label": meta["label"],
        "dataset_version": DATASET_VERSION,
        "prompt_version": meta.get("prompt_version") or ",".join(sorted(prompt_versions)) or None,
        "model_name": meta.get("model_name") or ",".join(sorted(models)) or None,
        "git_sha": meta.get("git_sha"),
        "n_questions": len(results),
        "notes": meta.get("notes", ""),
        "started_at": meta.get("started_at"),
        "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "config": {k: v for k, v in meta.items() if k not in ("label", "notes")},
        "metrics": aggregate(results),
        "results": results,
    }


def api_payload(run: dict) -> dict:
    """Body for `POST /api/v1/eval/runs` (docs/api.md §9)."""
    m = run["metrics"]
    keys = (
        "faithfulness", "answer_relevance", "context_precision", "behavior_accuracy",
        "refusal_accuracy", "retrieval_hit_rate", "deflection_rate", "p50_ms", "p95_ms",
    )  # fmt: skip
    return {
        "label": run["label"],
        "dataset_version": run["dataset_version"],
        "prompt_version": run["prompt_version"],
        "model_name": run["model_name"],
        "git_sha": run["git_sha"],
        "metrics": {k: m[k] for k in keys},
        "results": [
            {
                "question_id": r["id"],
                "user_role": r["user_role"],
                "category": r["category"],
                "expected_behavior": r["expected_behavior"],
                "actual_behavior": r["actual_behavior"],
                "predicted_intent": r["predicted_intent"],
                "expected_source_ids": r["expected_source_ids"],
                "retrieved_doc_ids": r["retrieved_doc_ids"],
                "passed": r["passed"],
                "latency_ms": r["latency_ms"],
                "scores": {"retrieval": r["retrieval"], "judge": r["judge"]},
            }
            for r in run["results"]
        ],
    }


def write_outputs(run: dict, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "run": out_dir / "run.json",
        "metrics": out_dir / "metrics.json",
        "payload": out_dir / "eval_run_payload.json",
        "report": out_dir / "report.md",
    }
    meta = {k: v for k, v in run.items() if k not in ("results", "metrics")}
    paths["run"].write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
    paths["metrics"].write_text(
        json.dumps({**meta, "metrics": run["metrics"]}, indent=2), encoding="utf-8"
    )
    paths["payload"].write_text(json.dumps(api_payload(run), indent=2), encoding="utf-8")
    paths["report"].write_text(report.render(run), encoding="utf-8")
    return paths
