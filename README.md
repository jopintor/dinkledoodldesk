# DinkDesk

**DinkDesk** is the AI IT helpdesk for **PickleHub Clubs**, a fictional chain of pickleball clubs in Cavite.
It is our capstone for S-ITPE006 (*AI-Powered Enterprise Helpdesk & Workflow Automation System*, AI-HAS)
at De La Salle University–Dasmariñas.

Staff, coaches and members chat with DinkDesk about IT problems (password resets, system access, club Wi-Fi/VPN,
POS terminals, member-app accounts). It answers from the club's SOPs and policies with citations (RAG), performs
actions through function calling (password reset, Jira ticket, service status), triggers n8n automations, and hands
off to a human IT agent when it is unsure or the request is sensitive.

See [`PROJECT_PLAN.md`](PROJECT_PLAN.md) for scope, timeline and decisions.

## Team

| Member | Role |
|---|---|
| Jose Pintor | Project lead, AI/RAG engineer, DevOps (Docker, demo host), documentation |
| Andre Montoya | Backend & automation (FastAPI, Postgres, function calling, n8n, Jira), QA/testing |
| Arjan Sarinas | Frontend & UI/UX (Figma → Next.js chat widget, agent and admin dashboards) |

## Stack

Next.js + TypeScript · FastAPI · PostgreSQL · ChromaDB · Google Gemini (free tier) via LangChain, behind a swappable
provider module · n8n · Jira Cloud · Docker Compose · GitHub Actions.

## Repository layout

```
backend/         FastAPI app (app/), tests (tests/), Dockerfile
frontend/        Next.js app; runs with `npm run dev`, no Docker needed
infra/           docker-compose.yml, demo-host scripts, Docker setup guide
mock-directory/  mocked StaffID directory (one-time codes, resets) used in demos
knowledge-base/  Markdown SOPs/FAQs/policies that DinkDesk answers from
eval/            Golden Q&A set, evaluation scripts, load tests
automation/      n8n workflow exports
docs/            Architecture, ERD, API spec, prompt and guardrail design
```

## Getting started

Copy the environment template once, at the repo root, and fill in your own keys (never commit `.env`):

```bash
cp .env.example .env
```

### Full stack in Docker (Jose, Andre)

Needs Docker Desktop (first-time install on Windows: [`infra/docker-desktop-setup.md`](infra/docker-desktop-setup.md)).
From the repo root:

```bash
docker compose -f infra/docker-compose.yml --env-file .env up -d --build
```

| Service | URL |
|---|---|
| Backend API (Swagger at `/docs`) | http://localhost:8000 |
| ChromaDB | http://localhost:8001 |
| n8n | http://localhost:5678 |
| PostgreSQL | localhost:5432 |
| Mock StaffID directory ([`mock-directory/`](mock-directory/README.md)) | http://localhost:8090 |
| Mailpit inbox (all demo emails and "SMS" codes) | http://localhost:8025 (SMTP on 1025) |

Add `--profile frontend` to also run the frontend in Docker at http://localhost:3000.

### Backend without Docker

Use Python 3.12 (3.15 lacks wheels for some dependencies).

```bash
cd backend
py -3.12 -m venv .venv            # macOS/Linux: python3.12 -m venv .venv
.venv/Scripts/activate            # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload     # http://localhost:8000/health
pytest
```

### Frontend only (Arjan)

Needs Node.js 20+ only.

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev                       # http://localhost:3000
```

Set `NEXT_PUBLIC_API_BASE_URL` in `frontend/.env.local` to `/mock-api` (no backend), `http://localhost:8000`, or the
tunnel URL Jose shares when his PC is running the stack. See [`frontend/README.md`](frontend/README.md).

### Demo host: Jose's PC

One script starts everything, ingests the knowledge base and opens Cloudflare quick tunnels for the backend and the
frontend (needs `cloudflared`: `winget install --id Cloudflare.cloudflared`). In PowerShell, from the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File infra\scripts\demo-up.ps1
```

It prints the URLs to send (also saved in `infra/.demo/urls.txt`, which git ignores):

- **Arjan**: the frontend URL, and the backend URL to put in `NEXT_PUBLIC_API_BASE_URL` for his own `npm run dev`.
- **Andre**: the backend URL and its `/docs` Swagger UI.

Tunnel URLs change on every run. The script builds the frontend against the backend's tunnel URL and adds the
frontend's tunnel origin to the backend's `CORS_ORIGINS` (`http://localhost:3000` is always allowed). Only the
backend and frontend are exposed; n8n, Postgres, Chroma, Mailpit and the mock directory stay local.

| Command | Does |
|---|---|
| `infra\scripts\demo-up.ps1 -NoTunnel` | local only, no tunnels |
| `infra\scripts\demo-up.ps1 -NoFrontend` | backend tunnel only (Arjan runs `npm run dev`) |
| `infra\scripts\demo-up.ps1 -SkipIngest` / `-FullIngest` | skip the KB ingestion / re-embed every document |
| `infra\scripts\verify-stack.ps1` | checks every service plus a one-time code landing in Mailpit |
| `infra\scripts\demo-down.ps1` | closes the tunnels (`-Stack` also stops the containers, data kept) |

## LLM provider

All LLM calls go through `backend/app/llm/` (`get_llm_provider()`), which returns LangChain chat and embedding
models. Gemini is the default; set `LLM_PROVIDER=openai` and `OPENAI_API_KEY` (plus `pip install -e ".[openai]"`)
to switch. Do not import a vendor SDK anywhere else.

## Rules

- The course PDFs are **Restricted**: never commit or upload them. `.gitignore` excludes `*.pdf`.
- Secrets live only in `.env` / `frontend/.env.local`.
- Work on a branch and open a pull request; see [`CONTRIBUTING.md`](CONTRIBUTING.md).
