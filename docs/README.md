# DinkDesk — Technical Design (`/docs`)

Workstream C of [PROJECT_PLAN.md](team/PROJECT_PLAN.md). Diagrams are Mermaid and render on GitHub. Design v1, 2026-10-28.

> **Prototype scope (2026-11-09):** these docs describe the full design. We build only what [PROJECT_PLAN.md §5](team/PROJECT_PLAN.md) lists: 2 tools (`create_ticket`, `reset_password`), n8n WF-01 (+ WF-02 if time), chat, one admin dashboard, read-only escalation list. Tools `check_service_status`/`escalate_to_agent`, WF-03…WF-05, SLA reminders, outbox/HMAC callbacks, agent takeover, KB admin page and mobile layout are **future work**.

| Document | Contents | Template section / assessment |
|---|---|---|
| [architecture.md](architecture.md) | System diagram, chat-turn sequence, component specification, data dependencies, Gemini rate-limit handling, LLM and tool failure handling, deployment view, provider swap | §6 System Architecture · **Week 14** architecture + component spec |
| [database.md](database.md) | ERD (per domain + overview), entity descriptions, indexes, retention, KPI formulas | §7 Database Design |
| [api.md](api.md) | REST endpoints with request/response shapes, SSE streaming events, RBAC per endpoint, webhooks | §6 / API docs |
| [ai-design.md](ai-design.md) | RAG pipeline, chunking, embeddings, hybrid search, confidence → escalation, citations, intent taxonomy, system prompt, tool schemas, prompt design table, eval metrics | §9 AI Prompt Design |
| [guardrails-and-security.md](guardrails-and-security.md) | PII redaction, prompt-injection defences, input validation, auth, RBAC matrix, secrets, audit logging, threat model | Governance & security criterion |
| [automation.md](automation.md) | n8n workflows in `[User Request] → [AI] → [Decision] → [Action/Notification]` form, payloads, tests | §10 Workflow Automation |

Names used everywhere (kept consistent with `/knowledge-base` and the root `.env.example`): roles `member · staff · agent · admin`; tools `reset_password · create_ticket · check_service_status · escalate_to_agent`; local tickets `DD-000123`, Jira project `ITH`; branches `DAS · IMS · BAC · GTR · TAG`; service keys and status values from KB-025; priorities P1–P4 from KB-024.

## Decisions to confirm (Jose)

These were not fixed by PROJECT_PLAN.md, so the design picked a default. Change any of them and update the docs that mention it.

1. **Four tools, not three.** `escalate_to_agent` is a function-calling tool alongside the three in the plan. The Google Doc (workstream D) currently says "3 tools" and needs updating.
2. ~~Jira project key~~ **Decided: `ITH`** (from KB-000/KB-020), so it doesn't clash with DinkDesk's own `DD-…` ticket numbers (KB-026). Workstream A has already set `JIRA_PROJECT_KEY=ITH` in `.env.example` and `backend/app/config.py`.
3. **Two extra containers**: `mock-directory` (port 8090) for the mocked StaffID directory and `mailpit` (8025/1025) as a local inbox for all demo emails and "SMS" codes. Workstream A's compose file needs them.
4. **New env vars** (listed in [architecture.md §5.1](architecture.md#51-planning-assumptions) and the shared notes): fallback model, embedding dimension, LLM limiter settings, JWT, n8n token/HMAC secrets, directory URL/key, SMTP, `SLA_TEST_MODE`.
5. **Gemini models and limits**: defaults `gemini-2.5-flash` → fallback `gemini-2.5-flash-lite`, `gemini-embedding-001` at 768 dimensions; our own ceilings 8 RPM / 200 RPD. Check the current free-tier numbers before Sprint 1.
6. **One generation call per turn**: tool results are shown from templates rather than sent back to the LLM for rephrasing. This saves quota and blocks one injection path, but replies after tool calls sound more scripted.
7. **Intent classification by embedding similarity** (no extra LLM call), with an LLM fallback only when unsure.
8. **Confidence thresholds 0.70 / 0.50** are starting values, to be calibrated on the golden set in Sprint 3. Below 0.50 the LLM is not called at all.
9. **KB-014 (superseded)** is indexed but down-ranked ×0.5 and labelled `[SUPERSEDED]`, not excluded.
10. **Privileged password resets** (agent/admin accounts) need an admin's approval in the dashboard. Approvals are not done by clicking links in emails. Normal staff resets complete after the OTP. Two admin demo accounts are needed because self-approval is blocked.
11. **Every escalation creates a ticket**, and P1/P2 tickets also escalate (KB-024 §4).
12. **Backend never calls Jira directly**: a transactional outbox sends events to n8n, and n8n polls Jira every 5 minutes instead of receiving Jira webhooks. This means n8n is never exposed to the internet.
13. **Redaction is irreversible**: raw user text is never stored, so agents also see only redacted messages.
14. **Auth**: seeded demo accounts, JWT 60 min with no refresh token, token kept in `sessionStorage`. Real SSO is out of scope.
15. **Arjan's offline mode** uses Mock Service Worker fixtures built from [api.md](api.md). Live mode goes through a Cloudflare quick tunnel that exposes only the backend.
16. **Golden-set field names** follow workstream B (`user_role`, `expected_source_ids`, `expected_behavior`). There is no `expected_intent` label, so intent accuracy is optional.
