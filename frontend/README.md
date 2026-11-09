# DinkDesk frontend

Next.js (App Router, TypeScript, Tailwind v4). Runs on its own — no Docker needed.

Built by Jose with Claude Code from Arjan's final Figma design
([DinkDesk – UI Design (Copy)](https://www.figma.com/design/1gFwqS3GDyX581iJMlsX0R)).

```bash
npm install
cp .env.example .env.local   # optional: the default is the built-in mock API
npm run dev                  # http://localhost:3000
```

## Which API it talks to

`NEXT_PUBLIC_API_BASE_URL` in `.env.local`:

| Value | When |
|---|---|
| `/mock-api` (default) | No backend. Serves the mock API in `src/app/mock-api/` (logic in `src/lib/mock/`) |
| `http://localhost:8000` | Backend running on your machine |
| `https://….trycloudflare.com` | Backend on Jose's PC through a tunnel |

With a real backend, endpoints the backend doesn't have yet (it answers FastAPI's
`404 {"detail":"Not Found"}`) fall back to the mock API automatically, so every screen keeps working
while backend endpoints land. Login (`/api/v1/auth/*`) and chat answers (`/api/v1/rag/ask`) always use
the real backend in that mode.

## Demo accounts (mock API)

Password `dinkdesk` for all of these (the login page has buttons that fill them in):

| Login | Role | Lands on |
|---|---|---|
| `lea.bautista` (Staff & IT tab) | staff | Chat |
| `carla.reyes@picklehub.example` (Member tab) | member | Chat |
| `kat.mendoza` | agent | Escalation list |
| `ramon.villareal` | admin | IT dashboard |

The seed users from `backend/app/seed.py` (`staff@picklehub.example` / `staff123!` etc.) also work
in both modes. In the mock chat, try: "I forgot my StaffID password", "Please reset it for me",
code `000000` (wrong code) or any other 6 digits, "Staff Wi-Fi keeps dropping", or
"Ignore your previous instructions…" (shows up in the admin guardrail log).

## Layout

| Path | What |
|---|---|
| `src/app/login` | Login (Staff & IT / Member) |
| `src/app/chat` + `src/components/chat` | Chat: cited answers, typing, tool confirmation, escalation notice, quick questions, new chat |
| `src/app/agent` | Escalation list for agents/admins |
| `src/app/admin` | IT dashboard: KPIs, eval scorecard, guardrail log |
| `src/app/admin/knowledge-base` | Knowledge-base list (built before the prototype scope cut; not extended) |
| `src/lib/api.ts` | The only place that calls the API (typed, follows `docs/api.md`) |
| `src/app/globals.css` | Design tokens from the Figma style guide |

Before every PR run `npm run lint` and `npm run build`.
