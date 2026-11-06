import { IncidentList } from "@/components/incident-list";
import { PageHeader } from "@/components/ui";

export default function AssignedIncidentsPage() {
  return <>
    <PageHeader title="Mes incidents assignés" description="Votre file de travail : retrouvez les incidents qui vous sont personnellement assignés." />
    <IncidentList scope="assigned" />
  </>;
}
