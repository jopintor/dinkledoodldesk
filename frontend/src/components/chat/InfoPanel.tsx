"use client";

// Right-hand "Info panel" on the chat screens: Service status + My tickets.
import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Badge, Spinner, cx } from "@/components/ui";
import { getServiceStatus, listTickets } from "@/lib/api";
import { SERVICE_STATE, TICKET_STATUS } from "@/lib/format";
import type { ServiceStatus, Ticket } from "@/lib/types";

export function InfoPanel({ refreshKey }: { refreshKey: number }) {
  const [services, setServices] = useState<ServiceStatus[] | null>(null);
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [minutes, setMinutes] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, t] = await Promise.all([getServiceStatus(), listTickets({ limit: 5 })]);
      setServices(s.items);
      const updated = s.items[0]?.updated_at;
      setMinutes(updated ? Math.max(0, Math.round((Date.now() - Date.parse(updated)) / 60000)) : null);
      setTickets(t.items);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch on mount and when a ticket is created
    void load();
  }, [load, refreshKey]);


  return (
    <aside className="flex h-full flex-col gap-4 overflow-y-auto border-l border-line bg-card px-6 py-6" aria-label="Service status and tickets">
      <div className="flex items-center justify-between">
        <h2 className="text-h3 text-ink">Service status</h2>
        <button
          type="button"
          onClick={() => void load()}
          aria-label="Refresh service status"
          className="rounded-sm p-1 text-subtle hover:bg-muted hover:text-ink"
        >
          {loading ? <Spinner className="size-4" /> : <RefreshCw size={16} aria-hidden />}
        </button>
      </div>
      {error && <p className="text-caption text-danger">{error}</p>}
      <ul className="flex flex-col">
        {(services ?? []).map((s) => {
          const st = SERVICE_STATE[s.status];
          return (
            <li key={`${s.service_key}-${s.club_code ?? ""}`} className="flex min-h-12 items-center justify-between gap-2" title={s.message ?? undefined}>
              <span className="text-body text-ink">{s.display_name}</span>
              <Badge tone={st.tone}>{st.label}</Badge>
            </li>
          );
        })}
      </ul>
      {minutes !== null && (
        <p className="-mt-2 text-caption text-subtle">
          From status.picklehub.example · updated {minutes <= 1 ? "just now" : `${minutes} min ago`}
        </p>
      )}

      <h2 className="mt-2 text-h3 text-ink">My tickets</h2>
      {tickets && tickets.length === 0 && <p className="text-body text-subtle">No tickets yet.</p>}
      <ul className="flex flex-col gap-3">
        {(tickets ?? []).map((t) => {
          const st = TICKET_STATUS[t.status];
          return (
            <li key={t.id} className={cx("flex flex-col gap-2 rounded-md border border-line bg-page p-3")}>
              <div className="flex items-center justify-between gap-2">
                <span className="text-label font-medium text-subtle">{t.jira_key ?? t.ticket_number}</span>
                <Badge tone={st.tone}>{st.label}</Badge>
              </div>
              <p className="text-body font-semibold text-ink">{t.summary}</p>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
