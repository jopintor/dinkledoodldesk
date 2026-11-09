// Shapes of the DinkDesk API, following docs/api.md.
// Fields marked "UI extension" are not in docs/api.md yet: the screens need them and the mock
// API returns them. The backend should add them (or the screens fall back gracefully).

export type Role = "member" | "staff" | "agent" | "admin";

export type User = {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  club_code?: string | null;
  job_title?: string | null;
};

export type MeResponse = { user: User; permissions: string[] };

export type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user?: User;
};

// ---------- Chat ----------

export type Citation = {
  n: number;
  doc_id: string;
  title: string;
  section: string;
  chunk_id: string;
};

export type AnswerMode = "generated" | "cached" | "template" | "degraded" | "agent_handling";

export type ToolCallStatus =
  | "awaiting_confirmation"
  | "awaiting_verification"
  | "awaiting_approval"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export type ToolCall = {
  id: string;
  tool_name: string;
  status: ToolCallStatus;
  arguments?: Record<string, unknown>;
  confirm_text?: string;
  result?: Record<string, unknown>;
  message?: string;
};

export type AssistantMessage = {
  id?: string;
  content: string;
  intent?: string | null;
  confidence?: number;
  retrieval_confidence?: number | null;
  answer_mode: AnswerMode;
  action?: "answer" | "clarify" | "escalate";
  citations: Citation[];
  latency_ms?: number;
};

// POST /api/v1/rag/ask (PR #18) and POST /conversations/{id}/messages share this shape.
export type AskResponse = {
  user_message: { id?: string; content: string; pii_detected: boolean };
  assistant_message: AssistantMessage | null;
  tool_calls: ToolCall[];
  conversation_status: ConversationStatus;
  suggested_actions: string[];
  escalation_required?: boolean;
};

export type HistoryItem = { role: "user" | "assistant"; content: string };

export type ConversationStatus = "active" | "escalated" | "resolved_ai" | "resolved_agent" | "closed";

// UI extension: POST /api/v1/escalations (user asks for a person). docs/api.md only has
// escalation through the escalate_to_agent tool; this is the "Talk to a person" button.
export type EscalateRequest = {
  conversation_id: string;
  reason: "user_request" | "low_confidence" | "negative_feedback" | "tool_failed";
  summary: string;
  /** UI extension: lets the agent read the chat, since /rag/ask doesn't store it. */
  title?: string;
  transcript?: HistoryItem[];
};

export type EscalateResponse = {
  escalation_id: string;
  ticket_number: string;
  jira_key: string | null;
  priority: Priority;
  first_reply_minutes: number;
  message: string;
  agent: { full_name: string } | null;
  agent_greeting: string | null;
};

export type ConversationMessage = {
  id: string;
  sender_type: "user" | "assistant" | "agent" | "system";
  sender_name?: string;
  content: string;
  citations?: Citation[];
  confidence?: number;
  created_at: string;
};

export type ConversationDetail = {
  id: string;
  status: ConversationStatus;
  assigned_agent: { id: string; full_name: string } | null;
  messages: ConversationMessage[];
  tool_calls: ToolCall[];
  tickets: { ticket_number: string; jira_key: string | null }[];
};

// ---------- Tickets, escalations ----------

export type Priority = "P1" | "P2" | "P3" | "P4";
export type TicketStatus = "open" | "in_progress" | "waiting_on_user" | "escalated" | "resolved" | "closed";

export type Ticket = {
  id: string;
  ticket_number: string;
  jira_key: string | null;
  summary: string;
  category: string;
  affected_system?: string | null;
  priority: Priority;
  status: TicketStatus;
  club_code: string | null;
  requester: { id: string; full_name: string };
  assignee: { id: string; full_name: string } | null;
  source: "ai_tool" | "manual" | "escalation";
  created_at: string;
};

export type EscalationStatus = "queued" | "assigned" | "resolved";

export type Escalation = {
  id: string;
  conversation_id: string;
  ticket_number: string;
  reason: string;
  urgency: "normal" | "high";
  handoff_summary: string;
  user: { full_name: string; role: Role; club_code: string | null; job_title?: string | null };
  status: EscalationStatus;
  created_at: string;
  waiting_s: number;
  // UI extension fields (agent queue card + ticket detail in Figma screen 05):
  title?: string;
  priority?: Priority;
  jira_key?: string | null;
  flag?: string;
  category_label?: string;
  confidence?: number | null;
  sla_due_at?: string | null;
  summary_points?: string[];
  suggested_next_step?: string | null;
  citations?: Citation[];
  assigned_agent?: { id: string; full_name: string } | null;
};

// ---------- Service status ----------

export type ServiceState =
  | "operational"
  | "degraded_performance"
  | "partial_outage"
  | "major_outage"
  | "maintenance";

export type ServiceStatus = {
  service_key: string;
  display_name: string;
  status: ServiceState;
  club_code: string | null;
  message: string | null;
  updated_at: string;
};

// ---------- Metrics, guardrails ----------

export type MetricsSummary = {
  period: { from: string; to: string };
  conversations: number;
  deflection_rate: number;
  escalation_rate: number;
  automation_success_rate: number;
  tool_calls: Record<string, number>;
  latency_ms: { p50: number; p95: number };
  cache_hit_rate: number;
  mttr_hours: number;
  csat: number;
  guardrail_blocks?: { prompt_injection: number; pii_redacted: number; rbac_denied: number };
  latest_eval?: EvalSummary;
  // UI extension fields (Figma screen 06):
  previous?: { deflection_rate: number; mttr_hours: number; p95_ms: number };
  previous_eval?: EvalSummary;
  tickets_created?: number;
  tickets_by_category?: { category: string; label: string; count: number }[];
};

export type EvalSummary = {
  run_id: string;
  label: string;
  faithfulness: number;
  answer_relevance: number;
  context_precision: number;
  // UI extension:
  malicious_blocked?: number;
  malicious_total?: number;
  questions?: number;
  ran_at?: string;
};

export type GuardrailEvent = {
  id: string;
  created_at: string;
  stage: "input" | "output";
  type: "prompt_injection" | "pii_redacted" | "rbac_denied" | string;
  action: "blocked" | "redacted" | "denied" | string;
  detector?: string;
  score?: number;
  rule_ids?: string[];
  user: { full_name: string; role: Role };
  // UI extension: the redacted text that was sent.
  excerpt?: string;
};

// ---------- Knowledge base ----------

export type KbDocument = {
  id: string;
  title: string;
  category: string;
  audience_roles: Role[];
  version: number;
  status: "active" | "superseded" | "archived" | "changed";
  chunk_count: number;
  last_updated: string;
  indexed_at: string | null;
  superseded_by?: string | null;
};

export type KbDocumentList = {
  items: KbDocument[];
  kb_version: number;
  // UI extension (index banner):
  last_reindex?: {
    at: string;
    by: string;
    embedding_model: string;
    dims: number;
    store: string;
  };
};

export type ReindexJob = {
  job_id?: string;
  status: "queued" | "running" | "done" | "failed";
  docs_total?: number;
  docs_done?: number;
  chunks_embedded?: number;
  paused_reason?: string | null;
};

export type Page<T> = { items: T[]; next_cursor: string | null };
