"use client";

// Figma screen 06: Admin – KPI dashboard.
import { ChevronDown, Clock, Upload } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/shell";
import { Badge, Button, ErrorNote, FullPageLoading, Spinner, cx, type Tone } from "@/components/ui";
import { getMetricsSummary, listGuardrailEvents } from "@/lib/api";
import { useRequireRole } from "@/lib/auth";
import { formatClock } from "@/lib/format";
import type { GuardrailEvent, MetricsSummary, Role, User } from "@/lib/types";

const ROLES: Role[] = ["admin"];
const PERIODS = [7, 15, 30] as const;

export default function AdminPage() {
  const user = useRequireRole(ROLES);
  if (!user) return <FullPageLoading />;
  return <Dashboard user={user} />;
}

function isoDay(d: Date) {
  return d.toISOString().slice(0, 10);
}

function Dashboard({ user }: { user: User }) {
  const [days, setDays] = useState<(typeof PERIODS)[number]>(15);
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const to = new Date();
    const from = new Date(Date.now() - (days - 1) * 86_400_000);
    let cancelled = false;
    getMetricsSummary(isoDay(from), isoDay(to))
      .then((s) => !cancelled && setSummary(s))
      .catch((err: Error) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [days]);

  const period = summary
    ? `${new Date(summary.period.from).toLocaleDateString("en-US", { month: "short", day: "numeric" })} – ${new Date(
        summary.period.to,
      ).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`
    : "";

  return (
    <AppShell user={user}>
      <main className="flex flex-col gap-6 px-4 py-6 sm:px-8 lg:py-10">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-h1 text-ink">IT dashboard</h1>
            <p className="text-body-lg text-body">PickleHub Clubs · all branches{period && ` · ${period}`}</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <label className="relative inline-flex items-center rounded-md border border-line-strong bg-card">
              <Clock size={16} className="pointer-events-none absolute left-3.5 text-body" aria-hidden />
              <span className="sr-only">Period</span>
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value) as (typeof PERIODS)[number])}
                className="appearance-none bg-transparent py-2.5 pr-10 pl-10 text-label text-ink outline-none"
              >
                {PERIODS.map((p) => (
                  <option key={p} value={p}>
                    Last {p} days
                  </option>
                ))}
              </select>
              <ChevronDown size={16} className="pointer-events-none absolute right-3.5 text-body" aria-hidden />
            </label>
            <Button variant="secondary" icon={<Upload size={18} aria-hidden />} onClick={() => summary && exportCsv(summary)} disabled={!summary}>
              Export CSV
            </Button>
          </div>
        </header>

        {error && <ErrorNote>{error}</ErrorNote>}
        {!summary && !error && <Spinner className="text-primary" />}

        {summary && (
          <>
            <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Key numbers">
              <Kpi
                label="Ticket deflection"
                value={`${Math.round(summary.deflection_rate * 100)}%`}
                delta={summary.previous && deltaPts(summary.deflection_rate, summary.previous.deflection_rate)}
                good={!summary.previous || summary.deflection_rate >= summary.previous.deflection_rate}
                note={`vs previous ${days} days · target ≥ 60%`}
              />
              <Kpi
                label="Avg resolution (MTTR)"
                value={`${summary.mttr_hours.toFixed(1)} h`}
                delta={summary.previous && arrow(summary.mttr_hours - summary.previous.mttr_hours, (v) => `${Math.abs(v).toFixed(1)} h`)}
                good={!summary.previous || summary.mttr_hours <= summary.previous.mttr_hours}
                note={summary.previous && summary.mttr_hours <= summary.previous.mttr_hours ? "faster than previous period" : "slower than previous period"}
              />
              <Kpi
                label="P95 response latency"
                value={`${(summary.latency_ms.p95 / 1000).toFixed(1)} s`}
                delta={summary.previous && arrow((summary.latency_ms.p95 - summary.previous.p95_ms) / 1000, (v) => `${Math.abs(v).toFixed(1)} s`)}
                good={!summary.previous || summary.latency_ms.p95 <= summary.previous.p95_ms}
                note={`p50 ${(summary.latency_ms.p50 / 1000).toFixed(1)} s · target under 5 s`}
              />
              <Kpi
                label="Faithfulness score"
                value={summary.latest_eval ? summary.latest_eval.faithfulness.toFixed(2) : "–"}
                delta={
                  summary.latest_eval && summary.previous_eval
                    ? arrow(summary.latest_eval.faithfulness - summary.previous_eval.faithfulness, (v) => Math.abs(v).toFixed(2))
                    : undefined
                }
                good
                note={summary.latest_eval ? `eval run ${summary.latest_eval.label} · ${summary.latest_eval.questions ?? 50} questions` : "no eval run yet"}
              />
            </section>

            <section className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_400px]">
              <CategoryCard summary={summary} days={days} />
              <EvalCard summary={summary} />
            </section>

            <GuardrailCard summary={summary} />
          </>
        )}
      </main>
    </AppShell>
  );
}

function deltaPts(now: number, before: number) {
  return arrow((now - before) * 100, (v) => `${Math.abs(Math.round(v))} pts`);
}

function arrow(diff: number, fmt: (v: number) => string) {
  return `${diff >= 0 ? "▲" : "▼"} ${fmt(diff)}`;
}

function Card({ children, className, id }: { children: React.ReactNode; className?: string; id?: string }) {
  return (
    <div id={id} className={cx("rounded-xl border border-line bg-card p-6 shadow-card", className)}>
      {children}
    </div>
  );
}

function Kpi({ label, value, delta, good, note }: { label: string; value: string; delta?: string; good: boolean; note: string }) {
  return (
    <Card className="flex flex-col gap-3 p-5">
      <p className="text-overline text-body">{label}</p>
      <p className="text-metric text-ink">{value}</p>
      <div className="flex items-center gap-2.5">
        {delta && <Badge tone={good ? "success" : "warning"}>{delta}</Badge>}
        <span className="text-caption text-body">{note}</span>
      </div>
    </Card>
  );
}

function CategoryCard({ summary, days }: { summary: MetricsSummary; days: number }) {
  const rows = summary.tickets_by_category ?? [];
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <Card className="flex flex-col gap-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-h3 text-ink">Tickets by category</h2>
          <p className="text-caption text-body">
            {summary.tickets_created ?? rows.reduce((n, r) => n + r.count, 0)} tickets created · {summary.conversations} conversations
          </p>
        </div>
        <Badge tone="neutral">Last {days} days</Badge>
      </div>
      {rows.length === 0 ? (
        <p className="text-body text-subtle">No tickets in this period.</p>
      ) : (
        <ul className="flex flex-col gap-4">
          {rows.map((r, i) => (
            <li key={r.category} className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1 sm:grid-cols-[180px_1fr_32px]">
              <span className="text-body text-ink">{r.label}</span>
              <span className="order-3 col-span-2 h-2.5 overflow-hidden rounded-full bg-muted sm:order-none sm:col-span-1">
                <span
                  className={cx("block h-full rounded-full", i === 0 ? "bg-primary" : "bg-sage")}
                  style={{ width: `${(r.count / max) * 96}%` }}
                />
              </span>
              <span className="text-right text-body font-semibold text-ink">{r.count}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function EvalCard({ summary }: { summary: MetricsSummary }) {
  const ev = summary.latest_eval;
  const prev = summary.previous_eval;
  return (
    <Card id="eval" className="flex scroll-mt-6 flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-h3 text-ink">RAG eval scorecard</h2>
          <p className="text-caption text-body">
            Golden set · {ev?.questions ?? 50} questions{ev?.ran_at ? ` · ${new Date(ev.ran_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}` : ""}
          </p>
        </div>
        {ev && <Badge tone="brand">{ev.label}</Badge>}
      </div>
      {!ev ? (
        <p className="text-body text-subtle">No evaluation run imported yet.</p>
      ) : (
        <ul className="flex flex-col gap-4">
          <Score label="Faithfulness" value={ev.faithfulness} prev={prev && `${prev.label}: ${prev.faithfulness.toFixed(2)}`} />
          <Score label="Answer relevance" value={ev.answer_relevance} prev={prev && `${prev.label}: ${prev.answer_relevance.toFixed(2)}`} />
          <Score label="Context precision" value={ev.context_precision} prev={prev && `${prev.label}: ${prev.context_precision.toFixed(2)}`} />
          {ev.malicious_total ? (
            <Score
              label="Malicious prompts blocked"
              value={(ev.malicious_blocked ?? 0) / ev.malicious_total}
              display={`${ev.malicious_blocked} / ${ev.malicious_total}`}
              prev={prev?.malicious_total && prev.malicious_blocked === ev.malicious_blocked ? `same as ${prev.label}` : prev && `${prev.label}: ${prev.malicious_blocked} / ${prev.malicious_total}`}
            />
          ) : null}
        </ul>
      )}
    </Card>
  );
}

function Score({ label, value, prev, display }: { label: string; value: number; prev?: string | false; display?: string }) {
  return (
    <li className="flex flex-col gap-1.5">
      <div className="flex justify-between text-body text-ink">
        <span>{label}</span>
        <span className="font-semibold">{display ?? value.toFixed(2)}</span>
      </div>
      <span className="h-2 overflow-hidden rounded-full bg-muted">
        <span className="block h-full rounded-full bg-primary" style={{ width: `${Math.min(1, value) * 100}%` }} />
      </span>
      {prev && <span className="text-caption text-body">{prev}</span>}
    </li>
  );
}

const EVENT_LABEL: Record<string, { type: string; action: string; tone: Tone }> = {
  prompt_injection: { type: "Prompt injection", action: "Blocked", tone: "danger" },
  pii_redacted: { type: "PII redacted", action: "Redacted", tone: "warning" },
  rbac_denied: { type: "Access denied (RBAC)", action: "Denied", tone: "info" },
};

function GuardrailCard({ summary }: { summary: MetricsSummary }) {
  const [events, setEvents] = useState<GuardrailEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const poll = useCallback(async () => {
    try {
      const res = await listGuardrailEvents();
      setEvents(res.items);
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- live feed, polled every 2 s (docs/api.md #36)
    void poll();
    const t = setInterval(poll, 2000);
    return () => clearInterval(t);
  }, [poll]);

  const g = summary.guardrail_blocks;
  return (
    <Card id="guardrails" className="flex scroll-mt-6 flex-col gap-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-h3 text-ink">Guardrail events</h2>
          <p className="text-caption text-body">Live feed · refreshes every 2 s · used in the “Try to break DinkDesk” demo</p>
        </div>
        {g && (
          <div className="flex flex-wrap gap-2">
            <Badge tone="danger">{g.prompt_injection} blocked</Badge>
            <Badge tone="warning">{g.pii_redacted} PII redacted</Badge>
            <Badge tone="info">{g.rbac_denied} access denied</Badge>
          </div>
        )}
      </div>
      {error && <ErrorNote>{error}</ErrorNote>}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] border-separate border-spacing-0 text-left">
          <thead>
            <tr className="text-overline text-body">
              <th className="rounded-l-md bg-muted px-3 py-3 font-bold">Time</th>
              <th className="bg-muted px-3 py-3 font-bold">Type</th>
              <th className="bg-muted px-3 py-3 font-bold">Role</th>
              <th className="bg-muted px-3 py-3 font-bold">Action</th>
              <th className="rounded-r-md bg-muted px-3 py-3 font-bold">What was sent (redacted)</th>
            </tr>
          </thead>
          <tbody>
            {(events ?? []).map((ev) => {
              const l = EVENT_LABEL[ev.type] ?? { type: ev.type, action: ev.action, tone: "neutral" as Tone };
              return (
                <tr key={ev.id} className="text-body text-ink">
                  <td className="border-b border-line px-3 py-4 font-semibold">{formatClock(ev.created_at)}</td>
                  <td className="border-b border-line px-3 py-4 font-medium">{l.type}</td>
                  <td className="border-b border-line px-3 py-4">{ev.user.role}</td>
                  <td className="border-b border-line px-3 py-4">
                    <Badge tone={l.tone}>{l.action}</Badge>
                  </td>
                  <td className="border-b border-line px-3 py-4 text-body">{ev.excerpt ? `“${ev.excerpt}”` : "–"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {events?.length === 0 && <p className="px-3 py-6 text-body text-subtle">No guardrail events yet.</p>}
      </div>
    </Card>
  );
}

function exportCsv(s: MetricsSummary) {
  const rows: (string | number)[][] = [
    ["metric", "value"],
    ["period_from", s.period.from],
    ["period_to", s.period.to],
    ["conversations", s.conversations],
    ["deflection_rate", s.deflection_rate],
    ["escalation_rate", s.escalation_rate],
    ["automation_success_rate", s.automation_success_rate],
    ["mttr_hours", s.mttr_hours],
    ["latency_p50_ms", s.latency_ms.p50],
    ["latency_p95_ms", s.latency_ms.p95],
    ["cache_hit_rate", s.cache_hit_rate],
    ["csat", s.csat],
    ...Object.entries(s.tool_calls).map(([k, v]) => [`tool_calls.${k}`, v]),
    ...(s.tickets_by_category ?? []).map((c) => [`tickets.${c.category}`, c.count]),
    ...(s.latest_eval
      ? [
          ["eval.label", s.latest_eval.label],
          ["eval.faithfulness", s.latest_eval.faithfulness],
          ["eval.answer_relevance", s.latest_eval.answer_relevance],
          ["eval.context_precision", s.latest_eval.context_precision],
        ]
      : []),
  ];
  const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = `dinkdesk-kpis-${s.period.from}-to-${s.period.to}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
