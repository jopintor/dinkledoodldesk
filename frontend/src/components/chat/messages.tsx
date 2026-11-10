// Chat message pieces from the Figma style guide: Chat message (4:69, From=User/DinkDesk/Agent),
// Escalation banner (4:109), and the typing state from screen 02b.
import { Headset, RotateCcw, ShieldAlert } from "lucide-react";
import { Fragment, type ReactNode } from "react";

import { Avatar, Badge, Button, Sources, cx } from "@/components/ui";
import { formatTime } from "@/lib/format";
import type { Citation } from "@/lib/types";

/** Renders model text: line breaks, **bold**, and `code`. No HTML from the model is trusted. */
export function RichText({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <>
      {lines.map((line, i) => (
        <Fragment key={i}>
          {line.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, j) => {
            if (part.startsWith("**") && part.endsWith("**")) return <strong key={j}>{part.slice(2, -2)}</strong>;
            if (part.startsWith("`") && part.endsWith("`"))
              return (
                <code key={j} className="rounded bg-muted px-1 text-[0.9em]">
                  {part.slice(1, -1)}
                </code>
              );
            return <Fragment key={j}>{part}</Fragment>;
          })}
          {i < lines.length - 1 && <br />}
        </Fragment>
      ))}
    </>
  );
}

export function UserBubble({ content, at, note }: { content: string; at: string; note?: string }) {
  return (
    <div className="flex flex-col items-end gap-1">
      <div className="max-w-[85%] rounded-[16px_16px_4px_16px] bg-primary px-4 py-3 text-body-lg break-words whitespace-pre-wrap text-white sm:max-w-[352px]">
        {content}
      </div>
      <span className="text-caption text-subtle">{formatTime(at)}</span>
      {note && <span className="text-caption text-info">{note}</span>}
    </div>
  );
}

function SenderRow({ kind, name, at }: { kind: "dinkdesk" | "agent"; name: string; at?: string }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-body font-semibold text-ink">{name}</span>
      {kind === "dinkdesk" ? <Badge tone="brand">AI assistant</Badge> : <Badge tone="info">IT Service Desk</Badge>}
      {at && <span className="text-caption text-subtle">{at}</span>}
    </div>
  );
}

export function AssistantMessage({
  content,
  at,
  citations,
  compactSources,
  children,
}: {
  content: string;
  at: string;
  citations: Citation[];
  compactSources?: boolean;
  children?: ReactNode;
}) {
  return (
    <div className="flex items-start gap-3">
      <Avatar kind="dinkdesk" />
      <div className="flex min-w-0 flex-1 flex-col items-start gap-2">
        <SenderRow kind="dinkdesk" name="DinkDesk" at={formatTime(at)} />
        <div className="max-w-full rounded-[4px_16px_16px_16px] border border-line bg-card p-4 text-body-lg break-words text-ink">
          <RichText text={content} />
        </div>
        <Sources citations={citations} compact={compactSources} />
        {children}
      </div>
    </div>
  );
}

export function AgentMessage({ name, content, at }: { name: string; content: string; at: string }) {
  return (
    <div className="flex items-start gap-3">
      <Avatar kind="agent" />
      <div className="flex min-w-0 flex-1 flex-col items-start gap-2">
        <SenderRow kind="agent" name={name} at={formatTime(at)} />
        <div className="max-w-full rounded-[4px_16px_16px_16px] bg-info-bg p-4 text-body-lg break-words text-ink">
          <RichText text={content} />
        </div>
      </div>
    </div>
  );
}

export function TypingBubble({ label = "DinkDesk is typing" }: { label?: string }) {
  return (
    <div className="flex items-start gap-3" role="status" aria-label={label}>
      <Avatar kind="dinkdesk" />
      <div className="flex flex-col items-start gap-2">
        <SenderRow kind="dinkdesk" name="DinkDesk" at={formatTime(new Date())} />
        <div className="flex h-[58px] w-[242px] max-w-full items-center gap-1.5 rounded-[4px_16px_16px_16px] border border-line bg-card px-4">
          {[0, 1, 2].map((i) => (
            <span key={i} className="dd-typing-dot size-1.5 rounded-full bg-body" style={{ animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
      </div>
    </div>
  );
}

export function EscalationBanner({
  agentName,
  ticketNumber,
  jiraKey,
  priority,
  firstReplyMinutes,
}: {
  agentName: string | null;
  ticketNumber: string;
  jiraKey: string | null;
  priority: string;
  firstReplyMinutes: number;
}) {
  const reply = firstReplyMinutes >= 60 ? `${Math.round(firstReplyMinutes / 60)} hour${firstReplyMinutes >= 120 ? "s" : ""}` : `${firstReplyMinutes} min`;
  return (
    <div className="flex items-center gap-3 rounded-lg bg-info-bg px-4 py-4 sm:px-4">
      <span className="inline-flex size-9 shrink-0 items-center justify-center rounded-full bg-card text-info">
        <Headset size={18} aria-hidden />
      </span>
      <div className="min-w-0">
        <p className="text-body font-semibold text-ink">
          {agentName ? "You're now chatting with a person" : "Waiting for the IT Service Desk"}
        </p>
        <p className="text-caption text-body">
          {agentName ? `${agentName} (IT Service Desk) joined · ` : ""}Ticket {ticketNumber}
          {jiraKey ? ` → ${jiraKey}` : ""} · {priority}, first reply within {reply}
        </p>
      </div>
    </div>
  );
}

export function SystemLine({ children }: { children: ReactNode }) {
  return (
    <div className="flex justify-center">
      <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-1 text-caption text-body">
        <span aria-hidden className="size-1.5 rounded-full bg-current" />
        {children}
      </span>
    </div>
  );
}

export function ErrorLine({ content, onRetry }: { content: string; onRetry?: () => void }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-danger-bg bg-card p-4" role="alert">
      <ShieldAlert size={18} className="mt-0.5 shrink-0 text-danger" aria-hidden />
      <div className="flex flex-1 flex-col gap-2">
        <p className="text-body text-ink">{content}</p>
        {onRetry && (
          <Button variant="secondary" size="sm" className="self-start" icon={<RotateCcw size={14} aria-hidden />} onClick={onRetry}>
            Try again
          </Button>
        )}
      </div>
    </div>
  );
}

export function EscalationOffer({ onEscalate, busy }: { onEscalate: () => void; busy?: boolean }) {
  return (
    <div className={cx("flex flex-wrap items-center gap-3 rounded-md bg-softer px-3 py-2")}>
      <span className="text-label font-medium text-body">Not what you needed?</span>
      <Button variant="secondary" size="sm" icon={<Headset size={14} aria-hidden />} onClick={onEscalate} disabled={busy}>
        Talk to a person
      </Button>
    </div>
  );
}
