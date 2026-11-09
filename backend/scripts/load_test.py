"""Load-test a running DinkDesk API with Locust, safely, in one command.

Run from `backend/` (see eval/README.md):

    python scripts/load_test.py --base-url https://xyz.trycloudflare.com
    python scripts/load_test.py --base-url http://localhost:8000 --users 20 --duration 3m
    python scripts/load_test.py --base-url ... --profile live --allow-llm --users 3 --duration 1m

Default profile `cached` asks only questions that `scripts/warm_cache.py` pre-answered, so
it costs no Gemini calls. A preflight checks that first and refuses to start on a cold
cache. Results go to eval/results/load-<date>/: summary.md, Locust CSVs and an HTML report.
"""

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCUSTFILE = REPO_ROOT / "eval" / "load" / "locustfile.py"
GOLDEN = REPO_ROOT / "eval" / "golden-set" / "golden_set.jsonl"
RESULTS_DIR = REPO_ROOT / "eval" / "results"
LIVE_MAX_USERS = 3


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--base-url", required=True, help="API root, e.g. https://xyz.trycloudflare.com")
    p.add_argument("--users", type=int, default=10, help="simulated users (default 10)")
    p.add_argument("--spawn-rate", type=float, default=2, help="users started per second")
    p.add_argument("--duration", default="2m", help="e.g. 90s, 2m, 5m (default 2m)")
    p.add_argument("--profile", choices=["cached", "live"], default="cached")
    p.add_argument(
        "--allow-llm", action="store_true", help="required for --profile live (spends quota)"
    )
    p.add_argument(
        "--max-cache-misses", type=int, default=5, help="cached profile: stop after N misses"
    )
    p.add_argument("--skip-preflight", action="store_true")
    p.add_argument("--out", type=Path, help="output folder (default eval/results/load-<date>)")
    return p.parse_args(argv)


def first_warm_question() -> tuple[str, str]:
    for line in GOLDEN.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        if item["category"] == "normal":
            return item["question"], item["user_role"]
    raise SystemExit("no normal questions in the golden set")


def preflight(base_url: str, profile: str) -> None:
    """Server up, demo login works, and (cached profile) the demo answers are cached."""
    sys.path.insert(0, str(Path(__file__).parent))
    from evalkit.targets import DEMO_USERS

    with httpx.Client(base_url=base_url, timeout=60) as client:
        health = client.get("/health")
        health.raise_for_status()
        print(f"Server: {health.json()}")
        question, role = first_warm_question()
        email, password = DEMO_USERS[role]
        login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        if login.status_code != 200:
            raise SystemExit(
                f"Login as the demo {role} failed ({login.status_code}). Run "
                "`python -m app.seed` on the server PC."
            )
        if profile != "cached":
            return
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        ask = client.post("/api/v1/rag/ask", json={"content": question}, headers=headers)
        ask.raise_for_status()
        mode = ask.json()["assistant_message"]["answer_mode"]
        if mode != "cached":
            raise SystemExit(
                f"Preflight answer was '{mode}', not 'cached': the demo questions are not "
                "warmed. On the server PC run `python scripts/warm_cache.py`, then retry."
            )
        print("Preflight OK: demo answers come from the response cache.")


def summarise(out_dir: Path, args: argparse.Namespace) -> str:
    stats_path = out_dir / "locust_stats.csv"
    if not stats_path.exists():
        return "Locust wrote no stats (did it start?)."
    rows = list(csv.DictReader(stats_path.open(encoding="utf-8")))
    modes_path = out_dir / "answer_modes.json"
    modes = json.loads(modes_path.read_text())["answer_modes"] if modes_path.exists() else {}
    lines = [
        f"# DinkDesk load test — {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"- **Target:** {args.base_url}",
        f"- **Profile:** {args.profile} · **users:** {args.users} · **spawn rate:** "
        f"{args.spawn_rate}/s · **duration:** {args.duration} · think time 2–5 s",
        f"- **Answer modes:** {', '.join(f'{k} {v}' for k, v in sorted(modes.items())) or '—'}",
        "",
        "| Endpoint | Requests | Failures | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        name = "**All requests**" if r["Name"] == "Aggregated" else f"{r['Type']} {r['Name']}"
        lines.append(
            f"| {name} | {r['Request Count']} | {r['Failure Count']} | "
            f"{float(r['Requests/s']):.2f} | {r['50%']} | {r['95%']} | {r['99%']} | "
            f"{float(r['Max Response Time']):.0f} |"
        )
    failures_path = out_dir / "locust_failures.csv"
    if failures_path.exists():
        failures = list(csv.DictReader(failures_path.open(encoding="utf-8")))
        if failures:
            lines += ["", "Failures:", ""]
            lines += [f"- {f['Name']}: {f['Error']} ×{f['Occurrences']}" for f in failures]
    lines += [
        "",
        "Times are measured on the PC running Locust, so over a Cloudflare tunnel they "
        "include the internet round trip.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    base_url = args.base_url.rstrip("/")
    if args.profile == "live":
        if not args.allow_llm:
            print("--profile live spends Gemini quota on every request; add --allow-llm.")
            return 2
        if args.users > LIVE_MAX_USERS:
            print(f"--profile live is capped at {LIVE_MAX_USERS} users (free-tier quota).")
            args.users = LIVE_MAX_USERS
    if not args.skip_preflight:
        preflight(base_url, args.profile)

    out_dir = args.out or RESULTS_DIR / f"load-{datetime.now():%Y%m%d-%H%M}-{args.profile}"
    out_dir.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "DINKDESK_LOAD_PROFILE": args.profile,
        "DINKDESK_MAX_CACHE_MISSES": str(args.max_cache_misses),
        "DINKDESK_LOAD_SUMMARY": str(out_dir / "answer_modes.json"),
    }
    cmd = [
        sys.executable, "-m", "locust", "-f", str(LOCUSTFILE), "--headless",
        "--host", base_url, "--users", str(args.users), "--spawn-rate", str(args.spawn_rate),
        "--run-time", args.duration, "--csv", str(out_dir / "locust"),
        "--html", str(out_dir / "locust.html"), "--only-summary",
    ]  # fmt: skip
    print(f"Running Locust: {args.users} users for {args.duration} ({args.profile}) ...")
    code = subprocess.run(cmd, env=env, check=False).returncode  # noqa: S603

    summary = summarise(out_dir, args)
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")
    print("\n" + summary)
    print(f"Wrote {out_dir / 'summary.md'} and {out_dir / 'locust.html'}")
    # Locust exits 1 when any request failed; the summary says which.
    return code


if __name__ == "__main__":
    sys.exit(main())
