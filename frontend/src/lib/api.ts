// Base URL of the DinkDesk API, set in `.env.local` (see `.env.example`):
//   http://localhost:8000          -> backend running locally / in Docker
//   https://<tunnel>.trycloudflare.com -> Jose's PC via Cloudflare Tunnel
//   /mock-api                      -> built-in mock routes, no backend needed
export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

export type HealthResponse = {
  status: string;
  version: string;
  env: string;
  llm_provider: string;
  llm_configured: boolean;
};

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, cache: "no-store" });
  if (!res.ok) {
    throw new Error(`GET ${path} failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}
