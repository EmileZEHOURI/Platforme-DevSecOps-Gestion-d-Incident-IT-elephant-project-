"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { Button, PageHeader, StatePanel } from "@/components/ui";
import { IncidentPriorityBadge, IncidentStatusBadge } from "@/components/incident-badges";
import { getIncident } from "@/services/incident.service";
import { ApiError } from "@/lib/api";
import { incidentCategories, type IncidentResponse } from "@/types/incident";
import { IncidentComments } from "@/components/incident-comments";

type DetailState = { status: "loading" }
  | { status: "success"; incident: IncidentResponse }
  | { status: "error"; code?: number; message: string };
const dates = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long", timeStyle: "short" });

function IncidentDate({ value, fallback }: { value: string | null; fallback: string }) {
  return value ? <time dateTime={value}>{dates.format(new Date(value))}</time> : <span className="muted">{fallback}</span>;
}

function DetailContent({ id }: { id: string }) {
  const [state, setState] = useState<DetailState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    void getIncident(id, controller.signal).then(incident => {
      if (active) setState({ status: "success", incident });
    }).catch(error => {
      if (active) setState({ status: "error", code: error instanceof ApiError ? error.status : undefined,
        message: error instanceof Error ? error.message : "Le détail n’a pas pu être chargé." });
    });
    return () => { active = false; controller.abort(); };
  }, [id, attempt]);

  if (state.status === "loading") return <>
    <PageHeader title="Détail de l’incident" description="Retrouvez les informations de votre signalement." />
    <section className="panel incident-list-loading" role="status" aria-busy="true"><span className="spinner" aria-hidden="true" />Chargement de l’incident…</section>
  </>;

  if (state.status === "error") {
    const notFound = state.code === 404 || state.code === 422;
    return <>
      <PageHeader title="Détail de l’incident" description="Retrouvez les informations de votre signalement." />
      <section className="panel"><StatePanel error
        title={notFound ? "Incident introuvable ou inaccessible" : state.code === 401 ? "Session expirée" : state.code === 403 ? "Accès refusé" : "Impossible de charger l’incident"}
        description={notFound ? "Cet incident n’est pas disponible. Revenez à votre liste pour consulter vos signalements." : state.message}>
        {notFound ? <Link className="button button-secondary" href="/dashboard/incidents">Retour à mes incidents</Link>
          : state.code === 401 ? <Link className="button button-primary" href={`/login?next=${encodeURIComponent(`/dashboard/incidents/${id}`)}`}>Se reconnecter</Link>
          : <Button variant="secondary" onClick={() => { setState({ status: "loading" }); setAttempt(value => value + 1); }}>Réessayer</Button>}
      </StatePanel></section>
    </>;
  }

  const { incident } = state;
  return <>
    <PageHeader eyebrow={incident.reference} title={incident.title} description="Détail de votre signalement" action={<IncidentStatusBadge status={incident.status} />} />
    <div className="incident-detail-grid">
      <div className="incident-detail-main">
        <section className="panel" aria-labelledby="description-heading">
          <div className="panel-heading"><h2 id="description-heading">Description</h2></div>
          <p className="incident-detail-text">{incident.description}</p>
        </section>
        <section className="panel" aria-labelledby="resolution-heading">
          <div className="panel-heading"><h2 id="resolution-heading">Résolution</h2></div>
          <p className={`incident-detail-text ${incident.resolution ? "" : "muted"}`}>{incident.resolution || "Aucune résolution renseignée pour le moment."}</p>
        </section>
        <IncidentComments key={incident.id} incident={incident} />
      </div>
      <div className="incident-detail-side">
        <section className="panel" aria-labelledby="information-heading">
          <div className="panel-heading"><h2 id="information-heading">Informations</h2></div>
          <dl className="incident-detail-facts">
            <div><dt>Référence</dt><dd className="incident-reference">{incident.reference}</dd></div>
            <div><dt>Catégorie</dt><dd>{incidentCategories[incident.category]}</dd></div>
            <div><dt>Priorité</dt><dd><IncidentPriorityBadge priority={incident.priority} /></dd></div>
            <div><dt>Statut</dt><dd><IncidentStatusBadge status={incident.status} /></dd></div>
            <div><dt>Affectation</dt><dd>{incident.assigned_to_id === null ? "Non attribué" : `Utilisateur n° ${incident.assigned_to_id}`}</dd></div>
          </dl>
        </section>
        <section className="panel" aria-labelledby="dates-heading">
          <div className="panel-heading"><h2 id="dates-heading">Dates clés</h2></div>
          <dl className="incident-detail-facts">
            <div><dt>Création</dt><dd><IncidentDate value={incident.created_at} fallback="Non renseignée" /></dd></div>
            <div><dt>Dernière mise à jour</dt><dd><IncidentDate value={incident.updated_at} fallback="Non renseignée" /></dd></div>
            <div><dt>Résolution</dt><dd><IncidentDate value={incident.resolved_at} fallback="Non résolu" /></dd></div>
            <div><dt>Clôture</dt><dd><IncidentDate value={incident.closed_at} fallback="Non clôturé" /></dd></div>
          </dl>
        </section>
      </div>
    </div>
  </>;
}

export function IncidentDetail({ id }: { id: string }) {
  const { user } = useAuth();
  return user ? <DetailContent key={`${user.id}:${id}`} id={id} /> : null;
}
