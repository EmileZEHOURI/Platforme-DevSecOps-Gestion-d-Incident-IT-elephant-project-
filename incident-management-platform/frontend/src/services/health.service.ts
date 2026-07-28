import type { DatabaseHealthResponse } from "@/types/health";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export async function getDatabaseHealth(): Promise<DatabaseHealthResponse> {
  if (!API_URL) {
    throw new Error("La variable NEXT_PUBLIC_API_URL est absente.");
  }

  const response = await fetch(`${API_URL}/health/database`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(
      `La vérification de l'API a échoué avec le statut ${response.status}.`,
    );
  }

  return response.json() as Promise<DatabaseHealthResponse>;
}