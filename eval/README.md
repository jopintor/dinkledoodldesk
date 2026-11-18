# DinkDesk evaluation and load testing

Two tools, both run from `backend/`:

| Tool | What it measures | LLM cost |
|---|---|---|
| `scripts/eval_rag.py` | Golden set (50 questions) → **retrieval hit rate, behaviour accuracy, latency p50/p95, deflection rate** (plus context precision, refusal accuracy) | ~35 generation calls for all 50 |
| `scripts/load_test.py` | Locust load test → requests/s, p50/p95/p99, failures, at 10–30 users | **0** with the default `cached` profile |

These four metrics plus a small load test are what the prototype needs (PROJECT_PLAN.md §5). The LLM-as-judge scores (faithfulness, answer relevance, correctness) are **optional**: off by default, only with `--judge`, and not needed for Sprint 2 — skip them to save Gemini quota.

Results go to `eval/results/<date>-<label>/`:

- `report.md` — paste this into the QA report and the Google Doc (tables are ready)
- `metrics.json` — the numbers only
- `run.json` — everything, per question (expected vs actual behaviour, retrieved docs, judge verdicts)
- `eval_run_payload.json` — the body for `POST /api/v1/eval/runs` once that endpoint exists

Load tests go to `eval/results/load-<date>-<profile>/summary.md` (plus `locust.html`, not committed).

The first real run is in [`results/20261109-1610-prompt-v1-baseline/report.md`](results/20261109-1610-prompt-v1-baseline/report.md).

---

## Andre: Sprint 2 checklist

Your laptop only sends requests; DinkDesk runs on Jose's PC and you reach it through a Cloudflare tunnel. Do the steps in order.

### 1. One-time setup on your laptop

```bash
git fetch
git checkout <this branch or main after merge>
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev,load]"
```

(macOS/Linux: `source .venv/bin/activate`.)

**Done when** `python scripts/eval_rag.py --help` and `python -m locust --version` both print without errors.

### 2. Ask Jose to start the server (he does this on his PC)

Jose runs, from `backend/`, with the real Gemini key in `.env`:

```bash
python -m app.seed
python -m app.rag.ingest
uvicorn app.main:app --port 8000
cloudflared tunnel --url http://localhost:8000
```

He sends you the `https://<random>.trycloudflare.com` URL. It changes every time the tunnel restarts.

**Done when** `https://<url>/health` opens in your browser and shows `"status": "ok"`.

### 3. Run the evaluation over the tunnel

```bash
python scripts/eval_rag.py --base-url https://<url> --label sprint2-tunnel
```

It signs in as the seeded demo users (member, staff, agent, admin1), asks all 50 questions one by one (3 s apart, about 5 minutes) and prints one line per question:

```
[ 1/50] ok   GS-001 normal  expected=answer  got=answer  generated  2310 ms hit@5
```

No judge runs (it is optional and off by default), so this needs no Gemini key on your laptop. The report shows "—" for faithfulness and relevance; that is expected.

**Done when** `eval/results/<folder>/report.md` exists and the "Errors" line in it says `0`.

### 4. Warm the demo cache (Jose, on his PC)

The load test should not spend Gemini quota, so it only asks questions whose answers are already cached. Jose runs this **before** starting `uvicorn` (or restarts `uvicorn` after it — the server reads the cache file at startup):

```bash
python scripts/warm_cache.py
```

Step 3 already cached most of these answers, so this costs only a few calls.

### 5. Run the load test

Start small, then go up:

```bash
python scripts/load_test.py --base-url https://<url> --users 10 --duration 2m
```

```bash
python scripts/load_test.py --base-url https://<url> --users 20 --duration 3m
```

```bash
python scripts/load_test.py --base-url https://<url> --users 30 --duration 3m
```

Each simulated user signs in, then asks a demo question every 2–5 s, sometimes checking `/health` and `/api/v1/auth/me`. Before it starts, a preflight checks that the server is up, the demo login works and the answers really come from the cache; if not, it stops and tells you what to do. If more than 5 answers during the run called Gemini (`generated` or `degraded`), it stops itself so it can't burn the quota. Fixed `template` replies (a clarifying question, the "no guide" hand-off) never call Gemini and don't count.

**Done when** each run prints a table like this and saves it as `summary.md`:

| Endpoint | Requests | Failures | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) |
|---|---|---|---|---|---|---|---|
| POST /api/v1/rag/ask [cached] | 312 | 0 | 2.6 | 180 | 420 | 610 | 900 |

### 6. Put the numbers in the QA report

- Copy the tables from the eval `report.md` (headline metrics, behaviour by category, failed items).
- Copy each load test's `summary.md` table, and write one sentence on where p95 started to climb or failures appeared.
- Commit the eval result folder and the `summary.md` files you used (raw Locust CSV/HTML files are ignored by git).

---

## Options

`eval_rag.py`:

| Option | Meaning |
|---|---|
| *(no `--base-url`)* | In-process: calls the RAG service directly. Needs the KB index on this PC (`python -m app.rag.ingest`). Jose's default. |
| `--base-url URL` | Over HTTP (tunnel or `http://localhost:8000`). |
| `--category normal,pii` · `--ids GS-001,GS-019` · `--limit 5` | Run part of the set (cheap re-checks). |
| `--judge` · `--max-judge-calls 60` | Optional: also run the LLM judge (faithfulness, relevance, correctness), capped at N calls. Needs a Gemini key on this PC and spends quota; not needed for the prototype. |
| `--from run.json` | Load an earlier run and rewrite the report (add `--judge` to judge it). Makes no DinkDesk calls. |
| `--label prompt-v2` · `--notes "..."` | Name the run (use the prompt version, so before/after runs compare). |
| `--use-cache` | In-process only: allow cached answers (default: always a fresh answer). |
| `--pace 5` | Seconds between questions (default 0 in-process, 3 over HTTP). |
| `--credentials users.json` | Other accounts: `{"member": ["email", "password"], "staff": [...], "agent": [...], "admin": [...]}`. |

`load_test.py`:

| Option | Meaning |
|---|---|
| `--users 10` · `--spawn-rate 2` · `--duration 2m` | Load shape. |
| `--profile live --allow-llm` | Real generation on every request (capped at 3 users). Spends quota; shows how the rate limiter, model fallback and degraded mode behave under load. Use once, at most. |
| `--max-cache-misses 5` | Cached profile: stop after N uncached answers. |
| `--skip-preflight` | Don't check the server first. |

## What the numbers mean

| Metric | How it is computed | Target (ai-design.md §9) |
|---|---|---|
| Behaviour accuracy | DinkDesk did what `expected_behavior` says: `answer`, `clarify`, `refuse`, `escalate` or `call_tool:<name>` | ≥ 85 % |
| Refusal accuracy | Injection + unsupported items that were refused **or** escalated | 100 % |
| Guardrail block rate | Injection items that were refused (stricter) | — |
| Retrieval hit rate | An expected KB document in the top 5 retrieved | — |
| Context precision | RAGAS formula on document ids: are the expected docs ranked high? | ≥ 0.75 |
| Faithfulness (optional, `--judge`) | Judge splits the answer into claims; supported ÷ total, against the retrieved chunks | ≥ 0.85 |
| Answer relevance (optional) | Judge's 0–1 score: does the answer address the question? | ≥ 0.80 |
| Correctness (optional) | Judge's 0–1 score against `reference_answer` | — |
| Deflection rate | `answer` / `call_tool:*` items DinkDesk resolved itself (answered or ran a tool), without escalating, refusing or asking back | — |
| Latency p50 / p95 | The service's own `latency_ms` (network excluded); also shown for generated answers only | p95 ≤ 6 s |

How behaviour is read from a response: a guardrail block (`answer_mode: "refusal"`) → `refuse`; a tool call → `call_tool:<name>`; `escalation_required` or the "I don't have a guide… I can create a ticket or connect you" template → `escalate`; a clarifying question → `clarify`; anything else → `answer`.

Limits worth stating in the QA report: the judge is the same model family as the generator (scores are indicative; spot-check failed items by hand), 50 questions is a small set, and Gemini answers vary a little between runs.

## Troubleshooting

| Problem | Fix |
|---|---|
| `Collection ... is empty` (in-process) | `python -m app.rag.ingest`, or add `--ingest`. |
| `401` / login failed | Jose runs `python -m app.seed` (creates the demo users). |
| Many `degraded` answers or `LLM unavailable` | Gemini per-minute or daily quota. Wait a minute (the daily quota resets at midnight US Pacific, 3–4 PM Philippine time) and rerun the failed items with `--ids`. |
| Load-test preflight says "not cached" | Step 4: `warm_cache.py`, then restart `uvicorn`. |
| `502` / `530` from the tunnel | The tunnel or Jose's server stopped; ask for a new URL. |
| `--judge` was skipped | No key on this PC; the judge is optional, so ignore it or run `--judge --from run.json` on Jose's PC. |

## Tests

The metric maths, judge parsing, HTTP client and an in-process end-to-end run are tested offline (fake LLM, hashed embeddings, no network) in CI:

```bash
pytest tests/test_eval_harness.py
```
