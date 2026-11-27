
import type { ComponentProps } from "react";

import { render, screen } from "@testing-library/react";

import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import IncidentDetailPage from "@/app/dashboard/incidents/[id]/page";

// ======================================================
// MOCKS
// ======================================================

const mocks = vi.hoisted(() => ({
  incidentDetail: vi.fn(),
}));

vi.mock("@/components/incident-detail", () => ({
  IncidentDetail: ({ id }: { id: string }) => {
    mocks.incidentDetail(id);

    return (
      <div data-testid="incident-detail">
        Détail de l&apos;incident {id}
      </div>
    );
  },
}));

vi.mock("next/link", () => ({
  default: (props: ComponentProps<"a">) => (
    <a {...props} />
  ),
}));

// ======================================================
// HELPER
// ======================================================

async function renderPage(id: string) {
  const element = await IncidentDetailPage({
    params: Promise.resolve({ id }),
  });

  return render(element);
}

beforeEach(() => {
  vi.clearAllMocks();
});

// ======================================================
// TESTS
// ======================================================

describe("IncidentDetailPage", () => {
  it("affiche un lien de retour vers mes incidents", async () => {
    await renderPage("42");

    const link = screen.getByRole("link", {
      name: /Retour à mes incidents/,
    });

    expect(link).toHaveAttribute(
      "href",
      "/dashboard/incidents",
    );
  });

  it("intègre le composant IncidentDetail", async () => {
    await renderPage("42");

    expect(
      screen.getByTestId("incident-detail"),
    ).toBeInTheDocument();
  });

  it("transmet le bon identifiant au composant IncidentDetail", async () => {
    await renderPage("42");

    expect(
      mocks.incidentDetail,
    ).toHaveBeenCalledWith("42");
  });

  it.each(["1", "42", "999"])(
    "transmet correctement l'identifiant %s",
    async (id) => {
      await renderPage(id);

      expect(
        mocks.incidentDetail,
      ).toHaveBeenCalledWith(id);

      expect(
        screen.getByTestId("incident-detail"),
      ).toHaveTextContent(
        `Détail de l'incident ${id}`,
      );
    },
  );
});
