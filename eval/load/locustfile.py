"""Locust load test for the DinkDesk API. Start it with `backend/scripts/load_test.py`.

Each simulated user signs in as a seeded demo account, then loops: ask a question
(`POST /api/v1/rag/ask`), sometimes check `GET /health` and `GET /api/v1/auth/me`, and
waits 2-5 s between actions like a person reading the reply.

Profiles (env `DINKDESK_LOAD_PROFILE`):
- `cached` (default, safe): only the golden-set "normal" questions, asked with the same role
  that `scripts/warm_cache.py` warmed them with, so every answer should come from the
  response cache and cost no Gemini call. A generated or degraded answer (one that called
  Gemini) is reported as a failure ("not cached"); fixed template replies (clarify, hand-off)
  never call Gemini and count as fine. The test stops itself after `DINKDESK_MAX_CACHE_MISSES`
  (default 5) so a cold cache can't burn the free-tier quota.
- `live`: the same questions with a unique suffix, so each one is a real retrieval +
  generation. Spends Gemini quota; the server's rate limiter will queue, fall back or serve
  degraded answers past ~8 requests per minute, which is what this profile measures.

`DINKDESK_LOAD_SUMMARY` (optional) = path of a JSON file for answer-mode counts.
"""

import json
import os
import random
import threading
from collections import Counter
from pathlib import Path

from locust import HttpUser, between, events, task

GOLDEN = Path(__file__).resolve().parents[1] / "golden-set" / "golden_set.jsonl"
PROFILE = os.environ.get("DINKDESK_LOAD_PROFILE", "cached")
MAX_CACHE_MISSES = int(os.environ.get("DINKDESK_MAX_CACHE_MISSES", "5"))
SUMMARY_PATH = os.environ.get("DINKDESK_LOAD_SUMMARY")

# Seeded demo accounts (backend/app/seed.py).
DEMO_USERS = {
    "member": ("member@picklehub.example", "member123!"),
    "staff": ("staff@picklehub.example", "staff123!"),
    "agent": ("agent@picklehub.example", "agent123!"),
    "admin": ("admin1@picklehub.example", "admin123!"),
}


def _questions_by_role() -> dict[str, list[str]]:
    by_role: dict[str, list[str]] = {}
    for line in GOLDEN.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        item = json.loads(line)
        if item["category"] == "normal":
            by_role.setdefault(item["user_role"], []).append(item["question"])
    return by_role


QUESTIONS = _questions_by_role()
# Answer modes that called (or tried to call) the LLM. "cached" and "template" did not.
LLM_MODES = {"generated", "degraded"}
modes: Counter = Counter()
_lock = threading.Lock()
_counter = 0


def _next_id() -> int:
    global _counter
    with _lock:
        _counter += 1
        return _counter


class HelpdeskUser(HttpUser):
    wait_time = between(2, 5)

    def on_start(self) -> None:
        self.role = random.choice(sorted(QUESTIONS))  # noqa: S311 - not security related
        email, password = DEMO_USERS[self.role]
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
            name="/api/v1/auth/login",
        )
        resp.raise_for_status()
        self.headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    @task(8)
    def ask(self) -> None:
        question = random.choice(QUESTIONS[self.role])  # noqa: S311
        if PROFILE == "live":
            question = f"{question} (load test {_next_id()})"
        with self.client.post(
            "/api/v1/rag/ask",
            json={"content": question},
            headers=self.headers,
            name=f"/api/v1/rag/ask [{PROFILE}]",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"HTTP {resp.status_code}")
                return
            mode = resp.json()["assistant_message"]["answer_mode"]
            with _lock:
                modes[mode] += 1
                misses = sum(n for m, n in modes.items() if m in LLM_MODES)
            # Fixed (template) replies never call Gemini, so only a generated or degraded
            # answer means the cache missed and quota was spent.
            if PROFILE == "cached" and mode in LLM_MODES:
                resp.failure(f"not cached ({mode}): this request spent LLM quota")
                if misses >= MAX_CACHE_MISSES:
                    print(
                        f"\nSTOPPING: {misses} answers were not cached. Run "
                        "`python scripts/warm_cache.py` on the server PC, then try again."
                    )
                    self.environment.runner.quit()
            else:
                resp.success()

    @task(1)
    def health(self) -> None:
        self.client.get("/health", name="/health")

    @task(1)
    def me(self) -> None:
        self.client.get("/api/v1/auth/me", headers=self.headers, name="/api/v1/auth/me")


@events.quitting.add_listener
def _write_summary(environment, **_kwargs) -> None:
    print(f"\nAnswer modes: {dict(modes)}")
    if SUMMARY_PATH:
        Path(SUMMARY_PATH).write_text(
            json.dumps({"profile": PROFILE, "answer_modes": dict(modes)}, indent=2),
            encoding="utf-8",
        )
