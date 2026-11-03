import Link from "next/link";
import { Badge, PageHeader, StatePanel } from "@/components/ui";

export default function IncidentsPage() {
  return <>
    <PageHeader title="Incidents" description="Signalez un problème et coordonnez sa prise en charge."
      action={<Link className="button button-primary" href="/dashboard/incidents/new">Créer un incident</Link>} />
    <section className="panel">
      <div className="panel-heading"><h2>Vos signalements</h2><Badge>Consultation à venir</Badge></div>
      <StatePanel title="Un problème à signaler ?" description="Vous pouvez dès maintenant créer un incident. La consultation de la liste et le suivi des incidents seront disponibles prochainement.">
        <Link className="button button-secondary" href="/dashboard/incidents/new">Nouveau signalement →</Link>
      </StatePanel>
    </section>
  </>;
}
