import { PageHeader } from "@/components/ui";
import { ServiceHealth } from "@/components/service-health";
export default function ServicesPage() { return <><PageHeader title="État des services" description="Vérifiez la disponibilité de l’application et de sa base de données." /><ServiceHealth /></>; }
