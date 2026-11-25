"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { AdminError } from "@/components/assignment-controls";
import { Button, PageHeader, StatePanel } from "@/components/ui";
import { IncidentPagination } from "@/components/incident-pagination";
import { AuditDetails } from "@/components/audit-details";
import { auditDate } from "@/lib/audit-display";
import { listUsers } from "@/services/user.service";
import { listAuditLogs } from "@/services/audit.service";
import { auditEvents, auditEventLabel, auditResults, type AuditFilters, type AuditLog, type PaginatedAuditLogsResponse } from "@/types/audit";
import type { User } from "@/types/auth";

const dateError = "La date de début doit être antérieure ou égale à la date de fin.";
const descriptions = { 403: "Vous n’êtes pas autorisé à consulter les journaux d’audit.", 404: "L’utilisateur authentifié n’est plus reconnu ou accessible.", 422: "Les paramètres sont invalides. Vérifiez les filtres et l’ordre des dates de début et de fin.", 500: "Impossible de récupérer les journaux d’audit. Veuillez réessayer.", 0: "Impossible de récupérer les journaux d’audit. Veuillez réessayer." };
type Draft = { user: string; event: string; result: string; from: string; to: string };
const empty: Draft = { user: "", event: "", result: "", from: "", to: "" };
function validate(draft: Draft) {
  if (draft.user && !/^\d+$/.test(draft.user)) return "L’identifiant utilisateur doit être un entier positif ou nul.";
  if (draft.user && !Number.isSafeInteger(Number(draft.user))) return "L’identifiant utilisateur est invalide.";
  if ((draft.from && Number.isNaN(Date.parse(draft.from))) || (draft.to && Number.isNaN(Date.parse(draft.to)))) return "La date saisie est invalide.";
  return draft.from && draft.to && Date.parse(draft.from) > Date.parse(draft.to) ? dateError : "";
}
function Management() {
  const [draft, setDraft] = useState(empty); const validation = validate(draft);
  const [page, setPage] = useState(1); const [size, setSize] = useState(20); const [attempt, retry] = useState(0);
  const [data, setData] = useState<PaginatedAuditLogsResponse>(); const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null); const [selected, select] = useState<AuditLog | null>(null);
  const [users, setUsers] = useState<User[]>([]); const [directoryFailed, setDirectoryFailed] = useState(false);
  useEffect(() => { const controller = new AbortController(); let active = true;
    listUsers({}, controller.signal).then(result => { if (active) setUsers(result); }).catch(() => { if (active) setDirectoryFailed(true); });
    return () => { active = false; controller.abort(); };
  }, []);
  useEffect(() => {
    if (validation) return;
    const controller = new AbortController(); let active = true;
    const timer = setTimeout(() => {
      const filters: AuditFilters = {
        ...(draft.user !== "" ? { user_id: Number(draft.user) } : {}),
        ...(Object.hasOwn(auditEvents, draft.event) ? { event_type: draft.event as keyof typeof auditEvents } : {}),
        ...(Object.hasOwn(auditResults, draft.result) ? { result: draft.result as keyof typeof auditResults } : {}),
        ...(draft.from ? { date_from: new Date(draft.from).toISOString() } : {}),
        ...(draft.to ? { date_to: new Date(draft.to).toISOString() } : {}),
      };
      listAuditLogs(filters, page, size, controller.signal).then(result => {
        if (!active) return;
        const last = Math.max(1, result.total_pages);
        if (!result.items.length && page > last) { setPage(last); return; }
        setData(result); setLoading(false);
      }).catch(cause => { if (active) { setError(cause instanceof Error ? cause : new Error()); setLoading(false); } });
    }, 250);
    return () => { active = false; clearTimeout(timer); controller.abort(); };
  }, [draft, page, size, attempt, validation]);
  function change(next: Draft) { setDraft(next); setPage(1); setData(undefined); setError(null); setLoading(!validate(next)); }
  function refresh() { setLoading(true); setError(null); retry(n => n + 1); }
  function changePage(next: number) { setData(undefined); setPage(next); setLoading(!validation); setError(null); }
  return <>
    <PageHeader eyebrow="ADMINISTRATION" title="Journaux d’audit" description="Consultez l’historique des actions sensibles effectuées sur la plateforme." />
    <section className="panel" aria-label="Journaux d’audit" aria-busy={loading}>
      <div className="panel-heading"><h2>Événements enregistrés</h2><Button variant="ghost" disabled={loading || !!validation} onClick={refresh}>Actualiser ↻</Button></div>
      <div className="assignment-filters incident-form" role="group" aria-label="Filtres des journaux">
        <div className="field"><label htmlFor="audit-event">Événement</label><select id="audit-event" value={draft.event} onChange={e => change({ ...draft, event: e.target.value })}><option value="">Tous les événements</option>{Object.entries(auditEvents).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></div>
        <div className="field"><label htmlFor="audit-result">Résultat</label><select id="audit-result" value={draft.result} onChange={e => change({ ...draft, result: e.target.value })}><option value="">Tous les résultats</option>{Object.entries(auditResults).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></div>
        <div className="field"><label htmlFor="audit-user">Identifiant utilisateur</label><input id="audit-user" inputMode="numeric" list="audit-users" value={draft.user} onChange={e => change({ ...draft, user: e.target.value })} placeholder="Tous les utilisateurs" /><datalist id="audit-users">{users.map(user => <option key={user.id} value={user.id}>{user.full_name} — {user.email}</option>)}</datalist></div>
        <div className="field"><label htmlFor="audit-from">Date/heure de début</label><input id="audit-from" type="datetime-local" value={draft.from} onChange={e => change({ ...draft, from: e.target.value })} /></div>
        <div className="field"><label htmlFor="audit-to">Date/heure de fin</label><input id="audit-to" type="datetime-local" value={draft.to} onChange={e => change({ ...draft, to: e.target.value })} /></div>
        <Button variant="secondary" disabled={!Object.values(draft).some(Boolean)} onClick={() => change(empty)}>Réinitialiser les filtres</Button>
      </div>
      <p className="incident-list-summary">Dates saisies dans le fuseau horaire de votre navigateur.{directoryFailed && " Annuaire indisponible : saisissez un identifiant utilisateur."}</p>
      {validation && <p role="alert" className="form-error">{validation}</p>}
      {loading && <p className="incident-list-loading" role="status"><span className="spinner" aria-hidden="true" />Chargement des journaux…</p>}
      {error && <AdminError error={error} descriptions={descriptions} retry={refresh} />}
      {data && <>
        <p className="incident-list-summary" role="status">{data.total} événements trouvés{loading || error ? " · Dernières données disponibles" : ""}</p>
        {!data.items.length ? <StatePanel title="Aucun événement" description="Aucun journal ne correspond aux filtres sélectionnés." /> :
          <div className="incident-table-scroll"><table className="incident-table audit-table"><caption className="sr-only">Journaux d’audit</caption><thead><tr>{["Date et heure", "Utilisateur", "Événement", "Ressource", "Résultat", "Détails"].map(label => <th scope="col" key={label}>{label}</th>)}</tr></thead><tbody>{data.items.map(log => <tr key={log.id}>
            <td data-label="Date et heure"><time dateTime={log.created_at}>{auditDate(log.created_at)}</time></td>
            <td data-label="Utilisateur">{log.user_id === null ? "Utilisateur inconnu ou supprimé" : users.find(user => user.id === log.user_id)?.full_name ?? `Utilisateur n° ${log.user_id}`}</td>
            <td data-label="Événement">{auditEventLabel(log.event_type)}</td><td data-label="Ressource">{log.resource_type ?? "Non renseignée"}{log.resource_id !== null && ` · n° ${log.resource_id}`}</td>
            <td data-label="Résultat"><span className={`badge ${log.result === "SUCCESS" ? "badge-success" : "audit-failure"}`}>{auditResults[log.result] ?? log.result}</span></td>
            <td data-label="Détails"><Button variant="secondary" onClick={() => select(log)} aria-label={`Voir le journal ${log.id}`}>Voir le détail</Button></td>
          </tr>)}</tbody></table></div>}
      </>}
      <IncidentPagination noun="événements" sizeLabel="Événements par page" data={!loading && !error && !validation ? data : undefined} pageSize={size} onPageChange={changePage} onPageSizeChange={next => { setSize(next); changePage(1); }} />
    </section>
    {selected && <AuditDetails log={selected} close={() => select(null)} />}
  </>;
}
export function AuditManagement() {
  const { user } = useAuth();
  if (!user) return null;
  return user.role === "ADMIN" ? <Management key={user.id} /> : <StatePanel error title="Accès refusé" description={descriptions[403]} />;
}
