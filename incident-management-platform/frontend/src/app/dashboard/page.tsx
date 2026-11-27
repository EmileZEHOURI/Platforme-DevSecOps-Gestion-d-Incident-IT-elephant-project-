import { IncidentMetrics } from "@/components/incident-metrics";
import { IncidentOverview } from "@/components/incident-overview";
import Link from "next/link";
import { Badge, PageHeader } from "@/components/ui";
import { ServiceHealth } from "@/components/service-health";
export default function DashboardPage() { return <><PageHeader title="Vue d’ensemble" description="Votre point de départ pour les opérations IT et la sécurité." action={<Link className="button button-primary" href="/dashboard/incidents">Espace incidents ↗</Link>} /><div className="overview-banner"><div><Badge>VOTRE CENTRE D’OPÉRATIONS</Badge><h2>Une vision claire.<br />Une réponse coordonnée.</h2><p>Retrouvez vos services et préparez le suivi de vos incidents.</p></div><div className="banner-grid" aria-hidden="true">◎</div></div><IncidentMetrics /><div className="dashboard-grid"><IncidentOverview /><ServiceHealth /></div><div className="bottom-note"><p><strong>Tout commence par un signalement clair.</strong> Un contexte précis aide votre équipe à intervenir plus rapidement.</p></div></>; }
