// Mock of the backend's GET /health so the UI can be built without the backend.
// Use it by setting NEXT_PUBLIC_API_BASE_URL=/mock-api in .env.local.
// Add more mock routes next to this one, mirroring the real API paths.
import type { HealthResponse } from "@/lib/api";

export async function GET() {
  const body: HealthResponse = {
    status: "ok",
    version: "mock",
    env: "mock",
    llm_provider: "gemini",
    llm_configured: false,
  };
  return Response.json(body);
}
