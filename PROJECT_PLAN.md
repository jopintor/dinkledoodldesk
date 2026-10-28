# DinkDesk — AI-HAS Capstone Master Plan

> Single source of truth for the team and for every Claude session working on this project.
> Read this file first. Update it when a decision changes. Last updated: 2026-10-28.

## 1. Course & team

| Item | Value |
|---|---|
| School | De La Salle University–Dasmariñas, CICS, IT Department |
| Course | S-ITPE006 — IT Professional Elective 6 (Integrative Programming Technologies 2) / "Applied Generative AI for IT Solution Development" (WPH Academy materials) |
| Instructor | Mr. Ansbert F. Gregana |
| Project | AI-Powered Enterprise Helpdesk & Workflow Automation System (AI-HAS) |
| Team chat | Facebook Messenger |

| Member | Role | Also owns |
|---|---|---|
| **Jose Pintor** (Project Lead) | Project Manager + AI/RAG Engineer | DevOps (Docker, demo host machine — 32 GB PC), documentation lead, defense lead |
| **Andre Montoya** | Backend & Automation (FastAPI, Postgres, function calling, n8n, Jira) | QA / testing (test suite, load testing, QA report) |
| **Arjan Sarinas** | Frontend & UI/UX (Figma → Next.js: chat widget, agent dashboard, admin KPI dashboard) | UI copy, user manual screenshots |

Hardware note: Jose and Andre can run the full Docker stack. Arjan's laptop is weaker, so the frontend must run on its own (`npm run dev`) against either a mock API or the backend running on Jose's PC (via a tunnel such as Cloudflare Tunnel/ngrok). Arjan never needs Docker.

## 2. Scenario (personalised, still spec-compliant)

**DinkDesk** — the AI IT helpdesk for **PickleHub Clubs** (fictional chain of pickleball clubs in Cavite; names are placeholders the team may rename).

The spec requires an *enterprise IT* helpdesk, so DinkDesk supports the **IT needs of a pickleball business**, not pickleball rules/coaching:

- Staff/coach account password resets (court-booking admin portal, email)
- Software & system access requests (booking system, POS, tournament-bracket software, CCTV viewer)
- Club Wi-Fi / manager VPN troubleshooting
- POS & card-terminal issues at the front desk
- Member app account problems (login, locked account, double-booked court bug reports)
- Automated ticket creation & escalation to the IT team; KPI dashboard for the IT lead

Users/roles (RBAC): `member`, `staff`, `agent` (IT support), `admin`.

## 3. Platforms & stack (decided)

| Area | Choice |
|---|---|
| Design | Figma (Jose will send templates) |
| Task board | GitHub Projects (private repo created by Jose) |
| Documentation | Google Docs/Drive |
| Frontend | Next.js (React, TypeScript) |
| Backend | Python FastAPI |
| App database | PostgreSQL |
| Vector DB | ChromaDB |
| LLM | Google Gemini **free tier** (chat + embeddings + function calling), behind a single swappable provider module |
| Orchestration | LangChain (Python) |
| Automation | n8n (self-hosted in Docker) + webhooks; Jira Cloud free tier as ticket system; password reset is a **mocked** directory service |
| DevOps | Docker Compose, GitHub Actions (lint/test) |
| Eval/QA | pytest, RAGAS-style metrics (faithfulness, answer relevance, context precision), Locust or k6 load tests, Playwright E2E |

Rules:
- The three course PDFs are marked **Restricted** — never commit or upload them. `.gitignore` must exclude `*.pdf` at repo root.
- Secrets live in `.env` (gitignored); commit `.env.example` only.
- Use feature branches + PRs; the Week 15 QA report must show git history of fixes, so commit meaningfully from day one.

## 4. Timeline (real dates — the spec's "8 weeks" is compressed into what's left of the semester)

Today is Week 13 of the syllabus. Presentation/demo is **Week 16 (Nov 16–20) or Week 17 (Nov 23–27)**; Final Product is **Week 18–19 (Nov 30 – Dec 7)**. Target: **demo-ready by Nov 16**.

| Sprint | Dates | Goal | Syllabus tie-in |
|---|---|---|---|
| 0 | Oct 28 – Nov 1 | Repo + Docker skeleton, knowledge-base content, architecture/ERD/prompt design, Figma wireframes, Google Doc started | Wk 13: risk-mitigation framework (privacy/data governance) — can reuse DinkDesk |
| 1 | Nov 2 – Nov 8 | RAG pipeline (ingest KB → Chroma → cited answers), core API, chat UI, auth/RBAC, basic PII redaction | Wk 14: architecture diagram + component spec — reuse Sprint 0 design work |
| 2 | Nov 9 – Nov 15 | Function calling (password reset, Jira ticket, service status), n8n webhooks, human escalation, agent + admin dashboards, prompt-injection guardrails, load test + vuln scan | Wk 15: QA report + git history — produced by Andre from this sprint |
| 3 | Nov 16 – Nov 22 | Evaluation run & metrics, bug fixes, slides, demo script, backup demo video | Wk 16: presentation slot (possible) |
| 4 | Nov 23 – Dec 7 | Defense, final documentation (template's 14 sections), final product submission | Wk 17 presentation (possible), Wk 18–19 final |

## 5. Feature checklist (from syllabus "Project Requirements")

- [ ] Conversational AI chat for IT requests
- [ ] RAG over SOPs/FAQs/policies with citations
- [ ] ≥1 function-calling action (we plan 3: password reset, create Jira ticket, check service status)
- [ ] FastAPI backend
- [ ] ChromaDB vector store
- [ ] Frontend: user chat + agent/admin dashboard with analytics
- [ ] n8n / webhook event-driven automation
- [ ] Human escalation on low confidence / sensitive requests; prompt-injection guardrails
- [ ] RBAC, PII redaction, input validation, secret handling
- [ ] Tests: normal, ambiguous, unsupported, malicious, low-confidence; metrics: accuracy, retrieval relevance, latency, automation success, ticket deflection
- [ ] Docs: architecture, ERD/data-flow, API docs, AI/RAG workflow, setup, user manual, code comments
- [ ] Git repo with branching, env config, Docker
- [ ] Live demo + defense

## 6. Going beyond the instructions (showcase ideas)

1. **"Try to break DinkDesk" live segment** — panel types prompt-injection/PII attempts; a Guardrail Log panel shows each block in real time.
2. **Evaluation scorecard** in the admin dashboard (faithfulness, relevance, deflection rate, p95 latency) from a 50-question golden test set.
3. **Before/after prompt iterations** — show how prompt changes moved the metrics (also feeds the Week 15 report).
4. **Backup demo video** in case the Gemini free tier rate-limits during the live defense; plus response caching for demo questions.
5. **Reuse every enabling assessment** (Wk 13, 14, 15) as project deliverables so no work is wasted.

## 7. Repo layout (planned)

```
/frontend          Next.js app (Arjan)
/backend           FastAPI app, RAG, tools, guardrails (Jose + Andre)
/knowledge-base    Markdown SOPs/FAQs/policies for PickleHub Clubs
/eval              Golden Q&A set, eval scripts, load tests
/automation        n8n workflow exports
/docs              Architecture, ERD, API spec, prompt design, diagrams
/infra             docker-compose, Dockerfiles
```

## 8. Workstreams (one Claude session each)

| # | Workstream | Owner | Writes to |
|---|---|---|---|
| A | Repo, Docker skeleton & GitHub Projects board | Jose | repo root config, `/frontend` + `/backend` + `/infra` skeletons, `.github/` |
| B | Knowledge base content + golden test set | Jose | `/knowledge-base`, `/eval/golden-set` |
| C | Architecture, ERD, API & prompt/guardrail design | Jose + Andre | `/docs` |
| D | Project documentation Google Doc (template sections) | Jose | Google Drive only |
| E | Figma UI/UX (after Jose sends templates) | Arjan | Figma only |

## 9. Open items

- Exact presentation slot (Week 16 or 17) — ask Mr. Gregana.
- Teammates' emails/GitHub usernames for sharing the Google Doc and repo.
- Project documentation Google Doc (workstream D, created 2026-10-28, not shared yet): [DinkDesk – AI-HAS Project Documentation](https://docs.google.com/document/d/1-9LpgU4tLxokY8w43LFUwOjdnqSnSjiqdxhE_A7BA54/edit). Sections 1–5, 11, 12, 14 drafted; 6–10 and 13 have highlighted placeholders waiting on `/docs` and the QA report.
- Figma templates/file link (Jose to send).
- Jira Cloud free site — Jose creates the account.
