"use client";

import { useEffect, useId, useRef, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { AdminError } from "@/components/assignment-controls";
import { Badge, Button, PageHeader, StatePanel } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { listUsers, updateUserActivation, type UserFilters } from "@/services/user.service";
import type { User } from "@/types/auth";

const roles = { USER: "Utilisateur", TECHNICIAN: "Technicien", ADMIN: "Administrateur" };
const messages = {
  403: "La gestion des utilisateurs est réservée aux administrateurs.",
  404: "L’utilisateur demandé n’existe plus ou n’est pas accessible.",
  422: "La sélection est invalide. Vérifiez les filtres ou l’état d’activation demandé.",
};
function conflictMessage(error: Error, user: User) {
  if (!(error instanceof ApiError) || error.status !== 409) return "";
  if (error.detail === "Impossible de désactiver un administrateur" || user.role === "ADMIN") return "Un compte administrateur ne peut pas être désactivé.";
  if (error.detail === "Liste non vide, impossibilité de désactivation") return "Impossible de désactiver ce technicien : des incidents ouverts ou en cours lui sont encore assignés. Veuillez les réassigner avant de poursuivre.";
  return typeof error.detail === "string" ? error.detail : "Cette modification est incompatible avec l’état actuel du compte. Actualisez les données.";
}

function UserDialog({ user, mode, close, saved }: {
  user: User; mode: "details" | "activation"; close: () => void; saved: (user: User) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const locked = useRef(false);
  const titleId = useId();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  useEffect(() => { const node = dialog.current; node?.showModal(); return () => node?.close(); }, []);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (locked.current || (user.role === "ADMIN" && user.is_active)) return;
    locked.current = true; setPending(true); setError(null);
    try { saved(await updateUserActivation(user.id, !user.is_active)); }
    catch (cause) { setError(cause instanceof Error ? cause : new Error()); }
    finally { locked.current = false; setPending(false); }
  }
  return <dialog ref={dialog} className="assignment-dialog panel" aria-labelledby={titleId}
    onCancel={event => { event.preventDefault(); if (!pending) close(); }}>
    <div className="panel-heading"><h2 id={titleId}>{mode === "details" ? "Informations utilisateur" : user.is_active ? "Désactiver le compte" : "Activer le compte"}</h2></div>
    <form className="incident-form incident-form-body" onSubmit={submit} aria-busy={pending}>
      <p className="break-words"><strong>{user.full_name}</strong></p>
      {mode === "details" ? <dl className="incident-detail-facts">
        <div><dt>E-mail</dt><dd className="break-words">{user.email}</dd></div>
        <div><dt>Rôle</dt><dd>{roles[user.role]}</dd></div>
        <div><dt>Statut</dt><dd>{user.is_active ? "Actif" : "Désactivé"}</dd></div>
        <div><dt>Créé le</dt><dd><time dateTime={user.created_at}>{new Intl.DateTimeFormat("fr-FR", { dateStyle: "long" }).format(new Date(user.created_at))}</time></dd></div>
      </dl> : <p className="my-3">{user.is_active ? "Ce compte ne pourra plus accéder à la plateforme tant qu’il restera désactivé. Confirmez-vous sa désactivation ?" : "Ce compte pourra à nouveau accéder à la plateforme. Confirmez-vous son activation ?"}</p>}
      {error && <AdminError error={error} descriptions={{ ...messages, 409: conflictMessage(error, user) }} />}
      <div className="incident-actions">
        <Button type="button" variant="secondary" disabled={pending} onClick={close}>{mode === "details" ? "Fermer" : "Annuler"}</Button>
        {mode === "activation" && <Button type="submit" disabled={pending}>{pending ? <><span className="spinner" aria-hidden="true" />Modification…</> : user.is_active ? "Confirmer la désactivation" : "Confirmer l’activation"}</Button>}
      </div>
    </form>
  </dialog>;
}

function Management() {
  const [filters, setFilters] = useState<UserFilters>({});
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [attempt, retry] = useState(0);
  const [notice, setNotice] = useState("");
  const [selected, select] = useState<{ user: User; mode: "details" | "activation" } | null>(null);
  useEffect(() => {
    const controller = new AbortController(); let active = true;
    listUsers(filters, controller.signal).then(result => { if (active) setUsers(result); })
      .catch(cause => { if (active) setError(cause instanceof Error ? cause : new Error()); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; controller.abort(); };
  }, [filters, attempt]);
  function reload() { setLoading(true); setError(null); retry(n => n + 1); }
  function changeFilters(next: UserFilters) { setFilters(next); setLoading(true); setError(null); setUsers([]); }
  function saved(user: User) {
    select(null); setNotice(`${user.full_name} : compte ${user.is_active ? "activé" : "désactivé"}.`);
    // Keep the confirmed state even if the following list refresh fails.
    setUsers(current => current.map(item => item.id === user.id ? user : item)); reload();
  }
  return <>
    <PageHeader eyebrow="ADMINISTRATION" title="Gestion des utilisateurs" description="Consultez les comptes et gérez leur accès à la plateforme." />
    {notice && <p className="comment-confirmation" role="status">{notice}</p>}
    <section className="panel" aria-busy={loading} aria-label="Liste des utilisateurs">
      <div className="panel-heading"><h2>Utilisateurs</h2><Button variant="ghost" disabled={loading} onClick={reload}>Actualiser ↻</Button></div>
      <div className="assignment-filters incident-form" role="group" aria-label="Filtres des utilisateurs">
        <div className="field"><label htmlFor="users-role">Rôle</label><select id="users-role" value={filters.role ?? ""} onChange={event => {
          const value = event.target.value;
          changeFilters({ ...filters, role: value === "ADMIN" || value === "TECHNICIAN" || value === "USER" ? value : undefined });
        }}><option value="">Tous les rôles</option><option value="ADMIN">Administrateurs</option><option value="TECHNICIAN">Techniciens</option><option value="USER">Utilisateurs</option></select></div>
        <div className="field"><label htmlFor="users-active">Statut</label><select id="users-active" value={filters.is_active === undefined ? "" : String(filters.is_active)} onChange={event => changeFilters({ ...filters, is_active: event.target.value === "" ? undefined : event.target.value === "true" })}><option value="">Tous les statuts</option><option value="true">Actifs</option><option value="false">Désactivés</option></select></div>
        <Button variant="secondary" disabled={!filters.role && filters.is_active === undefined} onClick={() => changeFilters({})}>Réinitialiser les filtres</Button>
      </div>
      {loading && <p className="incident-list-loading" role="status"><span className="spinner" aria-hidden="true" />Chargement des utilisateurs…</p>}
      {error && <AdminError error={error} descriptions={messages} retry={reload} />}
      {!loading && !error && !users.length && <StatePanel title="Aucun utilisateur" description="Aucun compte ne correspond à la sélection actuelle." />}
      {!!users.length && <>
        <p className="incident-list-summary" role="status">{users.length} compte{users.length > 1 ? "s" : ""}{loading || error ? " · Dernières données disponibles" : ""}</p>
        <div className="incident-table-scroll" role="region" aria-label="Comptes utilisateurs, défilement horizontal disponible" tabIndex={0}>
          <table className="incident-table"><caption className="sr-only">Comptes utilisateurs</caption><thead><tr><th scope="col">Nom complet</th><th scope="col">E-mail</th><th scope="col">Rôle</th><th scope="col">Statut</th><th scope="col">Actions</th></tr></thead>
            <tbody>{users.map(user => <tr key={user.id}>
              <th scope="row"><Button variant="ghost" onClick={() => select({ user, mode: "details" })}>{user.full_name}</Button></th><td>{user.email}</td><td>{roles[user.role]}</td>
              <td><Badge tone={user.is_active ? "success" : "neutral"}>{user.is_active ? "Actif" : "Désactivé"}</Badge></td>
              <td>{user.role === "ADMIN" && user.is_active ? <small className="muted">Compte administrateur protégé</small> : <Button variant="secondary" disabled={loading} onClick={() => select({ user, mode: "activation" })}>{user.is_active ? "Désactiver" : "Activer"}</Button>}</td>
            </tr>)}</tbody>
          </table>
        </div>
      </>}
    </section>
    {selected && <UserDialog user={selected.user} mode={selected.mode} close={() => select(null)} saved={saved} />}
  </>;
}
export function UserManagement() {
  const { user } = useAuth();
  if (!user) return null;
  return user.role === "ADMIN" ? <Management key={user.id} /> : <StatePanel error title="Accès refusé" description="La gestion des utilisateurs est réservée aux administrateurs." />;
}
