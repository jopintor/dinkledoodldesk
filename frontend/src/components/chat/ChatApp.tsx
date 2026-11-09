"use client";

// Member / staff chat. Figma screens 02 (answer + action), 02b (typing), 02c (new chat),
// 03 (escalated to a person) and 04 (mobile, 390 wide).
import { Headset, Menu, MessageCircle, Plus, Send, Shield, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState, useSyncExternalStore, type KeyboardEvent } from "react";

import { UserCard } from "@/components/shell";
import { Avatar, Badge, Button, LogoMark, QuickChip, Spinner, cx } from "@/components/ui";
import { ApiError, IS_MOCK, ask, escalate, getConversation, sendConversationMessage } from "@/lib/api";
import type { Citation, ToolCall, User } from "@/lib/types";

import { ActionCard } from "./ActionCard";
import { InfoPanel } from "./InfoPanel";
import {
  AgentMessage,
  AssistantMessage,
  EscalationBanner,
  EscalationOffer,
  ErrorLine,
  SystemLine,
  TypingBubble,
  UserBubble,
} from "./messages";
import {
  emptyConversation,
  historyOf,
  loadConversations,
  newId,
  quickQuestionsFor,
  sampleConversations,
  saveConversations,
  titleFor,
  type ChatItem,
  type Conversation,
} from "./model";

const SLA_CITATION: Citation = {
  n: 1,
  doc_id: "KB-024",
  title: "IT Incident Priority, SLA and Escalation Policy",
  section: "",
  chunk_id: "KB-024",
};

const MAX_LEN = 2000;

export function ChatApp({ user }: { user: User }) {
  const firstName = user.full_name.split(" ")[0] || "there";
  const [convos, setConvos] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [escalatingId, setEscalatingId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [input, setInput] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const convosRef = useRef<Conversation[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const loaded = useRef(false);

  // Load history from this browser once.
  useEffect(() => {
    const stored = loadConversations(user.id);
    const initial = stored?.length
      ? stored
      : [emptyConversation(firstName), ...(IS_MOCK ? sampleConversations(firstName, user.role) : [])];
    loaded.current = true;
    convosRef.current = initial;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate from localStorage after mount
    setConvos(initial);
    setActiveId(initial[0].id);
  }, [user.id, user.role, firstName]);

  useEffect(() => {
    convosRef.current = convos;
    if (loaded.current) saveConversations(user.id, convos);
  }, [convos, user.id]);

  const active = convos.find((c) => c.id === activeId) ?? null;

  const update = useCallback((id: string, fn: (c: Conversation) => Conversation) => {
    setConvos((prev) => prev.map((c) => (c.id === id ? fn(c) : c)));
  }, []);

  const append = useCallback(
    (id: string, ...items: ChatItem[]) =>
      update(id, (c) => ({ ...c, updatedAt: new Date().toISOString(), items: [...c.items, ...items] })),
    [update],
  );

  // Keep the newest message in view.
  const itemCount = active?.items.length ?? 0;
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [itemCount, pendingId, activeId]);

  // ---------- AI turn ----------

  const runAsk = useCallback(
    async (convoId: string, text: string, userItemId: string) => {
      const convo = convosRef.current.find((c) => c.id === convoId);
      if (!convo) return;
      const history = historyOf(convo.items.filter((i) => i.id !== userItemId && i.kind !== "error"));
      setPendingId(convoId);
      try {
        const res = await ask(text, history, userItemId);
        const now = new Date().toISOString();
        const items: ChatItem[] = [];
        const a = res.assistant_message;
        const offer =
          res.escalation_required ||
          res.suggested_actions.includes("escalate_to_agent") ||
          a?.action === "escalate";
        if (a && a.content) {
          items.push({
            kind: "assistant",
            id: newId(),
            at: now,
            content: a.content,
            citations: a.citations ?? [],
            confidence: a.confidence,
            offerEscalation: offer,
            serverId: a.id,
          });
        }
        for (const call of res.tool_calls) {
          if (call.status === "awaiting_confirmation") items.push({ kind: "tool", id: newId(), at: now, call });
          else if (call.tool_name === "check_service_status") {
            items.push({ kind: "system", id: newId(), at: now, content: "Checked the service status page" });
          } else if (call.message) items.push({ kind: "system", id: newId(), at: now, content: call.message });
        }
        update(convoId, (c) => ({
          ...c,
          updatedAt: now,
          items: [
            ...c.items.map((i) => (i.id === userItemId && i.kind === "user" ? { ...i, piiRedacted: res.user_message.pii_detected } : i)),
            ...items,
          ],
        }));
      } catch (err) {
        const e = err as ApiError;
        const message =
          e.code === "RATE_LIMITED"
            ? e.message
            : e.status === 401
              ? "Your session expired. Sign in again to keep chatting."
              : `DinkDesk couldn't answer just now. ${e.message}`;
        append(convoId, { kind: "error", id: newId(), at: new Date().toISOString(), content: message, retry: text });
      } finally {
        setPendingId(null);
      }
    },
    [append, update],
  );

  const send = useCallback(
    async (raw: string) => {
      const text = raw.trim().slice(0, MAX_LEN);
      const convo = convosRef.current.find((c) => c.id === activeId);
      if (!text || !convo || pendingId) return;
      setInput("");
      const userItem: ChatItem = { kind: "user", id: newId(), at: new Date().toISOString(), content: text };
      const isFirst = !convo.items.some((i) => i.kind === "user");
      update(convo.id, (c) => ({
        ...c,
        title: isFirst ? titleFor(text) : c.title,
        updatedAt: userItem.at,
        items: [...c.items, userItem],
      }));
      convosRef.current = convosRef.current.map((c) =>
        c.id === convo.id ? { ...c, items: [...c.items, userItem] } : c,
      );

      if (convo.status === "escalated") {
        try {
          await sendConversationMessage(convo.id, text);
        } catch (err) {
          append(convo.id, {
            kind: "error",
            id: newId(),
            at: new Date().toISOString(),
            content: `Your message didn't reach the IT Service Desk. ${(err as Error).message}`,
          });
        }
        return;
      }
      await runAsk(convo.id, text, userItem.id);
    },
    [activeId, append, pendingId, runAsk, update],
  );

  const retry = useCallback(
    (convoId: string, errorId: string, text: string) => {
      update(convoId, (c) => ({ ...c, items: c.items.filter((i) => i.id !== errorId) }));
      const convo = convosRef.current.find((c) => c.id === convoId);
      const lastUser = [...(convo?.items ?? [])].reverse().find((i) => i.kind === "user");
      void runAsk(convoId, text, lastUser?.id ?? newId());
    },
    [runAsk, update],
  );

  // ---------- Hand-over to a person ----------

  const startEscalation = useCallback(
    async (reason: "user_request" | "low_confidence" | "tool_failed" = "user_request") => {
      const convo = convosRef.current.find((c) => c.id === activeId);
      if (!convo || convo.status === "escalated" || escalatingId) return;
      setEscalatingId(convo.id);
      setDrawerOpen(false);
      const lastUser = [...convo.items].reverse().find((i) => i.kind === "user");
      try {
        const res = await escalate({
          conversation_id: convo.id,
          reason,
          summary: lastUser?.content ?? convo.title,
          title: convo.title,
          transcript: historyOf(convo.items),
        });
        const now = new Date().toISOString();
        update(convo.id, (c) => ({
          ...c,
          status: "escalated",
          ticket: { ticketNumber: res.ticket_number, jiraKey: res.jira_key },
          agentName: res.agent?.full_name ?? null,
          seen: [],
          updatedAt: now,
          items: [
            ...c.items,
            { kind: "assistant", id: newId(), at: now, content: res.message, citations: [SLA_CITATION] },
            {
              kind: "escalation",
              id: newId(),
              at: now,
              agentName: res.agent?.full_name ?? null,
              ticketNumber: res.ticket_number,
              jiraKey: res.jira_key,
              priority: res.priority,
              firstReplyMinutes: res.first_reply_minutes,
            },
          ],
        }));
        setRefreshKey((k) => k + 1);
      } catch (err) {
        append(convo.id, {
          kind: "error",
          id: newId(),
          at: new Date().toISOString(),
          content: `Couldn't reach the IT Service Desk. Call ext. 4357 if it's urgent. (${(err as Error).message})`,
        });
      } finally {
        setEscalatingId(null);
      }
    },
    [activeId, append, escalatingId, update],
  );

  // While a person has the chat, pull their replies.
  const escalatedId = active?.status === "escalated" ? active.id : null;
  useEffect(() => {
    if (!escalatedId) return;
    let stopped = false;
    async function poll() {
      try {
        const detail = await getConversation(escalatedId!);
        if (stopped) return;
        update(escalatedId!, (c) => {
          const seen = new Set(c.seen ?? []);
          const fresh: ChatItem[] = [];
          for (const m of detail.messages) {
            if (seen.has(m.id) || (m.sender_type !== "agent" && m.sender_type !== "system")) continue;
            seen.add(m.id);
            fresh.push(
              m.sender_type === "agent"
                ? { kind: "agent", id: m.id, at: m.created_at, name: m.sender_name ?? c.agentName ?? "IT Service Desk", content: m.content }
                : { kind: "system", id: m.id, at: m.created_at, content: m.content },
            );
          }
          const status = detail.status === "escalated" ? "escalated" : detail.status === "active" ? "active" : "resolved";
          if (!fresh.length && status === c.status) return c;
          return {
            ...c,
            status,
            agentName: detail.assigned_agent?.full_name ?? c.agentName,
            seen: [...seen],
            items: [...c.items, ...fresh],
          };
        });
      } catch {
        // keep polling; a hiccup shouldn't break the chat
      }
    }
    const first = setTimeout(poll, 1200);
    const timer = setInterval(poll, 3000);
    return () => {
      stopped = true;
      clearTimeout(first);
      clearInterval(timer);
    };
  }, [escalatedId, update]);

  // ---------- conversation list ----------

  function newChat() {
    const c = emptyConversation(firstName);
    setConvos((prev) => [c, ...prev.filter((p) => p.items.some((i) => i.kind === "user"))]);
    setActiveId(c.id);
    setDrawerOpen(false);
    setInput("");
  }

  const onToolChange = useCallback(
    (convoId: string, itemId: string, call: ToolCall) => {
      update(convoId, (c) => ({
        ...c,
        items: c.items.map((i) => (i.id === itemId && i.kind === "tool" ? { ...i, call } : i)),
      }));
      if (call.status === "succeeded") setRefreshKey((k) => k + 1);
    },
    [update],
  );

  if (!active) {
    return (
      <div className="flex h-dvh items-center justify-center text-primary">
        <Spinner className="size-6" />
      </div>
    );
  }

  const escalated = active.status === "escalated";
  const typing = pendingId === active.id;
  const agentFirst = active.agentName?.split(" ")[0];

  const sidebar = (
    <ChatSidebar
      user={user}
      convos={convos}
      activeId={active.id}
      onSelect={(id) => {
        setActiveId(id);
        setDrawerOpen(false);
      }}
      onNew={newChat}
    />
  );

  return (
    <div className="flex h-dvh overflow-hidden bg-page">
      <aside className="hidden w-[280px] shrink-0 border-r border-line bg-muted lg:flex">{sidebar}</aside>

      {drawerOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Chats">
          <button type="button" aria-label="Close menu" className="absolute inset-0 bg-ink/30" onClick={() => setDrawerOpen(false)} />
          <div className="relative flex h-full w-[300px] max-w-[85vw] bg-muted shadow-card">
            <button
              type="button"
              onClick={() => setDrawerOpen(false)}
              aria-label="Close menu"
              className="absolute top-5 right-3 rounded-sm p-1 text-body hover:bg-card"
            >
              <X size={20} aria-hidden />
            </button>
            {sidebar}
          </div>
        </div>
      )}

      <main className="flex min-w-0 flex-1 flex-col">
        {/* Mobile app bar (Figma 04) */}
        <header className="flex items-center gap-3 border-b border-line px-4 py-2.5 lg:hidden">
          <button type="button" onClick={() => setDrawerOpen(true)} aria-label="Open chats menu" className="rounded-sm p-1 text-ink">
            <Menu size={24} aria-hidden />
          </button>
          <LogoMark size={32} />
          <div className="min-w-0 flex-1">
            <p className="font-display text-[17px] leading-6 font-semibold text-ink">DinkDesk</p>
            <p className="truncate text-caption text-body">{active.title === "New chat" ? "IT help desk" : active.title}</p>
          </div>
          {!escalated && (
            <button
              type="button"
              onClick={() => void startEscalation()}
              aria-label="Talk to a person"
              className="rounded-full p-2 text-primary hover:bg-soft"
            >
              <Headset size={20} aria-hidden />
            </button>
          )}
          <Avatar kind="person" name={user.full_name} />
        </header>

        {/* Desktop header */}
        <header className="hidden min-h-[66px] items-center justify-between gap-4 border-b border-line px-8 lg:flex">
          <div className="flex min-w-0 items-center gap-3">
            <h1 className="truncate font-display text-[18px] leading-6 font-semibold text-ink">{active.title}</h1>
            {escalated ? (
              <Badge tone="info">With IT Service Desk</Badge>
            ) : active.status === "resolved" ? (
              <Badge tone="neutral">Resolved</Badge>
            ) : (
              <Badge tone="brand">AI answering</Badge>
            )}
          </div>
          {escalated && active.ticket ? (
            <Badge tone="neutral">
              Ticket {active.ticket.ticketNumber}
              {active.ticket.jiraKey ? ` · ${active.ticket.jiraKey}` : ""}
            </Badge>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              icon={escalatingId ? <Spinner /> : <Headset size={18} aria-hidden />}
              onClick={() => void startEscalation()}
              disabled={!!escalatingId}
            >
              Talk to a person
            </Button>
          )}
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto" aria-live="polite">
          <div className="mx-auto flex min-h-full w-full max-w-[840px] flex-col justify-end gap-6 px-4 py-4 lg:px-10">
            {active.items.map((item) => (
              <ChatItemView
                key={item.id}
                item={item}
                busy={!!escalatingId}
                escalated={escalated}
                onEscalate={() => void startEscalation(item.kind === "tool" ? "tool_failed" : "low_confidence")}
                onRetry={item.kind === "error" && item.retry ? () => retry(active.id, item.id, item.retry!) : undefined}
                onToolChange={(call) => onToolChange(active.id, item.id, call)}
              />
            ))}
            {typing && <TypingBubble />}
          </div>
        </div>

        <div className="mx-auto flex w-full max-w-[840px] flex-col gap-3 px-4 pt-3 pb-3 lg:px-10 lg:pb-4">
          {!escalated && (
            <div className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 lg:mx-0 lg:flex-wrap lg:px-0">
              {quickQuestionsFor(user.role).map((q) => (
                <QuickChip key={q} onClick={() => void send(q)} disabled={typing}>
                  {q}
                </QuickChip>
              ))}
            </div>
          )}
          <Composer
            value={input}
            onChange={setInput}
            onSend={() => void send(input)}
            disabled={typing}
            placeholder={
              escalated
                ? `Message ${agentFirst ?? "the IT team"} at the IT Service Desk…`
                : "Ask DinkDesk about passwords, Wi-Fi, DinkPOS, the Member App…"
            }
            mobilePlaceholder={escalated ? `Message ${agentFirst ?? "IT"}…` : "Ask DinkDesk…"}
          />
          <p className="hidden items-center justify-center gap-1.5 text-caption text-body sm:flex">
            <Shield size={14} aria-hidden />
            Never type your password here. DinkDesk can make mistakes – check the sources.
          </p>
        </div>
      </main>

      <div className="hidden w-[320px] shrink-0 xl:block">
        <InfoPanel refreshKey={refreshKey} />
      </div>
    </div>
  );
}

function ChatItemView({
  item,
  busy,
  escalated,
  onEscalate,
  onRetry,
  onToolChange,
}: {
  item: ChatItem;
  busy: boolean;
  escalated: boolean;
  onEscalate: () => void;
  onRetry?: () => void;
  onToolChange: (call: ToolCall) => void;
}) {
  switch (item.kind) {
    case "user":
      return (
        <UserBubble
          content={item.content}
          at={item.at}
          note={item.piiRedacted ? "Personal details were hidden before DinkDesk read this." : undefined}
        />
      );
    case "assistant":
      return (
        <AssistantMessage content={item.content} at={item.at} citations={item.citations} compactSources={false}>
          {item.offerEscalation && !escalated && <EscalationOffer onEscalate={onEscalate} busy={busy} />}
        </AssistantMessage>
      );
    case "agent":
      return <AgentMessage name={item.name} content={item.content} at={item.at} />;
    case "tool":
      return (
        <div className="lg:pl-12">
          <ActionCard call={item.call} onChange={onToolChange} onEscalate={onEscalate} />
        </div>
      );
    case "escalation":
      return <EscalationBanner {...item} />;
    case "system":
      return <SystemLine>{item.content}</SystemLine>;
    case "error":
      return <ErrorLine content={item.content} onRetry={onRetry} />;
  }
}

function Composer({
  value,
  onChange,
  onSend,
  disabled,
  placeholder,
  mobilePlaceholder,
}: {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  disabled: boolean;
  placeholder: string;
  mobilePlaceholder: string;
}) {
  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      if (!disabled) onSend();
    }
  }
  const tooLong = value.length > MAX_LEN;
  const narrow = useIsNarrow();
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!disabled) onSend();
      }}
      className="flex items-end gap-3 rounded-lg border border-line-strong bg-card py-2 pr-2 pl-5 shadow-card focus-within:border-primary"
    >
      <label className="sr-only" htmlFor="chat-input">
        Message
      </label>
      <textarea
        id="chat-input"
        rows={1}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder={narrow ? mobilePlaceholder : placeholder}
        className="max-h-36 min-h-11 flex-1 resize-none bg-transparent py-2.5 text-body-lg text-ink outline-none [field-sizing:content] placeholder:text-subtle"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim() || tooLong}
        aria-label="Send message"
        className="inline-flex size-11 shrink-0 items-center justify-center rounded-md bg-primary text-white transition-colors hover:bg-primary-hover disabled:opacity-60"
      >
        {disabled ? <Spinner /> : <Send size={20} aria-hidden />}
      </button>
    </form>
  );
}

function ChatSidebar({
  user,
  convos,
  activeId,
  onSelect,
  onNew,
}: {
  user: User;
  convos: Conversation[];
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
}) {
  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  const weekAgo = startOfToday.getTime() - 6 * 86_400_000;
  const groups: [string, Conversation[]][] = [
    ["Today", convos.filter((c) => Date.parse(c.updatedAt) >= startOfToday.getTime())],
    ["Earlier this week", convos.filter((c) => Date.parse(c.updatedAt) < startOfToday.getTime() && Date.parse(c.updatedAt) >= weekAgo)],
    ["Older", convos.filter((c) => Date.parse(c.updatedAt) < weekAgo)],
  ];
  return (
    <div className="flex h-full w-full flex-col gap-4 px-5 py-5">
      <div className="pr-8 lg:pr-0">
        <div className="flex items-center gap-2.5">
          <LogoMark />
          <span className="text-h2 text-ink">DinkDesk</span>
        </div>
      </div>
      <Button onClick={onNew} icon={<Plus size={20} aria-hidden />} className="w-full">
        New chat
      </Button>
      <nav aria-label="Chat history" className="-mx-1 flex flex-1 flex-col gap-2 overflow-y-auto px-1">
        {groups.map(([label, list]) =>
          list.length ? (
            <div key={label} className="flex flex-col gap-1">
              <p className="mt-2 mb-1 text-overline text-subtle">{label}</p>
              {list.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => onSelect(c.id)}
                  aria-current={c.id === activeId ? "true" : undefined}
                  className={cx(
                    "flex items-center gap-3 rounded-md border px-3 py-2.5 text-left text-body",
                    c.id === activeId
                      ? "border-line bg-card font-semibold text-ink"
                      : "border-transparent font-medium text-body hover:bg-card/60",
                  )}
                >
                  <MessageCircle size={18} className="shrink-0" aria-hidden />
                  <span className="truncate">{c.title}</span>
                  {c.status === "escalated" && <span className="ml-auto size-2 shrink-0 rounded-full bg-info" title="With IT Service Desk" />}
                </button>
              ))}
            </div>
          ) : null,
        )}
      </nav>
      {IS_MOCK && <p className="text-caption text-subtle">Running on the built-in mock API</p>}
      <UserCard user={user} />
    </div>
  );
}

/** True on phone-width screens (matches Tailwind's `sm` breakpoint). */
function useIsNarrow() {
  return useSyncExternalStore(
    (cb) => {
      const mq = window.matchMedia("(max-width: 639px)");
      mq.addEventListener("change", cb);
      return () => mq.removeEventListener("change", cb);
    },
    () => window.matchMedia("(max-width: 639px)").matches,
    () => false,
  );
}
