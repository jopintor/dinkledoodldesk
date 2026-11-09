"""Golden set loading (`/eval/golden-set/README.md` describes the fields)."""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN = REPO_ROOT / "eval" / "golden-set" / "golden_set.jsonl"
RESULTS_DIR = REPO_ROOT / "eval" / "results"
DATASET_VERSION = "golden-v1"

CATEGORIES = (
    "normal",
    "ambiguous",
    "unsupported",
    "malicious_prompt_injection",
    "pii",
    "low_confidence",
    "action_request",
)


def load_items(
    path: Path = GOLDEN,
    *,
    categories: list[str] | None = None,
    ids: list[str] | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Golden items in file order, filtered by category and/or id."""
    items = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if categories and "all" not in categories:
        unknown = set(categories) - set(CATEGORIES)
        if unknown:
            raise ValueError(f"unknown category: {', '.join(sorted(unknown))}")
        items = [i for i in items if i["category"] in categories]
    if ids:
        wanted = {i.upper() for i in ids}
        items = [i for i in items if i["id"] in wanted]
    return items[:limit] if limit else items
