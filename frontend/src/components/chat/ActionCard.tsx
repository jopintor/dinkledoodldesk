"use client";

// Figma "Action confirmation" (4:94): shown before DinkDesk runs any tool. The user must
// confirm – DinkDesk never acts silently. Also covers the steps after confirming (OTP entry,
// success, cancelled, failed) so the whole tool call lives in one card.
import { CheckCircle2, Headset, Lock, Ticket, Wrench, XCircle } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Button, ErrorNote, Spinner, cx } from "@/components/ui";
import { ApiError, cancelToolCall, confirmToolCall, verifyToolCall } from "@/lib/api";
import type { ToolCall } from "@/lib/types";

type Describe = {
  title: string;
  body: string;
  confirmLabel: string;
  icon: typeof Lock;
  rows: [string, string][];
};

const ROW_LABELS: Record<string, string> = {
  account: "Account",
  code_goes_to: "Code goes to",
  signs_out_of: "Signs you out of",
  summary: "Summary",
  priority: "Priority",
  club_code: "Branch",
  affected_system: "System",
};

function describe(call: ToolCall): Describe {
  const args = call.arguments ?? {};
  const rows = Object.entries(args)
    .filter(([, v]) => v !== null && v !== undefined && v !== "")
    .map(([k, v]) => [ROW_LABELS[k] ?? k.replace(/_/g, " "), Array.isArray(v) ? v.join(", ") : String(v)] as [string, string]);
  if (call.tool_name === "reset_password") {
    return {
      title: call.confirm_text ?? "Reset your StaffID password?",
      body: "This also resets your CourtBook Admin and HubMail sign-in, because they all use StaffID. Your new password is never shown in chat.",
      confirmLabel: "Yes, send the code",
      icon: Lock,
      rows,
    };
  }
  if (call.tool_name === "create_ticket") {
    return {
      title: call.confirm_text ?? "Create an IT ticket?",
      body: "The IT Service Desk gets this chat with the ticket, so you won't need to repeat yourself.",
      confirmLabel: "Yes, create it",
      icon: Ticket,
      rows,
    };
  }
  return {
    title: call.confirm_text ?? `Run ${call.tool_name.replace(/_/g, " ")}?`,
    body: "DinkDesk needs your OK before it does this.",
    confirmLabel: "Yes, go ahead",
    icon: Wrench,
    rows,
  };
}

export function ActionCard({
  call,
  onChange,
  onEscalate,
}: {
  call: ToolCall;
  onChange: (call: ToolCall) => void;
  onEscalate: () => void;
}) {
  const d = describe(call);
  const [busy, setBusy] = useState<"confirm" | "cancel" | "verify" | null>(null);
  const [otp, setOtp] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function run(kind: "confirm" | "cancel" | "verify", fn: () => Promise<ToolCall>) {
    setBusy(kind);
    setError(null);
    try {
      const next = await fn();
      onChange({ ...call, ...next });
      setOtp("");
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(null);
    }
  }

  function onVerify(e: FormEvent) {
    e.preventDefault();
    if (!/^\d{6}$/.test(otp)) {
      setError("Enter the 6-digit code from the text message.");
      return;
    }
    void run("verify", () => verifyToolCall(call.id, otp));
  }

  const Icon = d.icon;
  const done = call.status === "succeeded" || call.status === "cancelled" || call.status === "failed";

  return (
    <section
      aria-label={`Action: ${call.tool_name}`}
      className="flex w-full max-w-[520px] flex-col gap-4 rounded-lg border border-line bg-card p-5 shadow-card"
    >
      <div className="flex items-center gap-3">
        <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-md bg-ball-soft text-ink">
          <Icon size={20} aria-hidden />
        </span>
        <div className="min-w-0">
          <p className="text-overline text-subtle">Action · {call.tool_name}</p>
          <p className="text-h3 text-ink">{d.title}</p>
        </div>
      </div>

      {call.status === "awaiting_confirmation" && (
        <>
          <p className="text-body text-body">{d.body}</p>
          {d.rows.length > 0 && (
            <dl className="flex flex-col gap-2 rounded-md bg-muted p-3">
              {d.rows.map(([label, value]) => (
                <div key={label} className="flex gap-3">
                  <dt className="w-[110px] shrink-0 text-caption text-subtle">{label}</dt>
                  <dd className="text-label text-ink">{value}</dd>
                </div>
              ))}
            </dl>
          )}
          {error && <ErrorNote>{error}</ErrorNote>}
          <div className="flex flex-wrap gap-3">
            <Button
              onClick={() => run("confirm", () => confirmToolCall(call.id))}
              disabled={!!busy}
              icon={busy === "confirm" ? <Spinner /> : undefined}
            >
              {d.confirmLabel}
            </Button>
            <Button
              variant="secondary"
              onClick={() => run("cancel", () => cancelToolCall(call.id))}
              disabled={!!busy}
            >
              Not now
            </Button>
          </div>
        </>
      )}

      {call.status === "awaiting_verification" && (
        <form onSubmit={onVerify} className="flex flex-col gap-3">
          <p className="text-body text-body">{call.message}</p>
          <label className="flex flex-col gap-2">
            <span className="text-label text-ink">6-digit code</span>
            <input
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
              className="w-40 rounded-md border border-line-strong bg-card px-4 py-3 text-body-lg tracking-[0.3em] text-ink outline-none focus:border-primary"
              aria-describedby="otp-help"
            />
          </label>
          <p id="otp-help" className="text-caption text-subtle">
            The code goes straight to the reset service – DinkDesk never sees it in the chat.
          </p>
          {error && <ErrorNote>{error}</ErrorNote>}
          <div className="flex flex-wrap gap-3">
            <Button type="submit" disabled={!!busy} icon={busy === "verify" ? <Spinner /> : undefined}>
              Verify code
            </Button>
            <Button variant="secondary" onClick={onEscalate} icon={<Headset size={18} aria-hidden />}>
              Code didn&apos;t arrive
            </Button>
          </div>
        </form>
      )}

      {call.status === "awaiting_approval" && <p className="text-body text-body">{call.message}</p>}

      {done && (
        <p
          className={cx(
            "flex items-start gap-2 rounded-md px-3 py-2 text-body",
            call.status === "succeeded" && "bg-success-bg text-success",
            call.status === "cancelled" && "bg-muted text-body",
            call.status === "failed" && "bg-danger-bg text-danger",
          )}
        >
          {call.status === "succeeded" ? (
            <CheckCircle2 size={18} className="mt-0.5 shrink-0" aria-hidden />
          ) : (
            <XCircle size={18} className="mt-0.5 shrink-0" aria-hidden />
          )}
          <span>{call.message ?? (call.status === "cancelled" ? "Cancelled – nothing was changed." : "Done.")}</span>
        </p>
      )}
      {call.status === "failed" && (
        <Button variant="secondary" className="self-start" onClick={onEscalate} icon={<Headset size={18} aria-hidden />}>
          Talk to a person
        </Button>
      )}
    </section>
  );
}
