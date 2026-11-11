import type { ReactNode } from "react";
import Link from "next/link";
import { IncidentPriorityBadge, IncidentStatusBadge } from "@/components/incident-badges";
import { incidentCategories, type IncidentResponse } from "@/types/incident";

const dateFormat = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" });

export function IncidentTable({ incidents, management, action }: { action?: (incident: IncidentResponse) => ReactNode; incidents: IncidentResponse[]; management?: { owner: (i: IncidentResponse) => string; action: (i: IncidentResponse) => ReactNode } }) {
  return (
    <div className="incident-table-scroll" role="region" aria-label="Liste des incidents, défilement horizontal disponible" tabIndex={0}>
      <table className="incident-table">
        <caption className="sr-only">Liste des incidents</caption>
        <thead><tr><th scope="col">Référence</th><th scope="col">Titre</th><th scope="col">Catégorie</th><th scope="col">Priorité</th><th scope="col">Statut</th><th scope="col">Créé le</th>{management && <th scope="col">Responsable</th>}{(management || action) && <th scope="col">Action</th>}</tr></thead>
        <tbody>{incidents.map(incident => (
          <tr key={incident.id}>
            <th scope="row" className="incident-reference">{management ? incident.reference : <Link className="incident-detail-link" href={`/dashboard/incidents/${incident.id}`} aria-label={`Voir le détail de ${incident.reference}`}>{incident.reference}</Link>}</th>
            <td className="incident-list-title">{incident.title}</td>
            <td>{incidentCategories[incident.category]}</td>
            <td><IncidentPriorityBadge priority={incident.priority} /></td>
            <td><IncidentStatusBadge status={incident.status} /></td>
            <td className="incident-list-date"><time dateTime={incident.created_at}>{dateFormat.format(new Date(incident.created_at))}</time></td>
            {management && <td>{management.owner(incident)}</td>}
            {(management || action) && <td>{(management?.action ?? action)?.(incident)}</td>}
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}
