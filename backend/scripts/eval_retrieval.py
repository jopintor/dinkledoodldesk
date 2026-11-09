"""Retrieval hit rate on the golden set (no LLM generation calls).

For each question it runs retrieval as the question's `user_role` and checks the retrieved
document ids against `expected_source_ids`:

- Hit@k: at least one expected document among the top k retrieved documents
- Recall@5: share of the expected documents retrieved
- MRR: 1 / rank of the first expected document

Run from `backend/` after ingesting (or pass --ingest):

    python scripts/eval_retrieval.py                     # 20 "normal" questions, hybrid
    python scripts/eval_retrieval.py --mode bm25         # ablation: keyword only
    python scripts/eval_retrieval.py --json out.json     # save per-question results

Uses one query-embedding call per question with LLM_PROVIDER=gemini. With
LLM_PROVIDER=fake the "vector" side is a hashed bag of words, not a semantic model.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from app.config import get_settings
from app.llm import LLMGateway, get_llm_provider
from app.rag.ingest import ingest_knowledge_base
from app.rag.retriever import Retriever
from app.rag.store import KBStore, collection_name, make_client

GOLDEN = get_settings().kb_dir.parent / "eval" / "golden-set" / "golden_set.jsonl"


def load_items(path: Path, category: str) -> list[dict]:
    items = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return [i for i in items if category == "all" or i["category"] == category]


def score(expected: list[str], retrieved: list[str]) -> dict:
    ranks = [retrieved.index(d) + 1 for d in expected if d in retrieved]
    first = min(ranks) if ranks else None
    return {
        "hit@1": bool(first and first <= 1),
        "hit@3": bool(first and first <= 3),
        "hit@5": bool(first and first <= 5),
        "recall@5": len([r for r in ranks if r <= 5]) / len(expected),
        "rr": 1 / first if first else 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--golden", type=Path, default=GOLDEN)
    parser.add_argument("--category", default="normal", help='golden-set category or "all"')
    parser.add_argument("--mode", choices=["hybrid", "vector", "bm25"], default="hybrid")
    parser.add_argument("--ingest", action="store_true", help="ingest the KB first")
    parser.add_argument("--json", type=Path, help="write per-question results here")
    args = parser.parse_args(argv)

    settings = get_settings()
    provider = get_llm_provider(settings)
    gateway = LLMGateway(provider, settings)
    store = KBStore(
        make_client(settings), collection_name(settings, provider.embedding_model_name())
    )
    if args.ingest:
        report = ingest_knowledge_base(settings.kb_dir, store, gateway.embed_documents)
        print(report.summary(), end="\n\n")
        if not report.ok:
            return 1
    retriever = Retriever(store, gateway.embed_query, settings)
    if retriever.chunk_count == 0:
        print(f"Collection {store.name} is empty: run `python -m app.rag.ingest` first.")
        return 1

    items = [i for i in load_items(args.golden, args.category) if i["expected_source_ids"]]
    rows = []
    for item in items:
        result = retriever.search(item["question"], item["user_role"], mode=args.mode)
        row = {
            "id": item["id"],
            "role": item["user_role"],
            "expected": item["expected_source_ids"],
            "retrieved": result.doc_ids,
            "chunks": [c.chunk.chunk_id for c in result.chunks],
            "confidence": result.retrieval_confidence,
            "band": result.band,
            **score(item["expected_source_ids"], result.doc_ids),
        }
        rows.append(row)
        mark = "ok  " if row["hit@5"] else "MISS"
        print(
            f"{mark} {row['id']} {row['role']:<6} conf={row['confidence']:.2f} {row['band']:<6} "
            f"expected={','.join(row['expected'])} got={','.join(row['retrieved'])}"
        )

    n = len(rows)
    summary = {
        "provider": provider.name,
        "embedding_model": provider.embedding_model_name(),
        "collection": store.name,
        "kb_version": retriever.kb_version,
        "mode": args.mode,
        "category": args.category,
        "questions": n,
        "hit@1": sum(r["hit@1"] for r in rows) / n,
        "hit@3": sum(r["hit@3"] for r in rows) / n,
        "hit@5": sum(r["hit@5"] for r in rows) / n,
        "recall@5": sum(r["recall@5"] for r in rows) / n,
        "mrr": sum(r["rr"] for r in rows) / n,
        "bands": dict(Counter(r["band"] for r in rows)),
    }
    print()
    for key in ("provider", "embedding_model", "mode", "questions"):
        print(f"{key:<16}{summary[key]}")
    for key in ("hit@1", "hit@3", "hit@5", "recall@5", "mrr"):
        print(f"{key:<16}{summary[key]:.3f}")
    print(f"{'bands':<16}{summary['bands']}")
    if args.json:
        args.json.write_text(json.dumps({"summary": summary, "items": rows}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
