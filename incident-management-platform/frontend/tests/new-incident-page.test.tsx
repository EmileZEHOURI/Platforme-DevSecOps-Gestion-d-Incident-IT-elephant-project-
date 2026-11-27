import type { ReactNode } from "react";

import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import NewIncidentPage from "@/app/dashboard/incidents/new/page";

// Simuler le formulaire pour tester uniquement la page.
vi.mock("@/components/incident-form", () => ({
  IncidentForm: () => (
    <div data-testid="incident-form">
      Formulaire de création d&apos;incident
    </div>
  ),
}));

// Simuler le composant d'en-tête.
vi.mock("@/components/ui", () => ({
  PageHeader: ({
    title,
    description,
  }: {
    title: string;
    description: string;
  }) => (
    <header>
      <h1>{title}</h1>
      <p>{description}</p>
    </header>
  ),
}));

// Simuler le lien Next.js.
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

describe("NewIncidentPage", () => {
  it("affiche le titre et la description", () => {
    render(<NewIncidentPage />);

    expect(
      screen.getByRole("heading", {
        name: "Créer un incident",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "Signalez un problème informatique ou de sécurité à votre équipe.",
      ),
    ).toBeInTheDocument();
  });

  it("affiche un lien de retour vers les incidents", () => {
    render(<NewIncidentPage />);

    const backLink = screen.getByRole("link", {
      name: /Espace incidents/,
    });

    expect(backLink).toHaveAttribute("href", "/dashboard/incidents");
  });

  it("intègre le formulaire de création d'incident", () => {
    render(<NewIncidentPage />);

    expect(screen.getByTestId("incident-form")).toBeInTheDocument();
  });
});
