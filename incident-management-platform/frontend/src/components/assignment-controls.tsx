"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Button, StatePanel } from "@/components/ui";
import { IncidentPriorityBadge, IncidentStatusBadge } from "@/components/incident-badges";
import { ApiError } from "@/lib/api";
import { assignIncident, listTechnicians } from "@/services/incident.service";
import type { User } from "@/types/auth";
import type { IncidentResponse } from "@/types/incident";

export function useTechnicians() {
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const [attempt, retry] = useState(0);
  useEffect(() => {
    let current = true;
    listTechnicians().then(data => {
      if (current) setUsers(data.filter(u => u.role === "TECHNICIAN" && u.is_active));
    }).catch(e => { if (current) setError(e); }).finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [attempt]);
  function reload() { setUsers([]); setLoading(true); setError(null); retry(n => n + 1); }
  return { users, loading, error, reload };
}

export function ownerLabel(id: number | null, admin: User, users: User[]) {
  if (id === null) return "Non assigné";
  if (id === admin.id) return admin.full_name + " (vous)";
  return users.find(u => u.id === id)?.full_name || `Utilisateur n° ${id}`;
}

export function AdminError({ error, retry, directory = false }: { error: Error; retry?: () => void; directory?: boolean }) {
  const path = usePathname();
  const code = error instanceof ApiError ? error.status : 0;
  const messages: Record<number, string> = {
    401: "Votre session a expiré. Reconnectez-vous pour continuer.",
    403: "Vous ne disposez pas des droits nécessaires pour cette opération.",
    404: "L’incident ou le responsable sélectionné est introuvable.",
    409: "L’incident a été fermé ou le responsable est devenu inactif. Actualisez les données.",
    422: "Le choix du responsable est invalide. Vérifiez votre sélection.",
  };
  return <StatePanel error title={code === 401 ? "Session expirée" : code === 403 ? "Accès refusé" : directory ? "Annuaire indisponible" : "Opération impossible"}
    description={directory && code !== 401 && code !== 403 ? "La liste des techniciens n’a pas pu être chargée." : messages[code] ?? "Le service est indisponible. Réessayez dans un instant."}>
    {code === 401 ? <Link className="button button-secondary" href={`/login?next=${encodeURIComponent(path)}`}>Se reconnecter</Link> : retry && <Button type="button" variant="secondary" onClick={retry}>Réessayer</Button>}
  </StatePanel>;
}

export function AssignmentButton({ incident, open }: { incident: IncidentResponse; open: () => void }) {
  const closed = incident.status === "CLOSED";
  return <div><Button type="button" variant="secondary" disabled={closed} onClick={open}>{incident.assigned_to_id === null ? "Assigner" : "Réassigner"}</Button>
    {closed && <small className="block muted">Incident clos</small>}</div>;
}

export function AssignmentDialog({ incident, admin, directory, close, saved }: {
  incident: IncidentResponse; admin: User; directory: ReturnType<typeof useTechnicians>; close: () => void;
  saved: (updated: IncidentResponse) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const locked = useRef(false);
  const [value, select] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  useEffect(() => { const element = dialog.current; element?.showModal(); return () => element?.close(); }, []);
  const target = Number(value);
  const eligible = !!value && (target === admin.id || directory.users.some(u => u.id === target));
  const unchanged = !!value && target === incident.assigned_to_id;
  const denied = directory.error instanceof ApiError && [401, 403].includes(directory.error.status);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!eligible || unchanged || denied || locked.current || incident.status === "CLOSED") return;
    locked.current = true; setPending(true); setError(null);
    try { saved(await assignIncident(incident.id, target)); }
    catch (e) { setError(e instanceof Error ? e : new Error()); }
    finally { locked.current = false; setPending(false); }
  }
  return <dialog ref={dialog} className="assignment-dialog panel" aria-labelledby="assignment-title" onCancel={event => { event.preventDefault(); if (!locked.current) close(); }}>
    <div className="panel-heading"><div><p className="eyebrow">{incident.reference}</p><h2 id="assignment-title">{incident.assigned_to_id === null ? "Assigner" : "Réassigner"} l’incident</h2></div></div>
    <form className="incident-form incident-form-body" onSubmit={submit}>
      <p><strong>{incident.title}</strong></p>
      <p className="my-3 flex gap-2"><IncidentStatusBadge status={incident.status} /><IncidentPriorityBadge priority={incident.priority} /></p>
      <p className="muted mb-5">Responsable actuel : {ownerLabel(incident.assigned_to_id, admin, directory.users)}</p>
      {directory.loading && <p role="status">Chargement des techniciens…</p>}
      {directory.error && <AdminError directory error={directory.error} retry={pending ? undefined : directory.reload} />}
      {!directory.loading && !directory.error && !directory.users.length && <p className="muted">Aucun technicien actif. Vous pouvez prendre cet incident en charge.</p>}
      <div className="field"><label htmlFor="assignment-target">Nouveau responsable</label>
        <select id="assignment-target" value={value} disabled={pending || denied || directory.loading} onChange={e => { select(e.target.value); setError(null); }}>
          <option value="">Choisir un responsable</option><option value={admin.id}>M’assigner cet incident</option>
          {directory.users.map(u => <option key={u.id} value={u.id}>{u.full_name} — {u.email}</option>)}
        </select></div>
      {unchanged && <p role="status">Cet incident est déjà assigné à cette personne.</p>}
      {error && <AdminError error={error} />}
      <div className="incident-actions"><Button type="submit" disabled={!eligible || unchanged || pending || denied || directory.loading}>{pending ? "Assignation en cours…" : "Confirmer"}</Button>
        <Button type="button" variant="secondary" disabled={pending} onClick={close}>Annuler</Button></div>
    </form>
  </dialog>;
}

export function DetailAssignment({ incident, admin, saved }: { incident: IncidentResponse; admin: User; saved: (i: IncidentResponse) => void }) {
  const directory = useTechnicians();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  return <section className="panel"><div className="panel-heading"><h2>Responsable</h2><AssignmentButton incident={incident} open={() => setOpen(true)} /></div>
    <p className="panel-note">{ownerLabel(incident.assigned_to_id, admin, directory.users)}</p>
    {message && <p role="status" className="comment-confirmation">{message}</p>}
    {open && <AssignmentDialog incident={incident} admin={admin} directory={directory} close={() => setOpen(false)}
      saved={updated => { saved(updated); setOpen(false); setMessage("Assignation enregistrée."); }} />}
  </section>;
}
