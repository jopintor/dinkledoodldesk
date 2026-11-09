"""Evaluation helpers for `scripts/eval_rag.py` and `scripts/load_test.py`.

- `golden`  — load the golden set (`/eval/golden-set/golden_set.jsonl`)
- `targets` — ask DinkDesk a question in-process or over HTTP and record what it did
- `metrics` — pure scoring functions (behaviour, retrieval, latency, deflection)
- `judge`   — LLM-as-judge for faithfulness, answer relevance and correctness
- `report`  — Markdown report for the QA report / Google Doc

Everything in `metrics`, `judge` and `report` is pure or takes its LLM call as a function,
so the tests run offline (backend/tests/test_eval_*.py).
"""
