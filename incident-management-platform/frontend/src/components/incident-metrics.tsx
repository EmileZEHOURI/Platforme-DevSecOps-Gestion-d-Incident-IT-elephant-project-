"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { subscribeIncidentUpdates } from "@/lib/incident-updates";
import { getIncidentMetrics, type IncidentMetrics as Metrics } from "@/services/incident.service";
import type { User } from "@/types/auth";

const cards = [
  ["open", "Incidents ouverts", "À prendre en charge"],
  ["inProgress", "En cours", "Suivi des interventions"],
  ["criticalActive", "Critiques actifs", "Priorité critique · ouverts ou en cours"],
  ["resolved", "Résolus", "Résolus uniquement · hors incidents clos"],
] as const;

function MetricsForUser({ user }: { user: User }) {
  const [data, setData] = useState<Metrics>();
  const [error, setError] = useState<Error>();
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    let controller: AbortController | undefined;
    let sessionExpired = false;
    async function load() {
      if (!active || sessionExpired) return;
      controller?.abort();
      const request = new AbortController();
      controller = request;
      setData(undefined);
      setError(undefined);
      try {
        const result = await getIncidentMetrics(user.role, request.signal);
        if (active && !request.signal.aborted) setData(result);
      } catch (reason) {
        if (!active || request.signal.aborted) return;
        sessionExpired = reason instanceof ApiError && reason.status === 401;
        setError(reason instanceof Error ? reason : new Error("Impossible de charger les indicateurs."));
      }
    }
    void Promise.resolve().then(load);
    const unsubscribe = subscribeIncidentUpdates(() => { void load(); });
    const onFocus = () => { if (document.visibilityState === "visible") void load(); };
    window.addEventListener("focus", onFocus);
    return () => { active = false; controller?.abort(); unsubscribe(); window.removeEventListener("focus", onFocus); };
  }, [user.role, attempt]);
  const expired = error instanceof ApiError && error.status === 401;
  return <section aria-label="Indicateurs des incidents" aria-busy={!data && !error}>
    <div className="metric-grid">{cards.map(([key, title, subtitle], index) =>
      <section className="metric" key={key} aria-label={title}>
        <div><span className={"metric-dot dot-" + index} aria-hidden="true" />{title}</div>
        <strong aria-label={data ? undefined : error ? "Donnée indisponible" : "Chargement"}>{data ? data[key] : "—"}</strong>
        <p>{subtitle}</p>
      </section>
    )}</div>
    <div className="data-note flex flex-wrap items-center justify-between gap-2">
      {error ? <p role="alert">{expired ? "Session expirée. Reconnectez-vous pour consulter les indicateurs." : "Impossible de charger les indicateurs. Réessayez."}</p>
        : !data ? <p role="status">Chargement des indicateurs…</p>
          : <p>{user.role === "ADMIN" ? "Tous les incidents de la plateforme." : user.role === "TECHNICIAN" ? "Vos incidents affectés." : "Vos incidents déclarés."} Les critiques actifs peuvent aussi être ouverts ou en cours.</p>}
      {expired ? <Link className="incident-detail-link" href="/login?next=%2Fdashboard">Se reconnecter</Link>
        : <Button variant="ghost" disabled={!data && !error} onClick={() => setAttempt(n => n + 1)}>{error ? "Réessayer les indicateurs" : "Actualiser les indicateurs"}</Button>}
    </div>
  </section>;
}

export function IncidentMetrics() {
  const { user } = useAuth();
  return user ? <MetricsForUser key={user.id + ":" + user.role} user={user} /> : null;
}
