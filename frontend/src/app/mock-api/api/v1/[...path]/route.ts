// Built-in mock of the DinkDesk API at /mock-api/api/v1/*. All logic lives in
// src/lib/mock/server.ts; this file only forwards every method to it.
import { handleMock } from "@/lib/mock/server";

type Ctx = { params: Promise<{ path: string[] }> };

async function handle(req: Request, ctx: Ctx) {
  const { path } = await ctx.params;
  return handleMock(req, path);
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
