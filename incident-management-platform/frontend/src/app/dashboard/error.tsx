"use client";
import { Button, StatePanel } from "@/components/ui";
export default function DashboardError({ reset }: { reset: () => void }) { return <StatePanel error title="Cette page n’a pas pu être chargée" description="Réessayez pour reprendre votre travail."><Button onClick={reset}>Réessayer</Button></StatePanel>; }
