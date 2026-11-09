// The built-in mock API. Served by src/app/mock-api/api/v1/[...path]/route.ts at
// /mock-api/api/v1/*, mirroring the real backend paths in docs/api.md. State lives in memory
// on the dev server, so two browser windows (member + agent) see each other's changes.
import { KB_ROWS } from "./kb";
import {
  MOCK_USERS,
  PERMISSIONS,
  cite,
  metricsSummary,
  seedEscalations,
  seedGuardrailEvents,
  seedServices,
  seedTickets,
  type MockUser,
} from "./data";
import type {
  AskResponse,
  Citation,
  ConversationDetail,
  ConversationMessage,
  EscalateRequest,
  EscalateResponse,
  Escalation,
  GuardrailEvent,
  KbDocument,
  ReindexJob,
  Role,
  ServiceStatus,
  Ticket,
  ToolCall,
  User,
} from "@/lib/types";

type State = {
  services: ServiceStatus[];
  tickets: Ticket[];
  escalations: Escalation[];
  conversations: Map<string, ConversationDetail>;
  toolCalls: Map<string, ToolCall & { attempts: number; ownerId: string }>;
  guardrails: GuardrailEvent[];
  kb: KbDocument[];
  jobs: Map<string, { startedAt: number; total: number }>;
  seq: number;
};

function createState(): State {
  const seeds = seedEscalations();
  const kb: KbDocument[] = KB_ROWS.map((row) => ({
    ...row,
    version: 1,
    status: row.id === "KB-026" ? "changed" : row.status,
    indexed_at: "2026-11-15T01:02:00Z",
  }));
  return {
    services: seedServices(),
    tickets: seedTickets(),
    escalations: seeds.map((s) => s.escalation),
    conversations: new Map(seeds.map((s) => [s.conversation.id, s.conversation])),
    toolCalls: new Map(),
    guardrails: seedGuardrailEvents(),
    kb,
    jobs: new Map(),
    seq: 125,
  };
}

const store = globalThis as unknown as { __dinkdeskMock?: State };
function state(): State {
  store.__dinkdeskMock ??= createState();
  return store.__dinkdeskMock;
}

// ---------- helpers ----------

function json(body: unknown, status = 200) {
  return Response.json(body, { status });
}

function error(status: number, code: string, message: string, details?: unknown) {
  return json({ error: { code, message, request_id: `mock-${Date.now()}`, details } }, status);
}

const publicUser = ({ password: _password, ...user }: MockUser): User => user;

/** Accepts mock tokens ("mock.<userId>") and, when a live backend falls back here, its JWTs. */
function currentUser(req: Request): MockUser | null {
  const header = req.headers.get("authorization") ?? "";
  const token = header.replace(/^Bearer\s+/i, "");
  if (!token) return null;
  if (token.startsWith("mock.")) return MOCK_USERS.find((u) => u.id === token.slice(5)) ?? null;
  try {
    const payload = JSON.parse(Buffer.from(token.split(".")[1], "base64url").toString("utf8"));
    const role = (payload.role ?? "staff") as Role;
    const byRole: Record<Role, string> = { member: "u-carla", staff: "u-lea", agent: "u-kat", admin: "u-ramon" };
    return MOCK_USERS.find((u) => u.id === byRole[role]) ?? null;
  } catch {
    return null;
  }
}

const SEEDED_TICKETS = new Set(seedTickets().map((t) => t.id));
const isStaffSide =(u: MockUser) => u.role === "agent" || u.role === "admin";
const firstName = (u: MockUser) => u.full_name.split(" ")[0];
const nextId = (prefix: string) => `${prefix}-${++state().seq}`;
const now = () => new Date().toISOString();

async function readJson<T>(req: Request): Promise<T> {
  try {
    return (await req.json()) as T;
  } catch {
    return {} as T;
  }
}

// ---------- chat scenarios ----------

type ReplyOptions = Partial<Omit<AskResponse, "assistant_message">> & {
  citations?: Citation[];
  confidence?: number;
  action?: "answer" | "clarify" | "escalate";
  answer_mode?: "generated" | "template";
};

function reply(content: string, extra: ReplyOptions = {}): AskResponse {
  const { citations = [], confidence = 0.82, action = "answer", answer_mode = "generated", ...rest } = extra;
  return {
    user_message: { content: "", pii_detected: false },
    assistant_message: {
      id: nextId("m"),
      content,
      intent: null,
      confidence,
      answer_mode,
      action,
      citations,
      latency_ms: 1400 + Math.round(Math.random() * 900),
    },
    tool_calls: [],
    conversation_status: "active",
    suggested_actions: [],
    ...rest,
  };
}

function answerFor(text: string, user: MockUser): AskResponse {
  const t = text.toLowerCase();
  const staffSide = user.role !== "member";

  if (/ignore (all |your )?(previous|prior)|developer mode|system prompt|jailbreak/.test(t)) {
    state().guardrails.unshift({
      id: nextId("g"), created_at: now(), stage: "input", type: "prompt_injection", action: "blocked", detector: "heuristic",
      score: 0.93, rule_ids: ["INJ-IGNORE-PREV"], user: { full_name: user.full_name, role: user.role }, excerpt: text.slice(0, 120),
    });
    return reply("I can't help with that request. I can help with PickleHub IT questions like passwords, Wi-Fi, DinkPOS or the Member App.", {
      answer_mode: "template", action: "answer", confidence: 1,
    });
  }

  if (staffSide && /reset/.test(t) && /(for me|please|emp-|do it)/.test(t)) {
    const id = nextId("tc");
    const call: ToolCall = {
      id, tool_name: "reset_password", status: "awaiting_confirmation",
      arguments: {
        account: `${user.email.split("@")[0]}${user.id === "u-lea" ? " (EMP-0412)" : ""}`,
        code_goes_to: "Mobile ending in ••47",
        signs_out_of: "HubMail, CourtBook Admin, Staff Wi-Fi, HubConnect VPN",
      },
      confirm_text: "Reset your StaffID password?",
    };
    state().toolCalls.set(id, { ...call, attempts: 0, ownerId: user.id });
    return { ...reply(""), assistant_message: null, tool_calls: [call] };
  }

  if (staffSide && /(code never|didn't arrive|never arrived|no code)/.test(t)) {
    return reply(
      "Sorry – the SMS gateway is delayed this morning (see Service status), so the code may not come in time. I can pass this to the IT Service Desk so someone verifies you by phone and resets it from their side.",
      { citations: [cite(1, "KB-024", "")], confidence: 0.45, action: "escalate", suggested_actions: ["escalate_to_agent"] },
    );
  }

  if (staffSide && /(password|forgot|staffid|locked out|lockout)/.test(t)) {
    return reply(
      "Sorry about that! You have two options:\n1. Try the self-service portal again at id.picklehub.example/reset – it needs your MFA app or a code to your mobile.\n2. I can reset it for you here after a quick identity check. [1]\nIf the portal says your account is locked, wait 15 minutes – it clears by itself. [2]",
      { citations: [cite(1, "KB-001", "Option 2"), cite(2, "KB-003", "")], confidence: 0.86, suggested_actions: ["reset_password"] },
    );
  }

  if (/dinkpos/.test(t) && /pin/.test(t)) {
    return reply(
      "Your DinkPOS cashier PIN can be reset by the branch manager on duty from **Back office › Staff › Reset PIN**. If no manager is on shift, I can open a ticket for the IT Service Desk. [1]",
      { citations: [cite(1, "KB-007", "Forgotten cashier PIN")], confidence: 0.84, suggested_actions: ["create_ticket"] },
    );
  }

  if (/(wi-?fi|wifi)/.test(t)) {
    if (!staffSide) {
      return reply(
        "Members and guests use **PickleHub-Members**. The password is on the card at the front desk and changes every Monday. If you're connected but nothing loads, open any web page to accept the terms. [1]",
        { citations: [cite(1, "KB-012", "Connecting")], confidence: 0.83 },
      );
    }
    return reply(
      "Staff Wi-Fi drops usually come from an old saved password after a StaffID change. Forget **PickleHub-Staff** on your device, reconnect, and sign in with your StaffID. If it still drops every few minutes, tell me which branch and I'll check for an incident. [1]",
      { citations: [cite(1, "KB-011", "Wi-Fi keeps asking for my password")], confidence: 0.82 },
    );
  }

  if (/(card terminal|host not reachable|tappay|card payment)/.test(t)) {
    const res = reply(
      "Card Payments show **Partial Outage** at Bacoor since 9:40 AM, so IT already knows – no need for a new ticket. Take cash meanwhile. If only one terminal shows “Host not reachable”, restart it and check its network cable. [1]",
      { citations: [cite(1, "KB-016", "Terminal cannot connect")], confidence: 0.79 },
    );
    res.tool_calls = [{ id: nextId("tc"), tool_name: "check_service_status", status: "succeeded", message: "Checked the status page." }];
    return res;
  }

  if (/double[- ]?book|twice|court \d/.test(t)) {
    return reply(
      "Double bookings usually come from the Member App and CourtBook syncing late. Pull down to refresh your bookings; if it still shows twice after 5 minutes, I can report it so the front desk cancels the duplicate. You won't be charged twice. [1]",
      { citations: [cite(1, "KB-020", "Duplicate bookings")], confidence: 0.77, suggested_actions: ["create_ticket"] },
    );
  }

  if (/(member app|log ?in|sign ?in)/.test(t)) {
    return reply(
      "For Member App sign-in problems, use **Forgot password** on the app's sign-in screen; the link goes to your Member App email. If the app says your account is locked, wait 15 minutes. [1]",
      { citations: [cite(1, "KB-018", "Can't sign in")], confidence: 0.8 },
    );
  }

  if (/(talk to|speak to|real person|human|agent)/.test(t)) {
    return reply("Sure – I can pass this chat to the IT Service Desk so a person picks it up.", {
      action: "escalate", confidence: 0.9, suggested_actions: ["escalate_to_agent"],
    });
  }

  return reply(
    `I'm not sure I have a guide for that, ${firstName(user)}. Could you tell me which system it's about (StaffID, CourtBook, DinkPOS, Wi-Fi or the Member App)? Or I can pass this to the IT Service Desk.`,
    { action: "clarify", confidence: 0.38, suggested_actions: ["escalate_to_agent"], escalation_required: false },
  );
}

// ---------- router ----------

type Handler = (req: Request, params: string[], user: MockUser | null, url: URL) => Promise<Response> | Response;

const routes: { method: string; pattern: RegExp; auth: boolean; handler: Handler }[] = [];
function route(method: string, path: string, handler: Handler, auth = true) {
  const pattern = new RegExp(`^${path.replace(/:[a-z_]+/g, "([^/]+)")}$`);
  routes.push({ method, pattern, auth, handler });
}

// Auth
route("POST", "/auth/login", async (req) => {
  const body = await readJson<{ email?: string; password?: string }>(req);
  const email = (body.email ?? "").trim().toLowerCase();
  const user = MOCK_USERS.find((u) => u.email === email);
  if (!user || user.password !== body.password) {
    return error(401, "UNAUTHENTICATED", "Email or password is incorrect");
  }
  return json({ access_token: `mock.${user.id}`, token_type: "bearer", expires_in: 3600, user: publicUser(user) });
}, false);

route("POST", "/auth/logout", () => new Response(null, { status: 204 }));

route("GET", "/auth/me", (_req, _p, user) => json({ user: publicUser(user!), permissions: PERMISSIONS[user!.role] }));

// Chat
route("POST", "/rag/ask", async (req, _p, user) => {
  const body = await readJson<{ content?: string }>(req);
  const content = (body.content ?? "").trim();
  if (!content) return error(422, "VALIDATION_ERROR", "Message can't be empty.");
  if (content.length > 2000) return error(400, "INPUT_TOO_LONG", "Messages can be up to 2,000 characters.");
  await new Promise((r) => setTimeout(r, 900 + Math.random() * 700)); // feels like a real model
  const res = answerFor(content, user!);
  res.user_message = { content, pii_detected: false };
  return json(res);
});

route("POST", "/conversations/:id/messages", async (req, [id], user) => {
  const body = await readJson<{ content?: string }>(req);
  const content = (body.content ?? "").trim();
  const convo = state().conversations.get(id);
  const userMessage: ConversationMessage = { id: nextId("m"), sender_type: "user", content, created_at: now() };
  if (convo && convo.status === "escalated") {
    convo.messages.push(userMessage);
    const res: AskResponse = {
      user_message: { id: userMessage.id, content, pii_detected: false },
      assistant_message: null,
      tool_calls: [],
      conversation_status: "escalated",
      suggested_actions: [],
    };
    return json(res);
  }
  const res = answerFor(content, user!);
  res.user_message = { id: userMessage.id, content, pii_detected: false };
  return json(res);
});

route("GET", "/conversations/:id", (_req, [id], user) => {
  const convo = state().conversations.get(id);
  if (!convo) return error(404, "NOT_FOUND", "Conversation not found.");
  if (!isStaffSide(user!) && !state().escalations.some((e) => e.conversation_id === id)) {
    return error(404, "NOT_FOUND", "Conversation not found.");
  }
  return json(convo);
});

route("POST", "/tool-calls/:id/confirm", (_req, [id], user) => {
  const call = state().toolCalls.get(id);
  if (!call || call.ownerId !== user!.id) return error(404, "NOT_FOUND", "Action not found.");
  if (call.status !== "awaiting_confirmation") return error(409, "INVALID_STATE", "This action already ran.");
  if (call.tool_name === "reset_password") {
    call.status = "awaiting_verification";
    call.message = "I sent a 6-digit code to the mobile number on file ending in ••47. Type it below – never in the chat.";
  } else {
    call.status = "succeeded";
    const ticket = `DD-000${++state().seq}`;
    call.result = { ticket_number: ticket, jira_key: null, jira_sync_status: "pending" };
    call.message = `Ticket ${ticket} created. The IT team will reply by email; you can track it under My tickets.`;
  }
  const { attempts: _a, ownerId: _o, ...out } = call;
  return json(out);
});

route("POST", "/tool-calls/:id/cancel", (_req, [id], user) => {
  const call = state().toolCalls.get(id);
  if (!call || call.ownerId !== user!.id) return error(404, "NOT_FOUND", "Action not found.");
  call.status = "cancelled";
  call.message = "Okay, I didn't change anything.";
  const { attempts: _a, ownerId: _o, ...out } = call;
  return json(out);
});

route("POST", "/tool-calls/:id/verify", async (req, [id], user) => {
  const call = state().toolCalls.get(id);
  if (!call || call.ownerId !== user!.id) return error(404, "NOT_FOUND", "Action not found.");
  if (call.status !== "awaiting_verification") return error(409, "INVALID_STATE", "No code is pending for this action.");
  const { otp } = await readJson<{ otp?: string }>(req);
  call.attempts += 1;
  // Demo rule: any 6 digits work except 000000, which simulates a wrong code.
  if (!/^\d{6}$/.test(otp ?? "") || otp === "000000") {
    const left = 3 - call.attempts;
    if (left <= 0) {
      call.status = "failed";
      call.message = "That code didn't match 3 times, so I stopped the reset. I can pass this to the IT Service Desk.";
      const { attempts: _a, ownerId: _o, ...out } = call;
      return json(out);
    }
    return error(400, "OTP_INVALID", `That code didn't match. ${left} attempt${left === 1 ? "" : "s"} left.`);
  }
  call.status = "succeeded";
  call.message =
    "Done. A temporary password was sent to your HubMail recovery address. It works for 24 hours and you'll be asked to change it at first sign-in.";
  const { attempts: _a, ownerId: _o, ...out } = call;
  return json(out);
});

route("POST", "/messages/:id/feedback", () => new Response(null, { status: 204 }));

// Escalation started by the user ("Talk to a person"). UI extension, see types.ts.
route("POST", "/escalations", async (req, _p, user) => {
  const body = await readJson<EscalateRequest & { title?: string; transcript?: { role: string; content: string }[] }>(req);
  const s = state();
  const n = ++s.seq;
  const ticketNumber = `DD-000${n}`;
  const jiraKey = `ITH-${1078 + n}`;
  const convoId = body.conversation_id || nextId("c");
  const title = body.title || "Chat passed to the IT Service Desk";
  const messages: ConversationMessage[] = (body.transcript ?? []).map((m, i) => ({
    id: `${convoId}-m${i}`,
    sender_type: m.role === "user" ? "user" : "assistant",
    content: m.content,
    created_at: now(),
  }));
  s.conversations.set(convoId, {
    id: convoId, status: "escalated", assigned_agent: null, messages, tool_calls: [],
    tickets: [{ ticket_number: ticketNumber, jira_key: jiraKey }],
  });
  s.escalations.unshift({
    id: `e-${n}`, conversation_id: convoId, ticket_number: ticketNumber, jira_key: jiraKey,
    reason: body.reason ?? "user_request", urgency: "normal", priority: "P2", title,
    flag: body.reason === "low_confidence" ? "Low confidence answer" : "User asked for a person",
    category_label: "Accounts & access", confidence: null, sla_due_at: new Date(Date.now() + 3600_000).toISOString(),
    handoff_summary: body.summary ?? title, summary_points: [body.summary ?? title], suggested_next_step: null, citations: [],
    user: { full_name: user!.full_name, role: user!.role, club_code: user!.club_code ?? null, job_title: user!.job_title },
    status: "queued", created_at: now(), waiting_s: 0, assigned_agent: null,
  });
  s.tickets.unshift({
    id: `t-${n}`, ticket_number: ticketNumber, jira_key: jiraKey, summary: title, category: "accounts_access",
    priority: "P2", status: "escalated", club_code: user!.club_code ?? null,
    requester: { id: user!.id, full_name: user!.full_name }, assignee: null, source: "escalation", created_at: now(),
  });
  const res: EscalateResponse = {
    escalation_id: `e-${n}`,
    ticket_number: ticketNumber,
    jira_key: jiraKey,
    priority: "P2",
    first_reply_minutes: 60,
    message: `I've passed this to the IT Service Desk and created ticket ${ticketNumber} with this chat attached, so you won't need to repeat yourself. Priority P2 – first reply within 1 hour.`,
    // Prototype scope: no live agent takeover. The chat shows the escalation notice and the
    // agent works the ticket outside the chat.
    agent: null,
    agent_greeting: null,
  };
  return json(res, 201);
});

route("GET", "/escalations", (_req, _p, user, url) => {
  if (!isStaffSide(user!)) return error(403, "FORBIDDEN", "Only the IT team can see the escalation queue.");
  const status = url.searchParams.get("status");
  const order = { P1: 1, P2: 2, P3: 3, P4: 4 };
  const items = state()
    .escalations.filter((e) => !status || status === "all" || e.status === status || (status === "open" && e.status !== "resolved"))
    .map((e) => ({ ...e, waiting_s: Math.round((Date.now() - Date.parse(e.created_at)) / 1000) }))
    .sort((a, b) => order[a.priority ?? "P4"] - order[b.priority ?? "P4"] || b.waiting_s - a.waiting_s);
  return json({ items, next_cursor: null });
});

route("POST", "/escalations/:id/claim", (_req, [id], user) => {
  if (!isStaffSide(user!)) return error(403, "FORBIDDEN", "Only the IT team can take over chats.");
  const esc = state().escalations.find((e) => e.id === id);
  if (!esc) return error(404, "NOT_FOUND", "Escalation not found.");
  if (esc.assigned_agent && esc.assigned_agent.id !== user!.id) {
    return error(409, "CONFLICT", `${esc.assigned_agent.full_name} already took this chat.`);
  }
  esc.status = "assigned";
  esc.assigned_agent = { id: user!.id, full_name: user!.full_name };
  const convo = state().conversations.get(esc.conversation_id);
  if (convo) convo.assigned_agent = esc.assigned_agent;
  return json({ id, status: "assigned", assigned_agent_id: user!.id });
});

route("POST", "/escalations/:id/resolve", async (req, [id], user) => {
  if (!isStaffSide(user!)) return error(403, "FORBIDDEN", "Only the IT team can resolve escalations.");
  const esc = state().escalations.find((e) => e.id === id);
  if (!esc) return error(404, "NOT_FOUND", "Escalation not found.");
  const body = await readJson<{ close_ticket?: boolean; return_to_ai?: boolean }>(req);
  esc.status = "resolved";
  const convo = state().conversations.get(esc.conversation_id);
  if (convo) {
    convo.status = body.return_to_ai ? "active" : "resolved_agent";
    convo.messages.push({
      id: nextId("m"), sender_type: "system",
      content: body.return_to_ai ? "The IT Service Desk handed this chat back to DinkDesk." : `${user!.full_name} marked this as resolved.`,
      created_at: now(),
    });
  }
  const ticket = state().tickets.find((t) => t.ticket_number === esc.ticket_number);
  if (ticket && body.close_ticket) ticket.status = "resolved";
  return json({ id, status: "resolved" });
});

route("POST", "/conversations/:id/agent-messages", async (req, [id], user) => {
  if (!isStaffSide(user!)) return error(403, "FORBIDDEN", "Only the IT team can reply as an agent.");
  const convo = state().conversations.get(id);
  if (!convo) return error(404, "NOT_FOUND", "Conversation not found.");
  const { content } = await readJson<{ content?: string }>(req);
  const msg: ConversationMessage = {
    id: nextId("m"), sender_type: "agent", sender_name: user!.full_name, content: (content ?? "").trim(), created_at: now(),
  };
  convo.messages.push(msg);
  return json(msg, 201);
});

// Tickets, service status
route("GET", "/tickets", (_req, _p, user) => {
  // Seeded tickets are shown to every member/staff demo account so "My tickets" is never empty.
  const items = isStaffSide(user!)
    ? state().tickets
    : state().tickets.filter((t) => t.requester.id === user!.id || SEEDED_TICKETS.has(t.id));
  return json({ items, next_cursor: null });
});

route("GET", "/services/status", () => json({ items: state().services }), false);

// Admin
route("GET", "/metrics/summary", (_req, _p, user, url) => {
  if (user!.role !== "admin" && user!.role !== "agent") return error(403, "FORBIDDEN", "Admins only.");
  return json(metricsSummary(url.searchParams.get("from") ?? "2026-11-01", url.searchParams.get("to") ?? "2026-11-15"));
});

route("GET", "/guardrail-events", (_req, _p, user) => {
  if (user!.role !== "admin") return error(403, "FORBIDDEN", "Admins only.");
  return json({ items: state().guardrails.slice(0, 20) });
});

route("GET", "/kb/documents", (_req, _p, user) => {
  if (!isStaffSide(user!)) return error(403, "FORBIDDEN", "Only the IT team can manage the knowledge base.");
  return json({
    items: state().kb,
    kb_version: 14,
    last_reindex: { at: "2026-11-15T01:02:00Z", by: "Ramon Villareal", embedding_model: "gemini-embedding-001", dims: 768, store: "ChromaDB" },
  });
});

route("POST", "/kb/documents", async (req, _p, user) => {
  if (user!.role !== "admin") return error(403, "FORBIDDEN", "Admins only.");
  const form = await req.formData().catch(() => null);
  const file = form?.get("file");
  if (!(file instanceof File)) return error(422, "VALIDATION_ERROR", "Choose a Markdown (.md) file.");
  if (!file.name.endsWith(".md")) return error(422, "VALIDATION_ERROR", "Only Markdown (.md) files can be uploaded.");
  if (file.size > 200 * 1024) return error(422, "VALIDATION_ERROR", "The file is larger than 200 KB.");
  const text = await file.text();
  const fm = /^---\n([\s\S]*?)\n---/.exec(text.replace(/\r\n/g, "\n"));
  const get = (k: string) => fm?.[1].match(new RegExp(`^${k}:\\s*(.+)$`, "m"))?.[1].trim();
  const id = get("id");
  const title = get("title");
  if (!fm || !id || !title) return error(422, "VALIDATION_ERROR", "The file needs frontmatter with at least id and title.");
  if (/<script|<iframe/i.test(text)) return error(422, "VALIDATION_ERROR", "HTML <script> and <iframe> are not allowed.");
  const roles = (get("audience_roles") ?? "[staff, agent, admin]").replace(/[[\]]/g, "").split(",").map((r) => r.trim()) as Role[];
  const doc: KbDocument = {
    id, title, category: get("category") ?? "support-process", audience_roles: roles, version: 1, status: "changed",
    chunk_count: Math.max(1, (text.match(/^#{2,3} /gm) ?? []).length), last_updated: get("last_updated") ?? now().slice(0, 10), indexed_at: null,
  };
  const s = state();
  const i = s.kb.findIndex((d) => d.id === id);
  if (i >= 0) s.kb[i] = { ...doc, version: s.kb[i].version + 1 };
  else s.kb.push(doc);
  return json({ job_id: nextId("rj"), doc_id: id }, 202);
});

route("POST", "/kb/reindex", (_req, _p, user) => {
  if (user!.role !== "admin") return error(403, "FORBIDDEN", "Admins only.");
  const jobId = nextId("rj");
  state().jobs.set(jobId, { startedAt: Date.now(), total: state().kb.length });
  return json({ job_id: jobId, status: "queued" } satisfies ReindexJob, 202);
});

route("GET", "/kb/reindex/:id", (_req, [id]) => {
  const job = state().jobs.get(id);
  if (!job) return error(404, "NOT_FOUND", "Job not found.");
  const done = Math.min(job.total, Math.floor((Date.now() - job.startedAt) / 120));
  if (done >= job.total) {
    for (const d of state().kb) {
      if (d.status === "changed") d.status = "active";
      d.indexed_at = now();
    }
  }
  const res: ReindexJob = {
    job_id: id,
    status: done >= job.total ? "done" : "running",
    docs_total: job.total,
    docs_done: done,
    chunks_embedded: state().kb.slice(0, done).reduce((n, d) => n + d.chunk_count, 0),
    paused_reason: null,
  };
  return json(res);
});

export async function handleMock(req: Request, segments: string[]): Promise<Response> {
  const url = new URL(req.url);
  const path = `/${segments.join("/")}`;
  for (const r of routes) {
    if (r.method !== req.method) continue;
    const match = r.pattern.exec(path);
    if (!match) continue;
    const user = currentUser(req);
    if (r.auth && !user) return error(401, "UNAUTHENTICATED", "Sign in first.");
    return r.handler(req, match.slice(1).map(decodeURIComponent), user, url);
  }
  return json({ detail: "Not Found" }, 404);
}
