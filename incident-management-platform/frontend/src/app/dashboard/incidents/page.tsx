import Link from "next/link";
import { IncidentList } from "@/components/incident-list";
import { PageHeader } from "@/components/ui";

export default function IncidentsPage() {
  return <>
    <PageHeader title="Incidents" description="Retrouvez vos signalements et leur état de prise en charge."
      action={<Link className="button button-primary" href="/dashboard/incidents/new">Créer un incident</Link>} />
    <IncidentList />
  </>;
}
