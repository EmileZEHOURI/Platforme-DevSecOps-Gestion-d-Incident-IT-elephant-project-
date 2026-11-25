"use client";
import { useEffect, useId, useRef } from "react";
import { Button } from "@/components/ui";
import { auditDate, redactAuditDetails } from "@/lib/audit-display";
import { auditEventLabel, auditResults, type AuditLog } from "@/types/audit";

export function AuditDetails({ log, close }: { log: AuditLog; close: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null); const id = useId();
  useEffect(() => { const node = dialog.current; node?.showModal(); return () => node?.close(); }, []);
  const fields = [["Identifiant du journal", log.id], ["Date et heure", auditDate(log.created_at)], ["Utilisateur", log.user_id ?? "Utilisateur inconnu ou supprimé"], ["Événement", auditEventLabel(log.event_type)], ["Résultat", auditResults[log.result] ?? log.result], ["Type de ressource", log.resource_type], ["Identifiant de la ressource", log.resource_id], ["Adresse IP", log.ip_address], ["User-Agent", log.user_agent]];
  return <dialog ref={dialog} className="assignment-dialog panel" aria-labelledby={id} onCancel={event => { event.preventDefault(); close(); }}>
    <div className="panel-heading"><h2 id={id}>Détails du journal</h2></div>
    <div className="incident-form-body"><dl className="incident-detail-facts">{fields.map(([label, value]) => <div key={label}><dt>{label}</dt><dd className="break-words">{value ?? "Non renseigné"}</dd></div>)}</dl>
      <h3 className="my-3">Détails JSON</h3><pre className="audit-json">{JSON.stringify(redactAuditDetails(log.details), null, 2)}</pre>
      <p className="muted my-3">Les propriétés sensibles reconnues sont masquées.</p>
      <Button variant="secondary" onClick={close}>Fermer</Button>
    </div>
  </dialog>;
}
