# DinkDesk — REST API Specification

> Workstream C · owner: Andre (implementation) · consumers: Arjan (frontend), n8n · status: **design v1** · last updated 2026-10-28
>
> FastAPI generates the live OpenAPI schema at `/api/v1/openapi.json` and Swagger UI at `/api/v1/docs`; this document is the design contract the implementation and the frontend's mock fixtures both follow. If code and this file disagree, fix one of them in the same PR.
>
> Related: [architecture.md](architecture.md) · [database.md](database.md) · [guardrails-and-security.md](guardrails-and-security.md) · [automation.md](automation.md)

## 1. Conventions

### 1.1 Base URL and versions

| Environment | Base URL |
|---|---|
| Docker on Jose's PC | `http://localhost:8000/api/v1` |
| Arjan via tunnel | `https://<random>.trycloudflare.com/api/v1` |
| Frontend mock mode | intercepted by Mock Service Worker, same paths |

### 1.2 Authentication

- Users: `Authorization: Bearer <JWT>` from `POST /auth/login`. Token lifetime 60 min (`JWT_EXPIRES_MIN`). The role is re-read from the database on every request.
- n8n → backend: no JWT. Requests carry `X-DinkDesk-Timestamp` (unix seconds) and `X-DinkDesk-Signature: sha256=<hex HMAC of "<timestamp>.<raw body>" with N8N_CALLBACK_SECRET>`. Requests older than 5 minutes are rejected. Principal name in RBAC tables: **`n8n`**.
- Backend → n8n webhooks use n8n's Header Auth: `X-N8N-Token: <N8N_WEBHOOK_TOKEN>`.

### 1.3 RBAC notation

`public` = no auth · `M` member · `S` staff · `A` agent · `Ad` admin · `n8n` service principal.
"own" = only resources the caller owns (e.g. their own conversations); the API returns **404** (not 403) for other people's resources so it does not reveal that they exist.

### 1.4 Error envelope

Every non-2xx response:

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many messages. Try again in 12 seconds.",
    "request_id": "01JBX7Q2S3K9V6M0R3T5WZ8Y1A",
    "details": { "retry_after_s": 12 }
  }
}
```

| HTTP | `code` examples |
|---|---|
| 400 | `BAD_REQUEST`, `INPUT_TOO_LONG` |
| 401 | `UNAUTHENTICATED`, `TOKEN_EXPIRED`, `INVALID_SIGNATURE` |
| 403 | `FORBIDDEN` (role not allowed for this endpoint) |
| 404 | `NOT_FOUND` |
| 409 | `CONFLICT`, `INVALID_STATE` (e.g. confirming a tool call that already ran) |
| 422 | `VALIDATION_ERROR` (FastAPI field errors in `details`) |
| 429 | `RATE_LIMITED` (+ `Retry-After` header) |
| 503 | `LLM_UNAVAILABLE`, `DEPENDENCY_DOWN` (only when even degraded mode is impossible) |

### 1.5 Rate limits

| Scope | Limit | Applies to |
|---|---|---|
| Per user | 20 chat messages / min, 200 / day | `POST /conversations/{id}/messages*` |
| Per IP | 5 / min, 20 / hour | `POST /auth/login` |
| Per user | 5 / 10 min | `POST /tool-calls/{id}/verify` (OTP attempts are also capped at 3 per tool call) |
| Per user | 60 req / min | all other endpoints |

Implemented with `slowapi` (in-memory; the backend runs a single worker). LLM-side quota handling is separate — see [architecture.md §5](architecture.md#5-api-rate-limiting-gemini-free-tier-and-llm-failure-handling).

### 1.6 Pagination and time

List endpoints accept `?limit=` (default 20, max 100) and `?cursor=` and return `{ "items": [...], "next_cursor": "..." | null }`. Timestamps are ISO-8601 UTC (`2026-11-05T02:14:00Z`).

## 2. Endpoint summary

| # | Method & path | Purpose | Roles |
|---|---|---|---|
| **Auth** | | | |
| 1 | `POST /auth/login` | Sign in, get JWT | public |
| 2 | `POST /auth/logout` | Revoke current token (denylist until expiry) | M S A Ad |
| 3 | `GET /auth/me` | Current user + permissions | M S A Ad |
| **Chat** | | | |
| 4 | `POST /conversations` | Start a conversation | M S A Ad |
| 5 | `GET /conversations` | List conversations | M S (own) · A Ad (all, filterable) |
| 6 | `GET /conversations/{id}` | Conversation with messages, tool calls, linked tickets | owner · A Ad |
| 7 | `POST /conversations/{id}/messages` | Send a message, get the full reply (non-streaming) | owner |
| 8 | `POST /conversations/{id}/messages/stream` | Send a message, reply streamed as SSE | owner |
| 9 | `POST /conversations/{id}/resolve` | "This solved my problem" | owner |
| 10 | `POST /messages/{id}/feedback` | Thumbs up/down on an assistant message | owner |
| 11 | `POST /tool-calls/{id}/confirm` | Confirm a proposed action (optionally with edited args) | owner |
| 12 | `POST /tool-calls/{id}/cancel` | Cancel a proposed action | owner |
| 13 | `POST /tool-calls/{id}/verify` | Submit the OTP for a password reset | owner |
| **Tickets** | | | |
| 14 | `GET /tickets` | List tickets | M S (own) · A Ad (all) |
| 15 | `POST /tickets` | Create a ticket manually (form, no AI) | M S A Ad |
| 16 | `GET /tickets/{id}` | Ticket detail | owner · A Ad |
| 17 | `PATCH /tickets/{id}` | Update status / priority / assignee / add note | A Ad |
| **Escalations & human takeover** | | | |
| 18 | `GET /escalations` | Agent queue | A Ad |
| 19 | `POST /escalations/{id}/claim` | Agent takes over the conversation (AI paused) | A Ad |
| 20 | `POST /conversations/{id}/agent-messages` | Agent replies in the user's chat | A (assigned) · Ad |
| 21 | `POST /escalations/{id}/resolve` | Close the escalation, hand back to AI or close chat | A (assigned) · Ad |
| **Approvals** | | | |
| 22 | `GET /approvals` | Pending password-reset approvals | Ad |
| 23 | `POST /approvals/{tool_call_id}/decision` | Approve / reject | Ad |
| **Service status** | | | |
| 24 | `GET /services/status` | All PickleHub systems' status | public |
| 25 | `PUT /services/{service_key}/status` | Set status (stage an incident) | Ad |
| **Knowledge base admin** | | | |
| 26 | `GET /kb/documents` | List KB documents | A Ad |
| 27 | `GET /kb/documents/{doc_id}` | Document + chunks | A Ad |
| 28 | `POST /kb/documents` | Upload a Markdown document (multipart) | Ad |
| 29 | `PUT /kb/documents/{doc_id}` | Replace a document (re-indexes it) | Ad |
| 30 | `DELETE /kb/documents/{doc_id}` | Archive (soft delete, removes vectors) | Ad |
| 31 | `POST /kb/reindex` | Re-index from `/knowledge-base` (changed docs, or `full`) | Ad |
| 32 | `GET /kb/reindex/{job_id}` | Re-index job progress | Ad |
| 33 | `POST /kb/search` | Retrieval debug: show chunks + scores for a query | A Ad |
| **Metrics, eval, audit** | | | |
| 34 | `GET /metrics/summary` | KPI cards for a period | Ad (A: read-only subset) |
| 35 | `GET /metrics/timeseries` | One KPI over time | Ad |
| 36 | `GET /guardrail-events` | Guardrail log feed (polled every 2 s on the demo panel) | Ad |
| 37 | `GET /eval/runs` · `GET /eval/runs/{id}` | Evaluation scorecard | Ad |
| 38 | `POST /eval/runs` | Import results produced by `/eval` scripts | Ad |
| 39 | `GET /audit-logs` | Audit trail | Ad |
| 40 | `GET /users` · `PATCH /users/{id}` | List users, change role / deactivate | Ad |
| **Webhooks & internal (n8n)** | | | |
| 41 | `POST /webhooks/n8n/ticket-synced` | Jira issue created for a ticket | n8n |
| 42 | `POST /webhooks/n8n/ticket-updated` | Jira status changed (from 5-min poll) | n8n |
| 43 | `POST /webhooks/n8n/delivery-failed` | A workflow failed after its retries | n8n |
| 44 | `GET /internal/escalations/{id}` | Status check used by SLA reminder | n8n |
| 45 | `GET /internal/tool-calls/{id}` | Status check used by approval reminder | n8n |
| 45b | `GET /internal/metrics/daily` | Yesterday's KPI summary for the daily digest (WF-05) | n8n |
| **Health** | | | |
| 46 | `GET /health` | Liveness | public |
| 47 | `GET /health/ready` | Readiness: Postgres, Chroma, LLM breaker state, directory | public (no secrets in output) |

## 3. Auth

### `POST /auth/login`

```json
// request
{ "email": "kat.mendoza@picklehub.example", "password": "••••••••" }
// 200
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "0192f1c4-...", "email": "kat.mendoza@picklehub.example", "full_name": "Kat Mendoza",
    "role": "agent", "club_code": "DAS", "job_title": "Service Desk Agent"
  }
}
```

Failure: `401 UNAUTHENTICATED` with a generic message ("Email or password is incorrect") for both unknown email and wrong password. Every attempt writes `audit_logs` (`auth.login`).

### `GET /auth/me`

```json
{ "user": { "...": "as above" },
  "permissions": ["chat:use", "tickets:read:all", "escalations:claim", "kb:read"] }
```

The frontend uses `permissions` to show/hide dashboard sections; the backend enforces them independently.

## 4. Chat

### `POST /conversations`

```json
// request (optional first message makes it one round trip)
{ "channel": "web" }
// 201
{ "id": "0192f1d0-...", "status": "active", "created_at": "2026-11-05T02:14:00Z" }
```

### `GET /conversations?status=escalated&limit=20`

```json
{ "items": [
    { "id": "0192f1d0-...", "title": "StaffID locked out", "status": "escalated",
      "primary_intent": "account_access", "user": { "id": "...", "full_name": "Mika Reyes", "role": "staff" },
      "last_message_at": "2026-11-05T02:20:11Z" }
  ], "next_cursor": null }
```

### `GET /conversations/{id}`

```json
{
  "id": "0192f1d0-...", "status": "active", "assigned_agent": null,
  "messages": [
    { "id": "m1", "sender_type": "user", "content": "Staff Wi-Fi keeps asking for my password on my phone",
      "created_at": "2026-11-05T02:14:03Z" },
    { "id": "m2", "sender_type": "assistant",
      "content": "This usually happens right after a StaffID password change [1]. Forget the `PickleHub-Staff` network on your phone, then reconnect… [1]",
      "citations": [ { "n": 1, "doc_id": "KB-011", "title": "Staff Wi-Fi (PickleHub-Staff) Troubleshooting",
                       "section": "Wi-Fi keeps asking for my password", "chunk_id": "KB-011-c03" } ],
      "confidence": 0.82, "answer_mode": "generated", "feedback": 0,
      "created_at": "2026-11-05T02:14:06Z" }
  ],
  "tool_calls": [],
  "tickets": []
}
```

`content` is always the **redacted** text (e.g. `My number is [PH_MOBILE]`).

### `POST /conversations/{id}/messages` (non-streaming)

```json
// request
{ "content": "Is DinkPOS down at Bacoor? The card terminal keeps failing." , "client_message_id": "c-7f3a" }
// 200
{
  "user_message": { "id": "m3", "content": "Is DinkPOS down at Bacoor? The card terminal keeps failing.", "pii_detected": false },
  "assistant_message": {
    "id": "m4",
    "content": "DinkPOS is **operational**, but Card Payments at Bacoor show **Partial Outage** since 9:40 AM, so IT already knows — no need for a new ticket. The incident note says to take cash meanwhile. If one terminal shows a connection error, check… [1]",
    "intent": "pos_payments",
    "confidence": 0.79,
    "answer_mode": "generated",
    "citations": [ { "n": 1, "doc_id": "KB-016", "title": "TapPay Card Terminal Errors and Declined Payments", "section": "Terminal cannot connect", "chunk_id": "KB-016-c02" } ],
    "latency_ms": 2140
  },
  "tool_calls": [
    { "id": "t1", "tool_name": "check_service_status", "status": "succeeded",
      "result": { "services": [ { "service_key": "dinkpos", "status": "operational" },
                                { "service_key": "card_payments", "status": "partial_outage", "club_code": "BAC", "since": "2026-11-05T01:40:00Z" } ] } }
  ],
  "conversation_status": "active",
  "suggested_actions": ["create_ticket", "escalate_to_agent"]
}
```

`client_message_id` is optional; repeating the same id within 10 minutes returns the original response instead of running the turn twice.

### `POST /conversations/{id}/messages/stream` (SSE)

Same request body. Response `Content-Type: text/event-stream`. The browser reads it with `fetch()` + `ReadableStream` (not `EventSource`, which cannot POST or send headers). Events, in order:

| Event | Data | When |
|---|---|---|
| `meta` | `{"user_message_id":"m5","assistant_message_id":"m6","intent":"how_to","pii_redacted":["EMAIL"]}` | first |
| `guardrail` | `{"type":"prompt_injection","action":"blocked","message":"I can't help with that request."}` | input blocked — stream then ends with `done` |
| `token` | `{"delta":"Front-desk tablets join "}` | repeated |
| `citations` | `{"citations":[{ "n":1, "doc_id":"KB-011", ... }]}` | after the last token |
| `tool_call` | `{"id":"t2","tool_name":"create_ticket","status":"awaiting_confirmation","arguments":{...},"confirm_text":"Create a P3 ticket for CourtBook Admin double-booking at Imus?"}` | model proposed an action |
| `tool_result` | `{"id":"t1","tool_name":"check_service_status","status":"succeeded","result":{...},"message":"..."}` | a no-confirmation tool ran |
| `escalation` | `{"escalation_id":"e1","ticket_number":"DD-000124","reason":"low_confidence","message":"I've passed this to the IT Service Desk…"}` | escalated |
| `done` | `{"confidence":0.82,"answer_mode":"generated","latency_ms":2310,"conversation_status":"active"}` | always last on success |
| `error` | `{"code":"LLM_UNAVAILABLE","message":"…","request_id":"…"}` | unrecoverable error (degraded mode already failed) |

Example wire format:

```
event: token
data: {"delta":"Front-desk tablets join "}

event: done
data: {"confidence":0.82,"answer_mode":"generated","latency_ms":2310,"conversation_status":"active"}
```

While a conversation is `escalated` and claimed by an agent, user messages are stored and pushed to the agent; the AI does not answer (the stream sends `meta` then `done` with `answer_mode":"agent_handling"`).

### `POST /tool-calls/{id}/confirm`

```json
// request (arguments optional — the user may edit fields the confirmation card exposes)
{ "arguments": { "club_code": "IMS" } }
// 200
{ "id": "t2", "tool_name": "create_ticket", "status": "succeeded",
  "result": { "ticket_number": "DD-000125", "jira_key": null, "jira_sync_status": "pending" },
  "message": "Ticket DD-000125 created (P3, CourtBook, Imus). The IT team will reply by email; you can track it under My tickets." }
```

For `reset_password` the confirm response is `{"status":"awaiting_verification","message":"I sent a 6-digit code to the mobile number on file ending in ••27."}`.

Errors: `409 INVALID_STATE` if the call is not `awaiting_confirmation`; `404` if not the caller's.

### `POST /tool-calls/{id}/verify`

```json
// request — the OTP goes to this endpoint, never through the chat message / LLM
{ "otp": "482913" }
// 200 (normal staff account)
{ "id": "t3", "tool_name": "reset_password", "status": "succeeded",
  "message": "Done. A temporary password was sent to your HubMail recovery address. It works for 24 hours and you'll be asked to change it at first sign-in." }
// 200 (privileged account)
{ "id": "t3", "status": "awaiting_approval",
  "message": "Because your account has admin rights, the IT Lead must approve this reset. You'll get an email when it's done." }
// 400
{ "error": { "code": "OTP_INVALID", "message": "That code didn't match. 2 attempts left." } }
```

### `POST /conversations/{id}/resolve`, `POST /messages/{id}/feedback`

```json
// resolve — request {} → 200
{ "id": "0192f1d0-...", "status": "resolved_ai" }
// feedback — request
{ "value": -1, "comment": "Steps didn't match what I see" }
// 204
```

Two thumbs-down in a row in one conversation triggers an offer to escalate (`reason = negative_feedback`).

## 5. Tickets

### `GET /tickets?status=open&priority=P1&club=BAC`

```json
{ "items": [
  { "id": "...", "ticket_number": "DD-000125", "jira_key": "ITH-58", "summary": "CourtBook Admin shows double bookings for Court 3",
    "category": "member_app_booking", "affected_system": "courtbook", "priority": "P3", "status": "open",
    "club_code": "IMS", "requester": { "id": "...", "full_name": "Mika Reyes" }, "assignee": null,
    "source": "ai_tool", "created_at": "2026-11-05T02:31:00Z" }
], "next_cursor": null }
```

### `POST /tickets`

```json
// request
{ "summary": "Need RallyBracket access for the Nov 22 tournament", "description": "…",
  "category": "access_request", "affected_system": "rallybracket", "priority": "P3", "club_code": "DAS" }
// 201 → ticket object as above (source = "manual")
```

Members may only use categories `member_app_booking`, `network` (member Wi-Fi) and `other`; priority from members is capped at P3.

### `PATCH /tickets/{id}`

```json
{ "status": "resolved", "priority": "P2", "assignee_id": "…", "note": "Cleared cached session on tablet" }
```

Status changes are pushed to n8n (`ticket.updated`) so Jira stays in sync.

## 6. Escalations, takeover, approvals

### `GET /escalations?status=queued`

```json
{ "items": [
  { "id": "e1", "conversation_id": "…", "ticket_number": "DD-000124", "reason": "low_confidence", "urgency": "normal",
    "handoff_summary": "Staff (Imus front desk) cannot open CourtBook Admin after the 4 Nov update; tried KB-006 "CourtBook is slow or not loading" steps; error 'session expired' loops. No outage listed.",
    "user": { "full_name": "Mika Reyes", "role": "staff", "club_code": "IMS" },
    "status": "queued", "created_at": "2026-11-05T02:40:00Z", "waiting_s": 312 }
] , "next_cursor": null }
```

### `POST /escalations/{id}/claim` → `200 {"id":"e1","status":"assigned","assigned_agent_id":"…"}`

`409` if another agent already claimed it.

### `POST /conversations/{id}/agent-messages`

```json
{ "content": "Hi Mika, Kat from IT here. Can you try signing out of all CourtBook tabs…" }
// 201 → message object (sender_type = "agent")
```

### `POST /escalations/{id}/resolve`

```json
{ "resolution": "resolved", "note": "Cleared SSO cookie", "close_ticket": true, "return_to_ai": false }
```

### `GET /approvals`, `POST /approvals/{tool_call_id}/decision`

```json
// GET → 
{ "items": [ { "tool_call_id": "t9", "tool_name": "reset_password", "requested_by": { "full_name": "Lea Bautista", "role": "admin" },
               "target_system": "staffid", "verified_otp": true, "requested_at": "…", "expires_at": "…" } ] }
// POST request
{ "decision": "approve", "note": "Confirmed by phone" }
// 200
{ "tool_call_id": "t9", "status": "succeeded" }
```

An admin cannot approve their own request (`403 FORBIDDEN`, code `SELF_APPROVAL`).

## 7. Service status

### `GET /services/status`

```json
{ "items": [
  { "service_key": "dinkpos", "display_name": "DinkPOS", "status": "operational", "club_code": null, "message": null, "updated_at": "…" },
  { "service_key": "card_payments", "display_name": "Card Payments (TapPay)", "status": "partial_outage", "club_code": "BAC",
    "message": "Bank-side authorisation delays. Workaround: take cash. Next update 11:00 AM.", "updated_at": "…" },
  { "service_key": "staff_wifi", "display_name": "Staff Wi-Fi", "status": "operational", "club_code": "IMS", "message": null, "updated_at": "…" }
] }
```

Service keys and status values follow the status-page guide (KB-025). Keys: `courtbook, member_app, dinkpos, card_payments, hubmail, staff_wifi, member_wifi, hubconnect_vpn, hubwatch, rallybracket, dinkdesk` (Wi-Fi rows exist per branch). Statuses: `operational, degraded_performance, partial_outage, major_outage, maintenance`.

### `PUT /services/{service_key}/status`

```json
{ "status": "major_outage", "club_code": "BAC", "message": "Fibre cut — ISP ETA 3 PM. Workaround: DinkPOS offline mode (KB-015)." }
```

## 8. Knowledge base admin

### `GET /kb/documents`

```json
{ "items": [ { "id": "KB-001", "title": "How to Reset Your StaffID Password", "category": "accounts-access",
               "audience_roles": ["staff","agent","admin"], "version": 2, "status": "active", "chunk_count": 7,
               "last_updated": "2026-09-15", "indexed_at": "…" } ],
  "kb_version": 14 }
```

### `POST /kb/documents` (multipart)

Form field `file` = one `.md` file with the standard frontmatter (`id`, `title`, `category`, `audience_roles`, `last_updated`, `owner`). Max 200 KB. Rejected with `422` if frontmatter is missing/invalid or the body contains HTML `<script>`/iframe. Response `202 {"job_id":"…","doc_id":"KB-031"}`.

### `POST /kb/reindex`

```json
// request
{ "mode": "changed" }        // or "full" (needed after changing GEMINI_EMBEDDING_MODEL or EMBEDDING_DIM)
// 202
{ "job_id": "rj-0192…", "status": "queued" }
```

`GET /kb/reindex/{job_id}` → `{"status":"running","docs_total":30,"docs_done":12,"chunks_embedded":96,"paused_reason":null}`; `paused_reason` is `"embedding_quota"` if the embedding quota was hit (job resumes automatically).

### `POST /kb/search`

```json
// request
{ "query": "wifi keeps asking for password after I changed it", "as_role": "staff", "k": 5 }
// 200
{ "confidence": 0.81, "results": [
  { "chunk_id": "KB-011-c03", "doc_id": "KB-011", "section": "Wi-Fi keeps asking for my password",
    "vector_score": 0.83, "bm25_score": 7.1, "rrf_score": 0.0325, "is_current": true, "preview": "Your phone is still using the old password…" } ] }
```

Used by the agent dashboard ("agent copilot" search) and for demonstrating hybrid retrieval during the defense.

## 9. Metrics, evaluation, audit

### `GET /metrics/summary?from=2026-11-01&to=2026-11-15`

```json
{
  "period": { "from": "2026-11-01", "to": "2026-11-15" },
  "conversations": 214,
  "deflection_rate": 0.63,
  "escalation_rate": 0.14,
  "automation_success_rate": 0.95,
  "tool_calls": { "reset_password": 18, "create_ticket": 41, "check_service_status": 33, "escalate_to_agent": 30 },
  "latency_ms": { "p50": 1850, "p95": 4200 },
  "cache_hit_rate": 0.31,
  "mttr_hours": 5.2,
  "csat": 0.84,
  "guardrail_blocks": { "prompt_injection": 12, "pii_redacted": 27, "rbac_denied": 4 },
  "llm": { "calls_today": { "gemini-2.5-flash": 96, "gemini-2.5-flash-lite": 12 }, "breaker": "closed" },
  "latest_eval": { "run_id": "…", "label": "prompt-v3", "faithfulness": 0.91, "answer_relevance": 0.88, "context_precision": 0.84 }
}
```

Agents get the same shape without `llm` and `guardrail_blocks`.

### `GET /metrics/timeseries?metric=deflection_rate&interval=day&from=…&to=…`

```json
{ "metric": "deflection_rate", "interval": "day", "points": [ { "t": "2026-11-01", "v": 0.58 }, { "t": "2026-11-02", "v": 0.61 } ] }
```

### `GET /guardrail-events?since=2026-11-16T05:00:00Z`

```json
{ "items": [ { "id": "…", "created_at": "…", "stage": "input", "type": "prompt_injection", "action": "blocked",
               "detector": "heuristic", "score": 0.92, "rule_ids": ["INJ-IGNORE-PREV", "INJ-ROLEPLAY"],
               "user": { "full_name": "Demo Panelist", "role": "member" } } ] }
```

### `POST /eval/runs`

```json
{ "label": "prompt-v3-hybrid", "dataset_version": "golden-v1", "prompt_version": "v3", "model_name": "gemini-2.5-flash",
  "git_sha": "a1b2c3d", "metrics": { "faithfulness": 0.91, "answer_relevance": 0.88, "context_precision": 0.84,
  "behavior_accuracy": 0.86, "refusal_accuracy": 1.0, "p50_ms": 1900, "p95_ms": 4300 },
  "results": [ { "question_id": "GS-017", "user_role": "member", "category": "malicious_prompt_injection",
                 "expected_behavior": "refuse", "actual_behavior": "refuse", "predicted_intent": "abuse",
                 "expected_source_ids": [], "retrieved_doc_ids": [], "passed": true, "latency_ms": 120, "scores": {} } ] }
// 201 → { "id": "…" }
```

### `GET /audit-logs?actor_id=&action=tool.reset_password.executed&from=&to=`

Returns audit rows (see [database.md §6](database.md#6-governance-evaluation-and-plumbing)).

## 10. Webhooks and internal endpoints (n8n)

All require the HMAC headers from §1.2. Each payload carries `event_id`; a repeated `event_id` returns `200 {"duplicate": true}` and changes nothing.

### `POST /webhooks/n8n/ticket-synced`

```json
{ "event_id": "n8n-exec-4412", "ticket_id": "…", "jira_key": "ITH-58", "jira_url": "https://picklehub-demo.atlassian.net/browse/ITH-58" }
```

### `POST /webhooks/n8n/ticket-updated`

```json
{ "event_id": "n8n-exec-4519", "jira_key": "ITH-58", "status": "Done", "resolution": "Fixed", "updated_at": "2026-11-05T07:10:00Z" }
```

Jira statuses are mapped: `To Do → open`, `In Progress → in_progress`, `Waiting for customer → waiting_on_user`, `Done → resolved`.

### `POST /webhooks/n8n/delivery-failed`

```json
{ "event_id": "n8n-exec-4600", "workflow": "WF-01 ticket-to-jira", "correlation_id": "<ticket id>", "error": "Jira 401 Unauthorized" }
```

### `GET /internal/escalations/{id}` · `GET /internal/tool-calls/{id}`

```json
{ "id": "e1", "status": "queued", "created_at": "…", "waiting_s": 640 }
```

Minimal fields only — no message content.

### Outbound events (backend → n8n)

Sent by the outbox worker to `${N8N_WEBHOOK_BASE_URL}/<path>` (e.g. `http://n8n:5678/webhook/dinkdesk/ticket-created`); full payloads in [automation.md](automation.md).

| Event | n8n webhook path | Workflow |
|---|---|---|
| `ticket.created` | `/webhook/dinkdesk/ticket-created` | WF-01 |
| `ticket.updated` | `/webhook/dinkdesk/ticket-updated` | WF-01b |
| `escalation.created` | `/webhook/dinkdesk/escalation-created` | WF-02 |
| `password_reset.approval_requested` | `/webhook/dinkdesk/reset-approval` | WF-03 |
| `password_reset.completed` | `/webhook/dinkdesk/reset-completed` | WF-03b |

## 11. Health

`GET /health` → `200 {"status":"ok"}`. The skeleton (workstream A) currently serves this at the root path `/health` for the Docker HEALTHCHECK and CI; `/api/v1/health` is added as an alias when the v1 router lands.

`GET /health/ready` →

```json
{ "status": "degraded",
  "checks": { "postgres": "ok", "chroma": "ok", "directory": "ok", "n8n": "unreachable", "llm_breaker": "closed", "llm_quota_used_pct": 47 } }
```

`status` is `ok`, `degraded` (non-critical dependency down) or `down` (Postgres down → HTTP 503).
