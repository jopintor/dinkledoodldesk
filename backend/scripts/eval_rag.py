"""Run the golden set end to end and write metrics + a Markdown report.

Run from `backend/` (see eval/README.md for the full guide):

    python scripts/eval_rag.py                                  # in-process, all 50, no judge
    python scripts/eval_rag.py --base-url https://xyz.trycloudflare.com
    python scripts/eval_rag.py --judge                          # optional LLM judge (spends quota)
    python scripts/eval_rag.py --category normal --ids GS-001,GS-002
    python scripts/eval_rag.py --from ../eval/results/<run>/run.json   # judge / re-report later

Writes `eval/results/<date>-<label>/` with run.json (everything), metrics.json,
eval_run_payload.json (body for POST /api/v1/eval/runs) and report.md.

LLM cost per run (Gemini free tier): one generation call per question that reaches the LLM
(templates and low-confidence items make none), about 35 for all 50. The LLM judge
(faithfulness / relevance) is optional and off by default; with --judge it adds one call per
answered question, runs after all questions are asked, and stops if the daily quota runs out.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from evalkit import runner
from evalkit.golden import GOLDEN, RESULTS_DIR, load_items
from evalkit.judge import Judge


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--base-url", help="call a running API (e.g. a Cloudflare tunnel) over HTTP")
    p.add_argument("--golden", type=Path, default=GOLDEN)
    p.add_argument(
        "--category", default="all", help='comma-separated categories, or "all" (default)'
    )
    p.add_argument("--ids", help="comma-separated golden ids, e.g. GS-001,GS-019")
    p.add_argument("--limit", type=int, help="only the first N items (after filters)")
    p.add_argument("--label", help="run name (default: prompt version + target)")
    p.add_argument("--notes", default="", help="free text stored with the run")
    p.add_argument("--out", type=Path, help="output folder (default: eval/results/<date>-<label>)")
    p.add_argument(
        "--judge", action="store_true", help="optional: run the LLM judge (spends Gemini quota)"
    )
    p.add_argument("--no-judge", action="store_true", help=argparse.SUPPRESS)  # old default
    p.add_argument("--max-judge-calls", type=int, default=60, help="judge call budget (default 60)")
    p.add_argument(
        "--pace", type=float, help="seconds between questions (default 0 in-process, 3 over HTTP)"
    )
    p.add_argument(
        "--use-cache",
        action="store_true",
        help="in-process: allow the response cache (default: always generate fresh answers)",
    )
    p.add_argument("--ingest", action="store_true", help="in-process: ingest the KB first")
    p.add_argument(
        "--credentials",
        type=Path,
        help='JSON {"member": ["email", "password"], ...} (default: seeded demo users)',
    )
    p.add_argument(
        "--from",
        dest="from_run",
        type=Path,
        help="load an earlier run.json: judge what is not judged yet and rewrite the report",
    )
    args = p.parse_args(argv)
    args.no_judge = not args.judge
    return args


def make_gateway_judge(gateway, max_calls: int) -> Judge:
    from langchain_core.messages import HumanMessage

    from app.llm import LLMUnavailable

    return Judge(
        lambda prompt: gateway.generate([HumanMessage(prompt)]).text,
        model=gateway.provider.chat_model_name(),
        max_calls=max_calls,
        is_unavailable=lambda exc: isinstance(exc, LLMUnavailable),
    )


def local_gateway():
    """A gateway from this PC's settings, for the judge in HTTP / --from mode."""
    from app.config import get_settings
    from app.llm import LLMGateway, get_llm_provider

    settings = get_settings()
    provider = get_llm_provider(settings)
    if not provider.is_configured():
        return None
    return LLMGateway(provider, settings)


def build_in_process_target(args):
    from evalkit.targets import InProcessTarget

    from app.rag.ingest import ingest_knowledge_base
    from app.rag.service import get_rag_service
    from app.rag.store import KBStore, collection_name, make_client

    service = get_rag_service()
    settings = service.settings
    store = KBStore(
        make_client(settings),
        collection_name(settings, service.gateway.provider.embedding_model_name()),
    )
    if args.ingest:
        report = ingest_knowledge_base(settings.kb_dir, store, service.gateway.embed_documents)
        print(report.summary(), end="\n\n")
        if not report.ok:
            raise SystemExit(1)
        service.retriever.refresh()
    if service.retriever.chunk_count == 0:
        raise SystemExit(
            f"Collection {store.name} is empty: run "
            "`python -m app.rag.ingest` first (or pass --ingest)."
        )
    return InProcessTarget(service, use_cache=args.use_cache)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    from evalkit.targets import HttpTarget, chunk_texts

    from app.config import get_settings

    settings = get_settings()
    started = datetime.now(UTC)

    if args.from_run:
        run = json.loads(args.from_run.read_text(encoding="utf-8"))
        results = run["results"]
        meta = {**run["config"], "label": run["label"], "notes": run.get("notes", "")}
        meta.update(git_sha=run.get("git_sha"), prompt_version=run.get("prompt_version"))
        meta["model_name"] = run.get("model_name")
        items = load_items(args.golden)
        out_dir = args.out or args.from_run.parent
        gateway = None if args.no_judge else local_gateway()
    else:
        categories = [c.strip() for c in args.category.split(",") if c.strip()]
        ids = [i.strip() for i in args.ids.split(",")] if args.ids else None
        items = load_items(args.golden, categories=categories, ids=ids, limit=args.limit)
        if not items:
            print("No golden items match those filters.")
            return 1

        if args.base_url:
            users = None
            if args.credentials:
                users = {
                    k: tuple(v)
                    for k, v in json.loads(args.credentials.read_text(encoding="utf-8")).items()
                }
            target = HttpTarget(args.base_url, users=users)
            gateway = None if args.no_judge else local_gateway()
            pace = 3.0 if args.pace is None else args.pace
        else:
            target = build_in_process_target(args)
            gateway = None if args.no_judge else target.service.gateway
            pace = args.pace or 0.0

        meta = target.describe()
        print(f"Target: {meta}")
        print(f"Asking {len(items)} questions ...\n")
        results = runner.ask_all(items, target, pace_s=pace)

        prompt_version = next(
            (
                r["observation"]["prompt_version"]
                for r in results
                if r["observation"].get("prompt_version")
            ),
            None,
        )
        where = "http" if args.base_url else "local"
        label = args.label or f"prompt-{prompt_version or 'unknown'}-{where}"
        meta.update(
            label=label,
            notes=args.notes,
            git_sha=runner.git_sha(),
            prompt_version=prompt_version,
            started_at=started.isoformat(timespec="seconds"),
            categories=args.category,
            questions=len(items),
            use_cache=args.use_cache if not args.base_url else "server default",
        )
        out_dir = args.out or RESULTS_DIR / f"{started.astimezone():%Y%m%d-%H%M}-{label}"

    if args.no_judge:
        meta.setdefault("judge", None)
    elif gateway is None:
        print(
            "\nNo LLM key configured on this PC, so the judge was skipped. Re-run later on a PC"
            " with GEMINI_API_KEY in .env:\n"
            f"    python scripts/eval_rag.py --judge --from {out_dir / 'run.json'}"
        )
    else:
        judge = make_gateway_judge(gateway, args.max_judge_calls)
        texts = chunk_texts(settings.kb_dir)
        runner.judge_all(results, {i["id"]: i for i in items}, judge, texts)
        meta["judge"] = f"{judge.model} (LLM-as-judge, {judge.calls} calls)"
        if judge.stopped:
            meta["judge"] += f"; stopped early: {judge.stopped}"

    run = runner.build_run(meta, results)
    paths = runner.write_outputs(run, out_dir)
    m = run["metrics"]
    print("\nSummary")
    for key in (
        "behavior_accuracy", "refusal_accuracy", "retrieval_hit_rate", "context_precision",
        "faithfulness", "answer_relevance", "answer_correctness", "deflection_rate",
        "p50_ms", "p95_ms", "pass_rate",
    ):  # fmt: skip
        print(f"  {key:<20}{m[key]}")
    print(f"\nWrote {paths['report']}\n      {paths['metrics']}\n      {paths['run']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
