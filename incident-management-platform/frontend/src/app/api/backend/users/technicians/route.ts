import { cookies } from "next/headers";

// Bridge the older /auth mount only after checking the session on FastAPI.
export async function GET() {
  const token = (await cookies()).get("access_token");
  const base = (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL)?.replace(/\/$/, "");
  const fail = (status: number) => Response.json({ detail: "Annuaire indisponible." }, { status, headers: { "Cache-Control": "no-store" } });
  if (!token) return fail(401);
  if (!base) return fail(503);
  const options: RequestInit = { cache: "no-store", redirect: "error", signal: AbortSignal.timeout(10000), headers: { cookie: `access_token=${encodeURIComponent(token.value)}` } };
  try {
    const session = await fetch(base + "/auth/me", options);
    if (!session.ok) return fail(session.status);
    const user = await session.json();
    if (user.role !== "ADMIN" || !user.is_active) return fail(403);
    let result = await fetch(base + "/users/technicians", options);
    if (result.status === 404) result = await fetch(base + "/auth/technicians", options);
    if (!result.ok) return fail(result.status);
    return Response.json(await result.json(), { headers: { "Cache-Control": "private, no-store" } });
  } catch { return fail(503); }
}
