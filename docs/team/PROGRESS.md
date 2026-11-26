# DinkDesk — Progress Tracker

> Where the project stands right now, track by track. [PROJECT_PLAN.md](PROJECT_PLAN.md) says *what* we're building and *when*; this file says *how far along we are*.
> **Last updated: 2026-11-02 (Mon, start of Sprint 1)** · Update the snapshot, the track you touched and the changelog whenever something lands.

> **Scope change 2026-11-09:** the project is now a *prototype* — see [PROJECT_PLAN.md §5](PROJECT_PLAN.md). Items below that mention 4 tools, WF-03…WF-05, outbox/HMAC, agent takeover, KB admin page, mobile layout or Playwright are cut ("future work").

**Legend:** ✅ Done · 🟡 In progress / partly done · ⬜ Not started · 🔴 Blocked · ⚠️ Needs a decision or action

---

## 1. Snapshot

| | |
|---|---|
| Current sprint | **Sprint 1 — Nov 2 → Nov 8** (RAG pipeline, core API, chat UI, auth/RBAC, PII redaction) |
| Days to demo-ready (Nov 16) | **14** |
| Sprint 0 (Oct 28 → Nov 1) | ✅ Engineering goals met · 🟡 sharing/accounts tasks still open (see §4) |
| Feature checklist (PROJECT_PLAN §5) | 0 / 13 shipped · 13 / 13 fully **designed** |
| GitHub issues | 13 open · 0 closed · 1 PR merged ([#14](https://github.com/jopintor/dinkledoodldesk/pull/14)) |
| CI | ✅ All 4 runs green (backend lint+tests, frontend lint+build, Docker Compose smoke test) |
| Overall | Design and content phase is done. **Build phase starts today** — nothing user-facing works yet beyond a health check. |

### Progress by track

| # | Track | Owner | Status | Rough % | One-line state |
|---|---|---|---|---|---|
| T1 | Project management | Jose | 🟡 | 70% | Plan, board, sprints, roles all set; a few sharing/accounts items left |
| T2 | Technical docs (`/docs`) | Jose + Andre | ✅ | 95% | Six design docs done (~2,100 lines); 16 defaults await Jose's confirmation |
| T3 | Project documentation (Google Doc) | Jose | 🟡 | 45% | 8 of 14 sections drafted; not shared yet |
| T4 | Knowledge base & golden set | Jose | ✅ | 100% | 28 KB docs + 50-question golden set |
| T5 | DevOps & infrastructure | Jose | 🟡 | 60% | Repo, compose, CI work; 2 containers + env vars still to add; Docker not on Jose's PC |
| T6 | Backend & API | Andre | 🟡 | 10% | Skeleton + `/health` + LLM provider switch; no DB models or endpoints yet |
| T7 | AI / RAG | Jose | 🟡 | 15% | Fully designed; LLM provider layer coded; no ingestion/retrieval yet |
| T8 | Automation & integrations | Andre | ⬜ | 5% | n8n container runs; workflows, tools and Jira not started |
| T9 | Security & guardrails | Jose + Andre | ⬜ | 5% | Fully designed; nothing coded |
| T10 | UI/UX design (Figma) | Jose → Arjan | 🟡 | 70% | Style guide + 7 screens done; not shared with Arjan yet |
| T11 | Frontend (Next.js) | Arjan | 🟡 | 5% | Scaffold + health page + mock API route only |
| T12 | QA, testing & evaluation | Andre | 🟡 | 15% | Golden set ready; 2 unit tests; no eval harness, load or E2E tests |
| T13 | Demo, presentation & defense | Jose | ⬜ | 0% | Slot (Wk 16 vs 17) still unknown |
| T14 | Course assessments (Wk 13–15) | Jose / Andre | 🟡 | — | Wk 14 material exists in `/docs`; Wk 13 and Wk 15 not tracked yet |

> "Rough %" is a judgement call for planning, not a measured number.

---

## 2. Timeline

| Sprint | Dates | Goal | Status |
|---|---|---|---|
| 0 | Oct 28 – Nov 1 | Repo + Docker skeleton, KB content, architecture/ERD/prompt design, Figma, Google Doc started | ✅ done (sharing items carried over) |
| **1** | **Nov 2 – Nov 8** | RAG pipeline, core API, chat UI, auth/RBAC, basic PII redaction | 🟡 **starts today** |
| 2 | Nov 9 – Nov 15 | Function calling, n8n, escalation, agent + admin dashboards, injection guardrails, load test + vuln scan | ⬜ |
| 3 | Nov 16 – Nov 22 | Eval run & metrics, bug fixes, slides, demo script, backup video | ⬜ |
| 4 | Nov 23 – Dec 7 | Defense, final documentation, final product submission | ⬜ |

Key dates: **Nov 16** demo-ready · **Nov 16–27** presentation (Wk 16 or 17) · **Nov 30 – Dec 7** final product.

---

## 3. Feature checklist (PROJECT_PLAN §5) — status by requirement

| Requirement | Issue | Sprint | Owner | Designed | Built | Tested |
|---|---|---|---|---|---|---|
| Conversational AI chat for IT requests | [#5](https://github.com/jopintor/dinkledoodldesk/issues/5) | 1 | Jose + Arjan | ✅ | ⬜ | ⬜ |
| RAG over SOPs/FAQs/policies with citations | [#4](https://github.com/jopintor/dinkledoodldesk/issues/4) | 1 | Jose | ✅ | ⬜ | ⬜ |
| ChromaDB vector store (ingest KB) | [#3](https://github.com/jopintor/dinkledoodldesk/issues/3) | 1 | Jose | ✅ | 🟡 container only | ⬜ |
| FastAPI backend: core API, Postgres models, migrations | [#2](https://github.com/jopintor/dinkledoodldesk/issues/2) | 1 | Andre | ✅ | 🟡 skeleton | 🟡 `/health` |
| RBAC, PII redaction, input validation, secrets | [#6](https://github.com/jopintor/dinkledoodldesk/issues/6) | 1 | Andre | ✅ | 🟡 secrets only | ⬜ |
| Function calling (reset password, Jira ticket, service status) | [#7](https://github.com/jopintor/dinkledoodldesk/issues/7) | 2 | Andre | ✅ (4 tools) | ⬜ | ⬜ |
| n8n / webhook automation | [#8](https://github.com/jopintor/dinkledoodldesk/issues/8) | 2 | Andre | ✅ | 🟡 container only | ⬜ |
| Human escalation + prompt-injection guardrails | [#9](https://github.com/jopintor/dinkledoodldesk/issues/9) | 2 | Jose | ✅ | ⬜ | ⬜ |
| Frontend: user chat + agent/admin dashboards | [#10](https://github.com/jopintor/dinkledoodldesk/issues/10) | 2 | Arjan | ✅ (Figma) | 🟡 scaffold | ⬜ |
| Tests & metrics (5 categories + eval run) | [#11](https://github.com/jopintor/dinkledoodldesk/issues/11) | 3 | Andre | ✅ | 🟡 golden set | ⬜ |
| Documentation (architecture, ERD, API, AI, setup, manual) | [#12](https://github.com/jopintor/dinkledoodldesk/issues/12) | 4 | Jose | ✅ | 🟡 tech docs done | — |
| Git repo, branching, env config, Docker | [#1](https://github.com/jopintor/dinkledoodldesk/issues/1) | 0 | Jose | ✅ | ✅ | ✅ CI | 
| Live demo + defense | [#13](https://github.com/jopintor/dinkledoodldesk/issues/13) | 4 | Jose | ⬜ | ⬜ | ⬜ |

---

## 4. Tracks in detail

### T1 · Project management & coordination — 🟡 (Jose)

**Done**
- ✅ Master plan written and kept current: [PROJECT_PLAN.md](PROJECT_PLAN.md) (scenario, stack, sprints, workstreams, rules).
- ✅ Team roles fixed (2026-10-28): Jose = PM + AI/RAG + DevOps; Andre = backend/automation + QA; Arjan = frontend/UI.
- ✅ Private repo [jopintor/dinkledoodldesk](https://github.com/jopintor/dinkledoodldesk) + [Projects board](https://github.com/users/jopintor/projects/1).
- ✅ Milestones Sprint 0–4, issues #1–#13 mapped 1:1 to the feature checklist, `owner:*` and `area:*` labels.
- ✅ Andre (`dremnty122`) and Arjan (`sarinasavs`) added as collaborators and board writers; issues assigned (Andre #2 #6 #7 #8 #11, Arjan #5 #10).
- ✅ [CONTRIBUTING.md](../../CONTRIBUTING.md): branch + PR workflow (first PR merged: #14).

**Open**
- ⚠️ Ask Mr. Gregana for the exact presentation slot (Week 16 or 17).
- ⚠️ Collect teammates' emails → share the Google Doc.
- ⚠️ Share the Figma file with Arjan (see T10).
- ⚠️ Create the Jira Cloud free site (project key `ITH`).
- ⬜ Close #1 (its scope is met) and move Sprint 1 issues to "In progress" on the board.
- ⬜ Commit the pending PROJECT_PLAN.md edit (Figma link + collaborators note) — currently uncommitted.
- ⬜ Delete the merged remote branch `docs/12-kb-eval-design`.

### T2 · Technical documentation (`/docs`) — ✅ (Jose + Andre)

**Done** — design v1, 2026-10-28, merged in PR #14. Diagrams are Mermaid (render on GitHub).

| Doc | Lines | Covers | Maps to |
|---|---|---|---|
| [docs/architecture.md](../../docs/architecture.md) | 386 | System diagram, chat-turn sequence, component spec, Gemini rate-limit handling, LLM/tool failure handling, deployment view, provider swap | Template §6 · **Wk 14 assessment** |
| [docs/database.md](../../docs/database.md) | 363 | ERD per domain, entities, indexes, retention, KPI formulas | Template §7 |
| [docs/api.md](../../docs/api.md) | 551 | All REST endpoints, SSE streaming, RBAC per endpoint, n8n webhooks | Template §6 / API docs |
| [docs/ai-design.md](../../docs/ai-design.md) | 347 | RAG pipeline, chunking, hybrid search, confidence→action, citations, intents, system prompt v1, 4 tool schemas, prompt table | Template §9 |
| [docs/guardrails-and-security.md](../../docs/guardrails-and-security.md) | 232 | PII redaction, injection defences, validation, auth, RBAC matrix, secrets, audit log, threat model | Governance criterion |
| [docs/automation.md](../../docs/automation.md) | 224 | n8n WF-01…WF-05 + WF-99, payloads, workflow tests | Template §10 |

**Open**
- ⚠️ Jose to confirm the **16 design defaults** in [docs/README.md](../../docs/README.md#decisions-to-confirm-jose) (only #2, Jira key `ITH`, is decided). The ones that change work this sprint: 4 tools not 3 (#1), extra containers (#3), new env vars (#4), Gemini model/quota check (#5), thresholds 0.70/0.50 (#8), auth approach (#14).
- ⬜ Setup guide in README once the stack actually runs end-to-end (Sprint 2–3).
- ⬜ User manual with screenshots (Arjan, Sprint 3–4).
- ⬜ Keep docs in sync when implementation diverges (whoever changes the code updates the doc).

### T3 · Project documentation Google Doc (workstream D) — 🟡 (Jose)

[DinkDesk – AI-HAS Project Documentation](https://docs.google.com/document/d/1-9LpgU4tLxokY8w43LFUwOjdnqSnSjiqdxhE_A7BA54/edit) — created 2026-10-28, follows the 14-section course template.

| Sections | Status |
|---|---|
| 1–5, 11, 12, 14 | ✅ drafted |
| 6 System Architecture, 7 Database Design, 9 AI Prompt Design, 10 Workflow Automation | ⬜ placeholders — **can be filled now** from `/docs` |
| 8 (implementation/UI) | ⬜ waits on built screens |
| 13 Testing / QA | ⬜ waits on the Wk 15 QA report |

**Open**
- ⬜ Port `/docs` content into §6, §7, §9, §10.
- ⬜ Fix "3 tools" → 4 tools (design decision #1).
- ⚠️ Share with Andre and Arjan (needs emails).

### T4 · Knowledge base & golden test set (workstream B) — ✅ (Jose)

**Done**
- ✅ [knowledge-base/](../../knowledge-base/README.md): **28 documents** — KB-000 company profile (PickleHub Clubs, branches DAS·IMS·BAC·GTR·TAG) + KB-001…KB-027 SOPs, FAQs and policies covering passwords/StaffID, lockout, MFA, HubMail, CourtBook, DinkPOS, RallyBracket, HubWatch CCTV, access requests, Wi-Fi, VPN, card terminals, printers, member app, booking bugs, on/offboarding, AUP, privacy, escalation/SLA, status page, phishing.
- ✅ Deliberate traps for retrieval testing: overlapping docs and **KB-014 superseded** remote-access policy.
- ✅ Consistency rules and writing rules documented in the KB README.
- ✅ [eval/golden-set/golden_set.jsonl](../../eval/golden-set/golden_set.jsonl): **50 questions** with expected sources, expected behaviour and reference answers.

| Golden set breakdown | Count |
|---|---|
| normal | 20 |
| ambiguous | 6 |
| malicious (prompt injection) | 6 |
| PII | 5 |
| action request | 5 |
| unsupported | 4 |
| low confidence | 4 |
| **Expected behaviour:** answer 22 · refuse 11 · escalate 7 · clarify 6 · tool call 4 | |
| **Roles:** staff 36 · member 12 · agent 2 | |

**Open** — nothing blocking. Add questions only if the eval run in Sprint 3 shows gaps.

### T5 · DevOps & infrastructure — 🟡 (Jose)

**Done**
- ✅ Repo scaffold: `.gitignore` (excludes root PDFs and `.env`), `.gitattributes`, `.env.example`, README, CONTRIBUTING.
- ✅ [infra/docker-compose.yml](../../infra/docker-compose.yml): Postgres 16, ChromaDB 1.5.9, n8n 2.45.4, backend, frontend — all with healthchecks.
- ✅ Dockerfiles for backend and frontend.
- ✅ [CI](../../.github/workflows/ci.yml): backend (ruff lint + format + pytest), frontend (eslint + build/type-check), **Docker Compose smoke test** (brings the stack up, curls backend `/health`, Chroma heartbeat, n8n `/healthz`). All runs green.
- ✅ Jira key `ITH` set in `.env.example` and `backend/app/config.py`.
- ✅ Local backend venv on Python 3.12.

**Open**
- 🔴 **Docker Desktop + WSL2 not installed on Jose's PC** (needs admin + reboot). Until then the full stack is only verified in CI. Needed before Sprint 2 integration work and the demo.
- ⬜ Add `mock-directory` (port 8090) and `mailpit` (8025/1025) containers (design decision #3).
- ⬜ Add the new env vars to `.env.example` + `config.py`: fallback model, embedding dimension, LLM limiter, JWT secret, n8n token/HMAC, directory URL/key, SMTP, `SLA_TEST_MODE` (decision #4).
- ⬜ Get a Gemini API key into the local `.env`; check current free-tier limits (decision #5).
- ⬜ Cloudflare quick tunnel so Arjan can hit the backend on Jose's PC (Sprint 1–2).
- ⬜ `/automation/n8n/` folder for workflow exports (Sprint 2).

### T6 · Backend & API (FastAPI + Postgres) — 🟡 (Andre) · Sprint 1 · [#2](https://github.com/jopintor/dinkledoodldesk/issues/2), [#6](https://github.com/jopintor/dinkledoodldesk/issues/6)

**Done**
- ✅ FastAPI app with CORS and `GET /health` ([backend/app/main.py](../../backend/app/main.py)).
- ✅ Typed settings with safe defaults ([backend/app/config.py](../../backend/app/config.py)); secrets as `SecretStr`.
- ✅ Swappable LLM provider layer: `base` interface, Gemini + OpenAI implementations, factory ([backend/app/llm/](../../backend/app/llm/)).
- ✅ Tests: `test_health.py`, `test_llm_factory.py`.

**Next (Sprint 1)**
- ⬜ SQLAlchemy models + Alembic migrations from [docs/database.md](../../docs/database.md) (users/roles/branches, conversations/messages, tickets, escalations, KB docs, audit log).
- ⬜ Seed script: demo accounts for every role (incl. two admins — decision #10), branches, services.
- ⬜ `POST /auth/login`, `GET /auth/me` (JWT 60 min) + RBAC dependency.
- ⬜ Conversation endpoints: `POST /conversations`, `POST /conversations/{id}/messages` (+ SSE stream).
- ⬜ Error envelope, input validation, rate limiting per [docs/api.md §1](../../docs/api.md).
- ⬜ PII redaction middleware (basic version this sprint).

### T7 · AI / RAG (Gemini + LangChain + ChromaDB) — 🟡 (Jose) · Sprint 1 · [#3](https://github.com/jopintor/dinkledoodldesk/issues/3), [#4](https://github.com/jopintor/dinkledoodldesk/issues/4), [#5](https://github.com/jopintor/dinkledoodldesk/issues/5)

**Done**
- ✅ Full design: chunking, embeddings (`gemini-embedding-001`, 768-d), hybrid search, confidence score → answer / clarify / escalate, citation format, intent taxonomy, system prompt v1, prompt design table, versioning loop ([docs/ai-design.md](../../docs/ai-design.md)).
- ✅ LLM provider abstraction (shared with T6).

**Next (Sprint 1)**
- ⬜ KB ingestion script: parse front-matter → chunk → embed → upsert to Chroma (KB-014 down-ranked ×0.5).
- ⬜ Retriever + confidence scoring (thresholds 0.70 / 0.50).
- ⬜ Answer generation with citations; one LLM call per turn (decision #6).
- ⬜ Intent classification by embedding similarity (decision #7).
- ⬜ LLM rate limiter + fallback model + response cache for demo questions.
- ⬜ Quick smoke run of the 20 "normal" golden questions to sanity-check retrieval.

### T8 · Automation & integrations (function calling, n8n, Jira) — ⬜ (Andre) · Sprint 2 · [#7](https://github.com/jopintor/dinkledoodldesk/issues/7), [#8](https://github.com/jopintor/dinkledoodldesk/issues/8)

**Done**
- ✅ Design: 4 tool schemas (`reset_password`, `create_ticket`, `check_service_status`, `escalate_to_agent`), n8n workflows WF-01…WF-05 + WF-99, outbox pattern, HMAC-signed callbacks, Jira polling ([docs/automation.md](../../docs/automation.md)).
- ✅ n8n container runs in compose (smoke-tested in CI).

**Next (Sprint 2)**
- ⬜ Tool executor with confirm/verify flow (`/tool-calls/{id}/confirm`, `/verify`).
- ⬜ Mock directory service for StaffID resets (OTP via Mailpit).
- ⬜ Transactional outbox → n8n webhooks.
- ⬜ WF-01 ticket → Jira, WF-02 escalation + SLA reminder, WF-03 privileged-reset approval, WF-04 Jira status poll, WF-99 error handler.
- ⬜ Export workflows (no credentials) to `/automation/n8n/`.
- ⚠️ Depends on the Jira Cloud site (T1).

### T9 · Security & guardrails — ⬜ (Jose + Andre) · Sprint 1–2 · [#6](https://github.com/jopintor/dinkledoodldesk/issues/6), [#9](https://github.com/jopintor/dinkledoodldesk/issues/9)

**Done**
- ✅ Design: layered guardrails, PII patterns, injection heuristics, capability limiting, output checks, RBAC matrix, audit events, threat model ([docs/guardrails-and-security.md](../../docs/guardrails-and-security.md)).
- ✅ Secrets only from `.env` (gitignored), `.env.example` committed, restricted course PDFs excluded from git.

**Next**
- ⬜ Sprint 1: PII redaction (irreversible — decision #13), input validation, RBAC enforcement.
- ⬜ Sprint 2: injection heuristics, escalation on low confidence / sensitive intents, guardrail event log (feeds the "Try to break DinkDesk" demo panel), audit logging.
- ⬜ Sprint 2: vulnerability scan (e.g. `pip-audit`, `npm audit`, OWASP ZAP baseline).

### T10 · UI/UX design (Figma, workstream E) — 🟡 (Jose → Arjan)

[DinkDesk – UI Design](https://www.figma.com/design/R0qIVGw2OPSdFTaDaCHqzs) — created 2026-10-29.

**Done**
- ✅ Pages: "Start here – Arjan", "Style guide" (variables + components), "Screens".
- ✅ Screens: login, chat desktop ×2, chat mobile, agent queue, admin KPI dashboard, knowledge base.
- ✅ Design decisions approved by Jose (2026-10-30): cream `#F7F4EC` + dark green `#3F6136`, yellow accents only; Outfit + Plus Jakarta Sans; "StaffID" wording; Staff & IT / Member login toggle; tagline *"Soft shots for hard IT problems."*; tickets shown as `DD-… → ITH-…`; mobile layout for chat only.

**Open**
- ⚠️ **Share the Figma file with Arjan** — frontend work is blocked until Arjan has it.
- ⬜ Screens still to design (as needed): escalation/takeover view, password-reset confirm/OTP flow, approvals queue, guardrail log panel, eval scorecard.

### T11 · Frontend (Next.js) — 🟡 (Arjan) · Sprint 1–2 · [#5](https://github.com/jopintor/dinkledoodldesk/issues/5), [#10](https://github.com/jopintor/dinkledoodldesk/issues/10)

**Done**
- ✅ Next.js + TypeScript + Tailwind scaffold, ESLint, Dockerfile.
- ✅ Placeholder home page that calls the backend `/health` ([frontend/src/app/page.tsx](../../frontend/src/app/page.tsx)).
- ✅ API client with configurable base URL: local backend, Cloudflare tunnel, or built-in `/mock-api` ([frontend/src/lib/api.ts](../../frontend/src/lib/api.ts)) — Arjan never needs Docker.

**Next**
- ⬜ Sprint 1: apply style guide (fonts, colour tokens), login page, chat widget (messages, citations, streaming), mock fixtures from [docs/api.md](../../docs/api.md) (MSW — decision #15).
- ⬜ Sprint 2: agent queue + takeover, admin KPI dashboard, KB admin page, guardrail log panel.
- ⬜ Sprint 3: Playwright E2E for the main flows; screenshots for the user manual.

### T12 · QA, testing & evaluation — 🟡 (Andre) · [#11](https://github.com/jopintor/dinkledoodldesk/issues/11)

**Done**
- ✅ 50-question golden set covering all required test categories (normal, ambiguous, unsupported, malicious, low-confidence + PII and actions).
- ✅ Metric definitions: faithfulness, relevance, behaviour accuracy, deflection, tool success, latency ([eval/golden-set/README.md](../../eval/golden-set/README.md)); KPI formulas in [docs/database.md §8](../../docs/database.md).
- ✅ pytest + CI wired up (2 tests passing).
- ✅ n8n workflow test cases written ([docs/automation.md §8](../../docs/automation.md)).

**Next**
- ⬜ Unit/integration tests alongside every Sprint 1 feature.
- ⬜ Eval runner script (golden set → metrics JSON) — needed by Sprint 3, useful as soon as RAG works.
- ⬜ Sprint 2: load test (Locust or k6), vuln scan, **Wk 15 QA report** with git history of fixes.
- ⬜ Sprint 3: full eval run, threshold calibration, before/after prompt iterations.

### T13 · Demo, presentation & defense — ⬜ (Jose) · [#13](https://github.com/jopintor/dinkledoodldesk/issues/13)

- ⚠️ Confirm presentation slot (Wk 16 vs Wk 17).
- ⬜ Demo script (Sprint 3) — include "Try to break DinkDesk" live segment and eval scorecard.
- ⬜ Slides (Sprint 3).
- ⬜ Backup demo video + cached answers for demo questions (in case of Gemini rate limits).
- ⬜ Rehearsal on the demo host (Jose's 32 GB PC) — needs Docker installed (T5).

### T14 · Course enabling assessments (reused as project work)

| Week | Assessment | Reuses | Status |
|---|---|---|---|
| 13 | Risk-mitigation framework (privacy / data governance) | [docs/guardrails-and-security.md](../../docs/guardrails-and-security.md), KB-023 privacy policy | ⚠️ status not tracked — confirm whether it was submitted |
| 14 | Architecture diagram + component spec | [docs/architecture.md](../../docs/architecture.md) §2–§3 | 🟡 content ready; format and submit |
| 15 | QA report + git history | T12 Sprint 2 output | ⬜ |

---

## 5. Blockers & risks

| Risk / blocker | Impact | Owner | Mitigation |
|---|---|---|---|
| Docker not installed on Jose's PC | Can't run the full stack locally or rehearse the demo | Jose | Install Docker Desktop + WSL2 this week; CI smoke test covers the gap meanwhile |
| Figma not shared with Arjan | Frontend can't start | Jose | Share today |
| Jira site doesn't exist | WF-01/WF-04 can't be built or tested | Jose | Create before Sprint 2 (Nov 9) |
| Gemini free-tier limits | Rate-limited demo or eval runs | Jose | Limiter + fallback model + response cache + backup video |
| Compressed schedule (8 weeks → ~5) | Sprint 2 is very heavy | Jose | Keep scope at 4 tools; WF-05 is optional; cut showcase ideas before core features |
| Arjan's weak laptop | Slow frontend dev | Arjan | Mock API / MSW, no Docker; tunnel to Jose's backend |
| 16 unconfirmed design defaults | Rework if changed late | Jose | Confirm in Sprint 1 week 1 |

---

## 6. Changelog

| Date | What landed |
|---|---|
| 2026-10-28 | Plan written; roles decided; repo + board + milestones + issues #1–#13; repo scaffold, backend, frontend, compose and CI (`7d1d152`); Jira key → `ITH` (`ffe466a`); Google Doc created (sections 1–5, 11, 12, 14) |
| 2026-10-28 | PR #14 merged: knowledge base (28 docs), 50-question golden set, six technical design docs (`3979772`) |
| 2026-10-29 | Figma design file created (style guide + 7 screens) |
| 2026-10-30 | Figma design decisions approved by Jose |
| 2026-11-02 | Sprint 1 starts; this progress tracker created |
