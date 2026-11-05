import Link from "next/link";
import { IncidentDetail } from "@/components/incident-detail";

export default async function IncidentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <>
    <Link className="incident-back" href="/dashboard/incidents">← Retour à mes incidents</Link>
    <IncidentDetail id={id} />
  </>;
}
