export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: unknown,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const base = "/api/backend";
  let response: Response;
  try {
    response = await fetch(`${base.replace(/\/$/, "")}${path}`, {
      ...init,
      credentials: "include",
      cache: "no-store",
      signal: init.signal ?? AbortSignal.timeout(12000),
      headers: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...init.headers,
      },
    });
  } catch {
    throw new Error(
      "Le service est injoignable. Vérifiez votre connexion puis réessayez.",
    );
  }
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail = body && typeof body === "object" && "detail" in body
      ? body.detail : undefined;
    throw new ApiError(
      response.status,
      response.status === 401
        ? "Votre session a expiré. Reconnectez-vous."
        : response.status === 403
          ? "Vous ne disposez pas des autorisations nécessaires."
          : "Le service n’a pas pu traiter la demande. Réessayez dans un instant.",
      detail,
    );
  }
  return response.json() as Promise<T>;
}
