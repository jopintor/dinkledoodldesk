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
infra/           docker-compose.yml for the full stack
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

Needs Docker Desktop. From the repo root:

```bash
docker compose -f infra/docker-compose.yml --env-file .env up -d --build
```

| Service | URL |
|---|---|
| Backend API (Swagger at `/docs`) | http://localhost:8000 |
| ChromaDB | http://localhost:8001 |
| n8n | http://localhost:5678 |
| PostgreSQL | localhost:5432 |

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

### Sharing the backend from Jose's PC

```bash
cloudflared tunnel --url http://localhost:8000
```

Send the printed `https://….trycloudflare.com` URL to Arjan. The frontend calls the API from the browser, so the
backend's `CORS_ORIGINS` must include `http://localhost:3000` (the default).

## LLM provider

All LLM calls go through `backend/app/llm/` (`get_llm_provider()`), which returns LangChain chat and embedding
models. Gemini is the default; set `LLM_PROVIDER=openai` and `OPENAI_API_KEY` (plus `pip install -e ".[openai]"`)
to switch. Do not import a vendor SDK anywhere else.

## Rules

- The course PDFs are **Restricted**: never commit or upload them. `.gitignore` excludes `*.pdf`.
- Secrets live only in `.env` / `frontend/.env.local`.
- Work on a branch and open a pull request; see [`CONTRIBUTING.md`](CONTRIBUTING.md).
