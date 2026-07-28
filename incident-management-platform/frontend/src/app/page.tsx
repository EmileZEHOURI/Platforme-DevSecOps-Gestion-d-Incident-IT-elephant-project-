"use client";

import { useEffect, useState } from "react";

import { getDatabaseHealth } from "@/services/health.service";
import type { DatabaseHealthResponse } from "@/types/health";

type LoadingState = "loading" | "success" | "error";

export default function Home() {
  const [health, setHealth] = useState<DatabaseHealthResponse | null>(null);
  const [state, setState] = useState<LoadingState>("loading");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    async function checkApi(): Promise<void> {
      try {
        const result = await getDatabaseHealth();

        setHealth(result);
        setState("success");
      } catch (error) {
        setErrorMessage(
          error instanceof Error
            ? error.message
            : "Une erreur inconnue est survenue.",
        );

        setState("error");
      }
    }

    void checkApi();
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 p-6">
      <section className="w-full max-w-lg rounded-xl bg-white p-8 shadow">
        <h1 className="text-2xl font-semibold text-slate-900">
          Incident Management Platform
        </h1>

        <p className="mt-2 text-sm text-slate-600">
          Vérification de la communication entre Next.js, FastAPI et PostgreSQL.
        </p>

        <div className="mt-8 rounded-lg border border-slate-200 p-5">
          {state === "loading" && (
            <p className="text-slate-600">Connexion à l’API en cours…</p>
          )}

          {state === "success" && health && (
            <div>
              <p className="font-medium text-green-700">
                Communication établie
              </p>

              <dl className="mt-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-slate-500">API</dt>
                  <dd className="font-medium text-slate-900">
                    {health.status}
                  </dd>
                </div>

                <div className="flex justify-between">
                  <dt className="text-slate-500">PostgreSQL</dt>
                  <dd className="font-medium text-slate-900">
                    {health.database}
                  </dd>
                </div>
              </dl>
            </div>
          )}

          {state === "error" && (
            <div>
              <p className="font-medium text-red-700">
                Communication impossible
              </p>

              <p className="mt-2 text-sm text-red-600">{errorMessage}</p>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}