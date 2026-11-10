// The only place the frontend talks to the DinkDesk API (see CONTRIBUTING.md).
//
// NEXT_PUBLIC_API_BASE_URL (set in .env.local, see .env.example):
//   /mock-api                          -> built-in mock API in src/app/mock-api (default, no backend)
//   http://localhost:8000              -> backend running locally / in Docker
//   https://<tunnel>.trycloudflare.com -> Jose's PC via Cloudflare Tunnel
//
// With a real backend, endpoints marked `fallback: true` fall back to the mock API when the
// backend answers "route not found" (FastAPI's 404 {"detail":"Not Found"} or 405). That way
// the screens keep working while Andre's endpoints land one by one, and each one switches to
// the real data automatically once it exists. `mockedEndpoints` lists which ones fell back.

import type {
  AskResponse,
  ConversationDetail,
  ConversationMessage,
  EscalateRequest,
  EscalateResponse,
  Escalation,
  GuardrailEvent,
  HistoryItem,
  KbDocument,
  KbDocumentList,
  LoginResponse,
  MeResponse,
  MetricsSummary,
  Page,
  ReindexJob,
  Role,
  ServiceStatus,
  Ticket,
  ToolCall,
  User,
} from "./types";

export const MOCK_BASE_URL = "/mock-api";

export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || MOCK_BASE_URL).replace(/\/$/, "");

export const IS_MOCK = API_BASE_URL === MOCK_BASE_URL;

const V1 = "/api/v1";

export type HealthResponse = {
  status: string;
  version: string;
  env: string;
  llm_provider: string;
  llm_configured: boolean;
};

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

let authToken: string | null = null;

/** Called by the auth provider; every request after this sends the bearer token. */
export function setAuthToken(token: string | null) {
  authToken = token;
}

/** Endpoints that fell back to the mock API during this session (live mode only). */
export const mockedEndpoints = new Set<string>();

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  form?: FormData;
  /** Fall back to the mock API if the backend doesn't have this route yet. */
  fallback?: boolean;
  signal?: AbortSignal;
};

function buildInit(opts: RequestOptions): RequestInit {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;
  let body: BodyInit | undefined;
  if (opts.form) {
    body = opts.form;
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  return { method: opts.method ?? "GET", headers, body, cache: "no-store", signal: opts.signal };
}

async function isMissingRoute(res: Response): Promise<boolean> {
  if (res.status === 405) return true;
  if (res.status !== 404) return false;
  try {
    const data = await res.clone().json();
    // FastAPI's default for unknown routes; real "not found" errors use the error envelope.
    return data?.detail === "Not Found";
  } catch {
    return false;
  }
}

async function toApiError(res: Response): Promise<ApiError> {
  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    // not JSON
  }
  const envelope = (data as { error?: { code?: string; message?: string; details?: unknown } })?.error;
  if (envelope?.message) {
    return new ApiError(res.status, envelope.code ?? "ERROR", envelope.message, envelope.details);
  }
  // FastAPI HTTPException: {"detail": "..."} or validation errors {"detail": [...]}
  const detail = (data as { detail?: unknown })?.detail;
  if (typeof detail === "string") return new ApiError(res.status, codeFor(res.status), detail);
  if (Array.isArray(detail)) {
    return new ApiError(res.status, "VALIDATION_ERROR", "Some fields are not valid.", detail);
  }
  return new ApiError(res.status, codeFor(res.status), `Request failed (${res.status} ${res.statusText})`);
}

function codeFor(status: number): string {
  if (status === 401) return "UNAUTHENTICATED";
  if (status === 403) return "FORBIDDEN";
  if (status === 404) return "NOT_FOUND";
  if (status === 429) return "RATE_LIMITED";
  if (status >= 500) return "SERVER_ERROR";
  return "ERROR";
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, buildInit(opts));
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError(0, "NETWORK", `Can't reach the DinkDesk API at ${API_BASE_URL}. Is the backend running?`);
  }
  if (!IS_MOCK && opts.fallback && (await isMissingRoute(res))) {
    mockedEndpoints.add(`${opts.method ?? "GET"} ${path.split("?")[0]}`);
    res = await fetch(`${MOCK_BASE_URL}${path}`, buildInit(opts));
  }
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---------- Health ----------

export function getHealth() {
  return request<HealthResponse>("/health");
}

/** Kept for the original scaffold; prefer the typed functions below. */
export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path);
}

// ---------- Auth ----------

// The backend's /auth/me currently returns the user object flat, without `permissions`
// (docs/api.md §3 wraps it as {user, permissions}). Accept both.
function normalizeMe(data: unknown): MeResponse {
  const d = data as Partial<MeResponse> & Partial<User> & { club_id?: unknown };
  const raw = (d.user ?? d) as Partial<User> & { id?: unknown };
  const user: User = {
    id: String(raw.id ?? ""),
    email: raw.email ?? "",
    full_name: raw.full_name ?? raw.email ?? "",
    role: (raw.role ?? "member") as Role,
    club_code: raw.club_code ?? null,
    job_title: raw.job_title ?? null,
  };
  return { user, permissions: d.permissions ?? [] };
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>(`${V1}/auth/login`, { method: "POST", body: { email, password } });
}

export async function getMe(): Promise<MeResponse> {
  return normalizeMe(await request<unknown>(`${V1}/auth/me`));
}

export function logout() {
  return request<void>(`${V1}/auth/logout`, { method: "POST" });
}

// ---------- Chat ----------

/**
 * One chat turn through the RAG pipeline (PR #18: POST /api/v1/rag/ask). Stateless: the
 * frontend sends the last few turns as `history` until conversations are stored server-side.
 */
export function ask(content: string, history: HistoryItem[], clientMessageId?: string) {
  return request<AskResponse>(`${V1}/rag/ask`, {
    method: "POST",
    body: { content, history: history.slice(-6), client_message_id: clientMessageId },
  });
}

/** Message sent while a person from IT has the chat (the AI stays quiet). */
export function sendConversationMessage(conversationId: string, content: string) {
  return request<AskResponse>(`${V1}/conversations/${conversationId}/messages`, {
    method: "POST",
    body: { content },
    fallback: true,
  });
}

export function confirmToolCall(id: string, args?: Record<string, unknown>) {
  return request<ToolCall>(`${V1}/tool-calls/${id}/confirm`, {
    method: "POST",
    body: args ? { arguments: args } : {},
    fallback: true,
  });
}

export function cancelToolCall(id: string) {
  return request<ToolCall>(`${V1}/tool-calls/${id}/cancel`, { method: "POST", body: {}, fallback: true });
}

export function verifyToolCall(id: string, otp: string) {
  return request<ToolCall>(`${V1}/tool-calls/${id}/verify`, { method: "POST", body: { otp }, fallback: true });
}

export function escalate(body: EscalateRequest) {
  return request<EscalateResponse>(`${V1}/escalations`, { method: "POST", body, fallback: true });
}

export function sendFeedback(messageId: string, value: 1 | -1, comment?: string) {
  return request<void>(`${V1}/messages/${messageId}/feedback`, {
    method: "POST",
    body: { value, comment },
    fallback: true,
  });
}

// ---------- Service status, tickets ----------

export function getServiceStatus() {
  return request<{ items: ServiceStatus[] }>(`${V1}/services/status`, { fallback: true });
}

export function listTickets(params: { status?: string; limit?: number } = {}) {
  const q = new URLSearchParams();
  if (params.status) q.set("status", params.status);
  if (params.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return request<Page<Ticket>>(`${V1}/tickets${qs ? `?${qs}` : ""}`, { fallback: true });
}

// ---------- Agent ----------

export function listEscalations(status = "queued") {
  return request<Page<Escalation>>(`${V1}/escalations?status=${encodeURIComponent(status)}`, { fallback: true });
}

export function getConversation(id: string) {
  return request<ConversationDetail>(`${V1}/conversations/${id}`, { fallback: true });
}

export function claimEscalation(id: string) {
  return request<{ id: string; status: string; assigned_agent_id: string }>(`${V1}/escalations/${id}/claim`, {
    method: "POST",
    body: {},
    fallback: true,
  });
}

export function resolveEscalation(
  id: string,
  body: { resolution: "resolved" | "returned_to_ai"; note?: string; close_ticket: boolean; return_to_ai: boolean },
) {
  return request<{ id: string; status: string }>(`${V1}/escalations/${id}/resolve`, {
    method: "POST",
    body,
    fallback: true,
  });
}

export function sendAgentMessage(conversationId: string, content: string) {
  return request<ConversationMessage>(`${V1}/conversations/${conversationId}/agent-messages`, {
    method: "POST",
    body: { content },
    fallback: true,
  });
}

// ---------- Admin ----------

export function getMetricsSummary(from: string, to: string) {
  return request<MetricsSummary>(`${V1}/metrics/summary?from=${from}&to=${to}`, { fallback: true });
}

export function listGuardrailEvents(since?: string) {
  const qs = since ? `?since=${encodeURIComponent(since)}` : "";
  return request<{ items: GuardrailEvent[] }>(`${V1}/guardrail-events${qs}`, { fallback: true });
}

export function listKbDocuments() {
  return request<KbDocumentList>(`${V1}/kb/documents`, { fallback: true });
}

export function uploadKbDocument(file: File) {
  const form = new FormData();
  form.append("file", file);
  return request<{ job_id: string; doc_id: string }>(`${V1}/kb/documents`, { method: "POST", form, fallback: true });
}

export function startReindex(mode: "changed" | "full" = "changed") {
  return request<ReindexJob>(`${V1}/kb/reindex`, { method: "POST", body: { mode }, fallback: true });
}

export function getReindexJob(jobId: string) {
  return request<ReindexJob>(`${V1}/kb/reindex/${jobId}`, { fallback: true });
}

export type { KbDocument };
