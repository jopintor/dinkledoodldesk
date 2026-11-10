"""Pre-answer demo questions so they are served from the response cache on demo day.

Each question costs at most one generation call (none if it is already cached), paced by
the gateway's rate limiter. Answers are only cached while the KB and prompt version stay
the same, so run this after the final `python -m app.rag.ingest`.

    python scripts/warm_cache.py                                 # golden-set "normal" questions
    python scripts/warm_cache.py --questions demo.txt --role staff   # one question per line
"""

import argparse
import json
import sys
from pathlib import Path

from app.rag.service import Caller, get_rag_service

GOLDEN = Path(__file__).resolve().parents[2] / "eval" / "golden-set" / "golden_set.jsonl"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--questions", type=Path, help="text file, one question per line")
    parser.add_argument("--role", default="staff", help="role for --questions")
    parser.add_argument("--category", default="normal", help="golden-set category")
    args = parser.parse_args(argv)

    if args.questions:
        lines = args.questions.read_text(encoding="utf-8").splitlines()
        pairs = [(q.strip(), args.role) for q in lines if q.strip()]
    else:
        items = [json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines()]
        pairs = [(i["question"], i["user_role"]) for i in items if i["category"] == args.category]

    service = get_rag_service()
    if not service.settings.response_cache_path:
        print("RESPONSE_CACHE_PATH is empty, so nothing would be kept.")
        return 1
    for question, role in pairs:
        answer = service.answer(question, Caller(role=role))
        print(f"{answer.answer_mode:<9} {answer.confidence:.2f} {role:<6} {question[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
