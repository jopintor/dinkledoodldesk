"use client";

import { useEffect, useState } from "react";

import { API_BASE_URL, apiGet, type HealthResponse } from "@/lib/api";

// Placeholder home page: proves the frontend can reach the API.
// Replace with the chat widget / dashboards from the Figma designs.
export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<HealthResponse>("/health")
      .then(setHealth)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center gap-4 px-6 font-sans">
      <h1 className="text-3xl font-semibold">DinkDesk</h1>
      <p className="text-zinc-600 dark:text-zinc-400">AI IT helpdesk for PickleHub Clubs.</p>
      <section className="rounded-lg border border-zinc-200 p-4 text-sm dark:border-zinc-800">
        <p>
          API: <code>{API_BASE_URL}</code>
        </p>
        {health && (
          <p className="text-green-700 dark:text-green-400">
            Backend {health.status} (v{health.version}, env {health.env}, LLM {health.llm_provider}
            {health.llm_configured ? "" : ", no API key"})
          </p>
        )}
        {error && <p className="text-red-700 dark:text-red-400">Backend unreachable: {error}</p>}
        {!health && !error && <p>Checking backend…</p>}
      </section>
    </main>
  );
}
