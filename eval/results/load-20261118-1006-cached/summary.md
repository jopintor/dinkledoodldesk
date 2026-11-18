# DinkDesk load test — 2026-11-18 10:09

- **Target:** https://phentermine-icq-profits-apparently.trycloudflare.com
- **Profile:** cached · **users:** 20 · **spawn rate:** 2/s · **duration:** 3m · think time 2–5 s
- **Answer modes:** cached 11, template 5

| Endpoint | Requests | Failures | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) |
|---|---|---|---|---|---|---|---|
| POST /api/v1/auth/login | 14 | 0 | 2.09 | 470 | 2400 | 2400 | 2353 |
| POST /api/v1/rag/ask [cached] | 16 | 5 | 2.39 | 140 | 490 | 490 | 488 |
| GET /health | 2 | 0 | 0.30 | 130 | 130 | 130 | 130 |
| **All requests** | 32 | 5 | 4.77 | 270 | 1900 | 2400 | 2353 |

Failures:

- /api/v1/rag/ask [cached]: CatchResponseError('not cached (template): this request spent LLM quota') ×5

Times are measured on the PC running Locust, so over a Cloudflare tunnel they include the internet round trip.
