# DinkDesk load test — 2026-11-18 10:05

- **Target:** https://phentermine-icq-profits-apparently.trycloudflare.com
- **Profile:** cached · **users:** 10 · **spawn rate:** 2/s · **duration:** 2m · think time 2–5 s
- **Answer modes:** cached 3, template 5

| Endpoint | Requests | Failures | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) |
|---|---|---|---|---|---|---|---|
| POST /api/v1/auth/login | 9 | 0 | 1.46 | 430 | 1200 | 1200 | 1237 |
| GET /api/v1/auth/me | 3 | 0 | 0.49 | 440 | 590 | 590 | 595 |
| POST /api/v1/rag/ask [cached] | 8 | 5 | 1.30 | 150 | 900 | 900 | 895 |
| GET /health | 1 | 0 | 0.16 | 120 | 120 | 120 | 122 |
| **All requests** | 21 | 5 | 3.40 | 400 | 940 | 1200 | 1237 |

Failures:

- /api/v1/rag/ask [cached]: CatchResponseError('not cached (template): this request spent LLM quota') ×5

Times are measured on the PC running Locust, so over a Cloudflare tunnel they include the internet round trip.
