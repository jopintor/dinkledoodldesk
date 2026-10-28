# DinkDesk frontend

Next.js (App Router, TypeScript, Tailwind). Runs on its own — no Docker needed.

```bash
npm install
cp .env.example .env.local   # then choose which API to talk to
npm run dev                  # http://localhost:3000
```

`NEXT_PUBLIC_API_BASE_URL` in `.env.local` decides where API calls go:

| Value | When |
|---|---|
| `/mock-api` | No backend available; serves the mock routes in `src/app/mock-api/` |
| `http://localhost:8000` | Backend running on your machine |
| `https://….trycloudflare.com` | Backend on Jose's PC through a tunnel |

All API calls go through `src/lib/api.ts`. Before every PR run `npm run lint` and `npm run build`.
