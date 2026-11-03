import Link from "next/link";
import { IncidentForm } from "@/components/incident-form";
import { PageHeader } from "@/components/ui";

export default function NewIncidentPage() {
  return <>
    <Link href="/dashboard/incidents" className="incident-back">← Espace incidents</Link>
    <PageHeader title="Créer un incident" description="Signalez un problème informatique ou de sécurité à votre équipe." />
    <IncidentForm />
  </>;
}
