# DinkDesk load test — 2026-11-18 19:53

- **Target:** https://phentermine-icq-profits-apparently.trycloudflare.com
- **Profile:** cached · **users:** 20 · **spawn rate:** 2/s · **duration:** 3m · think time 2–5 s
- **Answer modes:** cached 473, template 312

| Endpoint | Requests | Failures | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) |
|---|---|---|---|---|---|---|---|
| POST /api/v1/auth/login | 20 | 0 | 0.11 | 420 | 710 | 710 | 708 |
| GET /api/v1/auth/me | 83 | 0 | 0.47 | 120 | 140 | 370 | 369 |
| POST /api/v1/rag/ask [cached] | 779 | 0 | 4.37 | 160 | 190 | 220 | 338 |
| GET /health | 98 | 0 | 0.55 | 110 | 150 | 180 | 179 |
| **All requests** | 980 | 0 | 5.50 | 160 | 200 | 420 | 708 |

Times are measured on the PC running Locust, so over a Cloudflare tunnel they include the internet round trip.
