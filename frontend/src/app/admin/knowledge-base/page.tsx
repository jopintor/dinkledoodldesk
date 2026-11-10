"use client";

// Figma screen 07: Admin – Knowledge base.
import { ArrowRight, Check, RefreshCw, Search, Upload } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/shell";
import { Badge, Button, ErrorNote, FullPageLoading, Spinner, cx } from "@/components/ui";
import { getReindexJob, listKbDocuments, startReindex, uploadKbDocument } from "@/lib/api";
import { useRequireRole } from "@/lib/auth";
import { CATEGORY_LABEL, audienceLabel, formatDate } from "@/lib/format";
import type { KbDocumentList, ReindexJob, Role, User } from "@/lib/types";

const ROLES: Role[] = ["agent", "admin"];
const PAGE = 12;
const FILTERS = [
  ["all", "All"],
  ["accounts-access", "Accounts & access"],
  ["pos-payments", "POS & payments"],
  ["network", "Network"],
  ["member-app-booking", "Member app"],
  ["support-process", "Support"],
] as const;

export default function KbPage() {
  const user = useRequireRole(ROLES);
  if (!user) return <FullPageLoading />;
  return <KnowledgeBase user={user} />;
}

function KnowledgeBase({ user }: { user: User }) {
  const [data, setData] = useState<KbDocumentList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<string>("all");
  const [page, setPage] = useState(0);
  const [job, setJob] = useState<ReindexJob | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const isAdmin = user.role === "admin";

  const load = useCallback(async () => {
    try {
      setData(await listKbDocuments());
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial fetch
    void load();
  }, [load]);

  useEffect(() => {
    if (!job?.job_id || job.status === "done" || job.status === "failed") return;
    const t = setInterval(async () => {
      try {
        const next = await getReindexJob(job.job_id!);
        setJob({ ...next, job_id: job.job_id });
        if (next.status === "done") {
          setNotice(`Re-index finished: ${next.docs_total} documents, ${next.chunks_embedded} chunks.`);
          void load();
        }
      } catch (err) {
        setError((err as Error).message);
        setJob(null);
      }
    }, 500);
    return () => clearInterval(t);
  }, [job, load]);

  async function onUpload(file: File) {
    setError(null);
    try {
      const res = await uploadKbDocument(file);
      setNotice(`${res.doc_id} uploaded. Re-index to make it searchable.`);
      void load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const docs = data?.items ?? [];
  const q = query.trim().toLowerCase();
  const filtered = docs.filter(
    (d) => (filter === "all" || d.category === filter) && (!q || d.id.toLowerCase().includes(q) || d.title.toLowerCase().includes(q)),
  );
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE));
  const shown = filtered.slice(page * PAGE, page * PAGE + PAGE);
  const changed = docs.filter((d) => d.status === "changed");
  const chunks = docs.reduce((n, d) => n + d.chunk_count, 0);
  const running = job && job.status !== "done" && job.status !== "failed";

  return (
    <AppShell user={user}>
      <main className="flex flex-col gap-6 px-4 py-6 sm:px-8 lg:py-10">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-h1 text-ink">Knowledge base</h1>
            <p className="text-body-lg text-body">
              {docs.length} documents · {chunks} chunks · DinkDesk only answers from these guides
            </p>
          </div>
          {isAdmin && (
            <div className="flex flex-wrap gap-3">
              <input
                ref={fileRef}
                type="file"
                accept=".md,text/markdown"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void onUpload(f);
                  e.target.value = "";
                }}
              />
              <Button variant="secondary" icon={<Upload size={18} aria-hidden />} onClick={() => fileRef.current?.click()}>
                Upload document
              </Button>
              <Button
                icon={running ? <Spinner /> : <RefreshCw size={18} aria-hidden />}
                disabled={!!running}
                onClick={async () => {
                  setNotice(null);
                  try {
                    setJob(await startReindex("full"));
                  } catch (err) {
                    setError((err as Error).message);
                  }
                }}
              >
                {running ? `Re-indexing ${job?.docs_done ?? 0}/${job?.docs_total ?? docs.length}` : "Re-index all"}
              </Button>
            </div>
          )}
        </header>

        {data && (
          <div className="flex flex-wrap items-center gap-4 rounded-xl border border-line bg-softer px-4 py-4">
            <span className="inline-flex size-10 items-center justify-center rounded-md bg-soft text-primary">
              <Check size={20} aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-body font-semibold text-ink">
                Index is up to date{changed.length ? ` (${changed.length} change${changed.length > 1 ? "s" : ""} waiting)` : ""}
              </p>
              {data.last_reindex && (
                <p className="text-caption text-body">
                  Last re-index {formatDate(data.last_reindex.at)},{" "}
                  {new Date(data.last_reindex.at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })} by{" "}
                  {data.last_reindex.by} · {data.last_reindex.embedding_model} · {data.last_reindex.dims} dims · {data.last_reindex.store}
                </p>
              )}
            </div>
            {changed.map((d) => (
              <Badge key={d.id} tone="info">
                {d.id} edited since last index
              </Badge>
            ))}
          </div>
        )}
        {notice && <p className="rounded-md bg-success-bg px-3 py-2 text-label font-medium text-success">{notice}</p>}
        {error && <ErrorNote>{error}</ErrorNote>}

        <div className="flex flex-wrap items-center gap-3">
          <label className="flex w-full items-center gap-3 rounded-md border border-line-strong bg-card px-4 py-2.5 sm:w-[320px]">
            <Search size={18} className="text-body" aria-hidden />
            <span className="sr-only">Search documents</span>
            <input
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(0);
              }}
              placeholder="Search title or KB ID…"
              className="w-full bg-transparent text-body outline-none placeholder:text-subtle"
            />
          </label>
          {FILTERS.map(([key, label]) => {
            const n = key === "all" ? docs.length : docs.filter((d) => d.category === key).length;
            return (
              <button
                key={key}
                type="button"
                onClick={() => {
                  setFilter(key);
                  setPage(0);
                }}
                className={cx(
                  "rounded-full border px-3 py-1.5 text-label",
                  filter === key ? "border-primary bg-primary text-white" : "border-line-strong bg-card text-ink hover:bg-softer",
                )}
              >
                {label} {n}
              </button>
            );
          })}
        </div>

        <div className="overflow-x-auto rounded-xl border border-line bg-card p-2 shadow-card">
          {!data && !error ? (
            <div className="p-6 text-primary">
              <Spinner />
            </div>
          ) : (
            <table className="w-full min-w-[860px] border-separate border-spacing-0 text-left">
              <thead>
                <tr className="text-overline text-body">
                  {["ID", "Title", "Category", "Who can see it", "Chunks", "Updated", "Status"].map((h, i, a) => (
                    <th key={h} className={cx("bg-muted px-4 py-3 font-bold", i === 0 && "rounded-l-md", i === a.length - 1 && "rounded-r-md")}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {shown.map((d) => (
                  <tr key={d.id} className="text-body text-ink">
                    <td className="border-b border-line px-4 py-3 font-semibold">{d.id}</td>
                    <td className="max-w-[260px] border-b border-line px-4 py-3 font-medium">{d.title}</td>
                    <td className="border-b border-line px-4 py-3 text-body">{CATEGORY_LABEL[d.category] ?? d.category}</td>
                    <td className="border-b border-line px-4 py-3 text-body">{audienceLabel(d.audience_roles)}</td>
                    <td className="border-b border-line px-4 py-3 text-body">{d.chunk_count}</td>
                    <td className="border-b border-line px-4 py-3 text-body">{formatDate(d.last_updated)}</td>
                    <td className="border-b border-line px-4 py-3">
                      {d.status === "superseded" ? (
                        <Badge tone="warning">Superseded{d.superseded_by ? ` → ${d.superseded_by}` : ""}</Badge>
                      ) : d.status === "changed" ? (
                        <Badge tone="info">Changed – re-index</Badge>
                      ) : (
                        <Badge tone="success">Indexed</Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="flex items-center justify-between px-4 py-3">
            <span className="text-caption text-body">
              Showing {shown.length} of {filtered.length}
            </span>
            <div className="flex gap-2">
              {page > 0 && (
                <Button variant="ghost" size="sm" onClick={() => setPage((p) => p - 1)}>
                  Previous
                </Button>
              )}
              {page < pages - 1 && (
                <Button variant="ghost" size="sm" icon={<ArrowRight size={16} aria-hidden />} onClick={() => setPage((p) => p + 1)}>
                  Next page
                </Button>
              )}
            </div>
          </div>
        </div>
      </main>
    </AppShell>
  );
}
