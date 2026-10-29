import Link from "next/link";
import { StatePanel } from "@/components/ui";
export default function NotFound() { return <main className="session-error"><StatePanel title="Page introuvable" description="Cette adresse ne correspond à aucune page de votre espace."><Link href="/dashboard" className="button button-primary">Retour au tableau de bord</Link></StatePanel></main>; }
