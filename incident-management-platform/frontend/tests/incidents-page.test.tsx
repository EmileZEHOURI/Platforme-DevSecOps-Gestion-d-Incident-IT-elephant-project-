
import type { ReactNode } from "react";

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import IncidentsPage from "@/app/dashboard/incidents/page";

// Simuler le composant de liste.
// Sa logique métier sera testée séparément.
vi.mock("@/components/incident-list", () => ({
  IncidentList: () => (
    <div data-testid="incident-list">
      Liste des incidents
    </div>
  ),
}));

// Simuler PageHeader pour isoler la page.
vi.mock("@/components/ui", () => ({
  PageHeader: ({
    title,
    description,
    action,
  }: {
    title: string;
    description: string;
    action?: ReactNode;
  }) => (
    <header>
      <h1>{title}</h1>
      <p>{description}</p>
      {action}
    </header>
  ),
}));

// Simuler Next.js Link.
vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
  }: {
    href: string;
    children: ReactNode;
    className?: string;
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

describe("IncidentsPage", () => {
  it("affiche le titre et la description", () => {
    render(<IncidentsPage />);

    expect(
      screen.getByRole("heading", {
        name: "Incidents",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "Retrouvez vos signalements et leur état de prise en charge.",
      ),
    ).toBeInTheDocument();
  });

  it("affiche un lien vers la création d'incident", () => {
    render(<IncidentsPage />);

    const createLink = screen.getByRole("link", {
      name: "Créer un incident",
    });

    expect(createLink).toBeInTheDocument();

    expect(createLink).toHaveAttribute(
      "href",
      "/dashboard/incidents/new",
    );
  });

  it("intègre le composant IncidentList", () => {
    render(<IncidentsPage />);

    expect(
      screen.getByTestId("incident-list"),
    ).toBeInTheDocument();
  });
});
