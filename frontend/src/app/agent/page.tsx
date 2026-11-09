"use client";

// Figma screen 05: Agent – Escalation queue + ticket detail.
import { AlertTriangle, ArrowRight, Check, Clock, Headset, Send, Sparkle } from "lucide-react";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { AgentMessage, AssistantMessage, SystemLine, UserBubble } from "@/components/chat/messages";
import { AppShell } from "@/components/shell";
import { Badge, Button, CitationChip, ErrorNote, FullPageLoading, Spinner, cx } from "@/components/ui";
import {
  ApiError,
  claimEscalation,
  getConversation,
  listEscalations,
  resolveEscalation,
  sendAgentMessage,
} from "@/lib/api";
import { useRequireRole } from "@/lib/auth";
import { PRIORITY_TONE, ROLE_LABEL, formatTime, minutesLabel } from "@/lib/format";
import type { ConversationDetail, Escalation, Priority, Role, User } from "@/lib/types";

const ROLES: Role[] = ["agent", "admin"];

export default function AgentPage() {
  const user = useRequireRole(ROLES);
  if (!user) return <FullPageLoading />;
  return <AgentQueue user={user} />;
}

function subtitleOf(e: Escalation) {
  return [e.user.full_name, e.user.job_title ?? ROLE_LABEL[e.user.role], e.user.club_code].filter(Boolean).join(" · ");
}

function AgentQueue({ user }: { user: User }) {
  const [items, setItems] = useState<Escalation[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Priority | "all">("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await listEscalations("open");
      setItems(res.items);
      setError(null);
      setSelectedId((cur) => cur ?? res.items.find((e) => e.priority === "P2")?.id ?? res.items[0]?.id ?? null);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial fetch + refresh every 10 s
    void load();
    const t = setInterval(load, 10_000);
    return () => clearInterval(t);
  }, [load]);

  const waiting = (items ?? []).filter((e) => e.status !== "resolved");
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const e of waiting) c[e.priority ?? "P4"] = (c[e.priority ?? "P4"] ?? 0) + 1;
    return c;
  }, [waiting]);
  const shown = waiting.filter((e) => filter === "all" || e.priority === filter);
  const oldest = waiting.reduce((m, e) => Math.max(m, e.waiting_s), 0);
  const selected = (items ?? []).find((e) => e.id === selectedId) ?? null;

  return (
    <AppShell user={user} escalationCount={waiting.length}>
      <div className="grid min-h-screen lg:h-screen lg:grid-cols-[420px_1fr]">
        <section className="flex flex-col gap-5 border-line bg-page px-6 py-6 lg:overflow-y-auto lg:border-r" aria-label="Escalation queue">
          <div>
            <h1 className="text-h1 text-ink">Escalation queue</h1>
            <p className="text-body-lg text-body">
              {items === null
                ? "Loading…"
                : waiting.length
                  ? `${waiting.length} waiting · oldest ${minutesLabel(oldest)} · sorted by priority`
                  : "Nobody is waiting. Nice."}
            </p>
          </div>
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Filter by priority">
            {(["all", "P1", "P2", "P3", "P4"] as const)
              .filter((p) => p === "all" || counts[p])
              .map((p) => (
                <button
                  key={p}
                  type="button"
                  role="tab"
                  aria-selected={filter === p}
                  onClick={() => setFilter(p)}
                  className={cx(
                    "rounded-full border px-3 py-1.5 text-label",
                    filter === p ? "border-primary bg-primary text-white" : "border-line-strong bg-card text-ink hover:bg-softer",
                  )}
                >
                  {p === "all" ? `All ${waiting.length}` : `${p} · ${counts[p]}`}
                </button>
              ))}
          </div>
          {error && <ErrorNote>{error}</ErrorNote>}
          <ul className="flex flex-col gap-4">
            {shown.map((e) => (
              <li key={e.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(e.id)}
                  aria-current={e.id === selectedId ? "true" : undefined}
                  className={cx(
                    "flex w-full flex-col gap-2 rounded-lg bg-card p-4 text-left transition-colors",
                    e.id === selectedId ? "border-2 border-primary p-[15px] shadow-card" : "border border-line hover:border-line-strong",
                  )}
                >
                  <div className="flex items-center justify-between">
                    <Badge tone={PRIORITY_TONE[e.priority ?? "P4"]}>{e.priority ?? "P4"}</Badge>
                    <span className="flex items-center gap-1.5 text-caption text-subtle">
                      <Clock size={14} aria-hidden />
                      {minutesLabel(e.waiting_s)}
                    </span>
                  </div>
                  <p className="text-body-lg font-semibold text-ink">{e.title ?? e.handoff_summary}</p>
                  <p className="text-caption text-body">{subtitleOf(e)}</p>
                  {e.flag && (
                    <p className="flex items-center gap-1.5 text-label font-medium text-body">
                      <AlertTriangle size={14} className="text-warning" aria-hidden />
                      {e.flag}
                    </p>
                  )}
                  {e.assigned_agent && (
                    <p className="text-caption text-info">With {e.assigned_agent.id === user.id ? "you" : e.assigned_agent.full_name}</p>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </section>

        {selected ? (
          <TicketDetail key={selected.id} escalation={selected} user={user} onChanged={load} />
        ) : (
          <section className="hidden items-center justify-center p-10 text-body lg:flex">
            {items === null ? <Spinner /> : "Pick a chat from the queue."}
          </section>
        )}
      </div>
    </AppShell>
  );
}

function TicketDetail({ escalation: e, user, onChanged }: { escalation: Escalation; user: User; onChanged: () => void }) {
  const [convo, setConvo] = useState<ConversationDetail | null>(null);
  const [busy, setBusy] = useState<"claim" | "resolve" | "send" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const [showResolve, setShowResolve] = useState(false);
  const [note, setNote] = useState("");
  const [closeTicket, setCloseTicket] = useState(true);
  const [handBack, setHandBack] = useState(false);
  const [now] = useState(() => Date.now());

  const mine = e.assigned_agent?.id === user.id;
  const takenByOther = !!e.assigned_agent && !mine;
  const resolved = e.status === "resolved";

  const loadConvo = useCallback(async () => {
    try {
      setConvo(await getConversation(e.conversation_id));
    } catch (err) {
      setError((err as Error).message);
    }
  }, [e.conversation_id]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch the chat, then follow new messages
    void loadConvo();
    const t = setInterval(loadConvo, 3000);
    return () => clearInterval(t);
  }, [loadConvo]);

  async function act(kind: "claim" | "resolve", fn: () => Promise<unknown>) {
    setBusy(kind);
    setError(null);
    try {
      await fn();
      onChanged();
      void loadConvo();
      if (kind === "resolve") setShowResolve(false);
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(null);
    }
  }

  async function onSend(ev: FormEvent) {
    ev.preventDefault();
    const text = reply.trim();
    if (!text) return;
    setBusy("send");
    setError(null);
    try {
      await sendAgentMessage(e.conversation_id, text);
      setReply("");
      void loadConvo();
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(null);
    }
  }

  const sla = e.sla_due_at ? new Date(e.sla_due_at) : null;
  const slaLeft = sla ? Math.round((sla.getTime() - now) / 60000) : null;
  const lowConfidence = (e.confidence ?? 1) < 0.5;

  return (
    <section className="flex min-w-0 flex-col lg:overflow-y-auto" aria-label="Ticket detail">
      <div className="flex flex-col gap-5 border-b border-line px-6 py-6 lg:px-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex min-w-0 flex-col gap-2">
            <div className="flex flex-wrap gap-2">
              <Badge tone={PRIORITY_TONE[e.priority ?? "P4"]}>{e.priority ?? "P4"}</Badge>
              <Badge tone={resolved ? "success" : "info"}>{resolved ? "Resolved" : mine ? "You have this chat" : "Escalated"}</Badge>
              <Badge tone="neutral">
                {e.ticket_number}
                {e.jira_key ? ` · ${e.jira_key}` : ""}
              </Badge>
            </div>
            <h2 className="max-w-[340px] text-h2 text-ink">{e.title ?? "Escalated chat"}</h2>
          </div>
          {!resolved && (
            <div className="flex flex-wrap gap-3">
              <Button variant="secondary" icon={<Check size={18} aria-hidden />} onClick={() => setShowResolve((v) => !v)} disabled={!!busy}>
                Resolve
              </Button>
              {!mine && (
                <Button
                  icon={busy === "claim" ? <Spinner /> : <Headset size={18} aria-hidden />}
                  onClick={() => act("claim", () => claimEscalation(e.id))}
                  disabled={!!busy || takenByOther}
                  title={takenByOther ? `${e.assigned_agent!.full_name} has this chat` : undefined}
                >
                  Take over chat
                </Button>
              )}
            </div>
          )}
        </div>

        {showResolve && (
          <form
            className="flex flex-col gap-3 rounded-lg border border-line bg-card p-4"
            onSubmit={(ev) => {
              ev.preventDefault();
              void act("resolve", () =>
                resolveEscalation(e.id, {
                  resolution: handBack ? "returned_to_ai" : "resolved",
                  note: note.trim() || undefined,
                  close_ticket: closeTicket,
                  return_to_ai: handBack,
                }),
              );
            }}
          >
            <label className="flex flex-col gap-1.5">
              <span className="text-label text-ink">What fixed it?</span>
              <textarea
                value={note}
                onChange={(ev) => setNote(ev.target.value)}
                rows={2}
                placeholder="e.g. Verified by phone, reset from the StaffID console"
                className="rounded-md border border-line-strong bg-card px-3 py-2 text-body outline-none focus:border-primary"
              />
            </label>
            <label className="flex items-center gap-2 text-label font-medium text-ink">
              <input type="checkbox" checked={closeTicket} onChange={(ev) => setCloseTicket(ev.target.checked)} className="accent-primary" />
              Close ticket {e.ticket_number}
            </label>
            <label className="flex items-center gap-2 text-label font-medium text-ink">
              <input type="checkbox" checked={handBack} onChange={(ev) => setHandBack(ev.target.checked)} className="accent-primary" />
              Hand the chat back to DinkDesk
            </label>
            <Button type="submit" size="sm" className="self-start" disabled={!!busy} icon={busy === "resolve" ? <Spinner /> : undefined}>
              Mark resolved
            </Button>
          </form>
        )}

        <dl className="grid grid-cols-2 gap-3 xl:grid-cols-4">
          <Tile label="Requester" value={subtitleOf(e)} />
          <Tile label="Category" value={e.category_label ?? e.reason.replace(/_/g, " ")} />
          <Tile
            label="AI confidence"
            value={e.confidence == null ? "–" : `${e.confidence.toFixed(2)} · ${lowConfidence ? "low" : "ok"}`}
            valueClass={lowConfidence ? "text-warning" : undefined}
          />
          <Tile
            label={`SLA (${e.priority ?? "P4"})`}
            value={sla ? `First reply by ${formatTime(sla)} · ${slaLeft! >= 0 ? `${slaLeft} min left` : `${-slaLeft!} min late`}` : "–"}
            valueClass={slaLeft !== null && slaLeft < 15 ? "text-danger" : undefined}
          />
        </dl>
        {error && <ErrorNote>{error}</ErrorNote>}
      </div>

      <div className="flex flex-col gap-6 px-6 py-6 lg:px-8">
        <div className="flex flex-col gap-4 rounded-xl border border-line bg-softer p-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="flex items-center gap-2 text-h3 text-ink">
              <Sparkle size={18} className="text-primary" aria-hidden />
              AI summary
            </h3>
            <span className="text-caption text-subtle">Written by DinkDesk · check before acting</span>
          </div>
          <ul className="flex flex-col gap-1 text-body text-ink">
            {(e.summary_points?.length ? e.summary_points : [e.handoff_summary]).map((p) => (
              <li key={p}>• {p}</li>
            ))}
          </ul>
          {e.suggested_next_step && (
            <p className="flex gap-3 rounded-md bg-card p-4 text-body font-semibold text-ink">
              <ArrowRight size={18} className="mt-0.5 shrink-0 text-body" aria-hidden />
              <span>Suggested next step: {e.suggested_next_step}</span>
            </p>
          )}
          {!!e.citations?.length && (
            <div className="flex flex-wrap gap-2">
              {e.citations.map((c) => (
                <CitationChip key={c.n} citation={{ ...c, section: "" }} />
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-6">
          <div className="flex flex-wrap items-baseline gap-3">
            <h3 className="text-h3 text-ink">Conversation</h3>
            <span className="text-caption text-body">
              {mine
                ? "You have this chat – DinkDesk stays quiet until you resolve it"
                : "DinkDesk is paused for this chat until you take over or resolve it"}
            </span>
          </div>
          {convo === null && <Spinner className="text-primary" />}
          {convo?.messages.map((m) =>
            m.sender_type === "user" ? (
              <UserBubble key={m.id} content={m.content} at={m.created_at} />
            ) : m.sender_type === "assistant" ? (
              <AssistantMessage key={m.id} content={m.content} at={m.created_at} citations={m.citations ?? []} />
            ) : m.sender_type === "agent" ? (
              <AgentMessage key={m.id} name={m.sender_name ?? "IT Service Desk"} content={m.content} at={m.created_at} />
            ) : (
              <SystemLine key={m.id}>{m.content}</SystemLine>
            ),
          )}
          {mine && !resolved && (
            <form onSubmit={onSend} className="flex items-end gap-3 rounded-lg border border-line-strong bg-card py-2 pr-2 pl-4 shadow-card focus-within:border-primary">
              <label htmlFor="agent-reply" className="sr-only">
                Reply to {e.user.full_name}
              </label>
              <textarea
                id="agent-reply"
                rows={1}
                value={reply}
                onChange={(ev) => setReply(ev.target.value)}
                onKeyDown={(ev) => {
                  if (ev.key === "Enter" && !ev.shiftKey) {
                    ev.preventDefault();
                    (ev.currentTarget.form as HTMLFormElement).requestSubmit();
                  }
                }}
                placeholder={`Reply to ${e.user.full_name.split(" ")[0]}…`}
                className="max-h-36 min-h-11 flex-1 resize-none bg-transparent py-2.5 text-body-lg outline-none [field-sizing:content] placeholder:text-subtle"
              />
              <button
                type="submit"
                aria-label="Send reply"
                disabled={busy === "send" || !reply.trim()}
                className="inline-flex size-11 items-center justify-center rounded-md bg-primary text-white hover:bg-primary-hover disabled:opacity-60"
              >
                {busy === "send" ? <Spinner /> : <Send size={20} aria-hidden />}
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}

function Tile({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-md bg-muted p-3">
      <dt className="text-caption text-subtle">{label}</dt>
      <dd className={cx("text-body font-semibold text-ink", valueClass)}>{value}</dd>
    </div>
  );
}
