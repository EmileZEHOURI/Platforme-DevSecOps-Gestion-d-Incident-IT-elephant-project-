
import type { ComponentProps } from "react";

import {
  render,
  screen,
  within,
} from "@testing-library/react";

import userEvent from "@testing-library/user-event";

import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { IncidentPagination } from "@/components/incident-pagination";

// ======================================================
// MOCK DU COMPOSANT BUTTON
// ======================================================

vi.mock("@/components/ui", () => ({
  Button: ({
    variant,
    ...props
  }: ComponentProps<"button"> & {
    variant?: string;
  }) => {
    void variant;
    return <button {...props} />;
  },
}));

// ======================================================
// DONNÉES DE TEST
// ======================================================

type PaginationData = NonNullable<
  ComponentProps<typeof IncidentPagination>["data"]
>;

const onPageChange = vi.fn();
const onPageSizeChange = vi.fn();

function makePage(
  overrides: Partial<PaginationData> = {},
): PaginationData {
  return {
    items: Array.from(
      { length: 20 },
      (_, index) => ({ id: index + 1 }),
    ),
    total: 45,
    page: 1,
    page_size: 20,
    total_pages: 3,
    has_next: true,
    has_previous: false,
    ...overrides,
  };
}

function renderPagination(
  props: Partial<
    ComponentProps<typeof IncidentPagination>
  > = {},
) {
  return render(
    <IncidentPagination
      data={makePage()}
      pageSize={20}
      onPageChange={onPageChange}
      onPageSizeChange={onPageSizeChange}
      {...props}
    />,
  );
}

beforeEach(() => {
  onPageChange.mockReset();
  onPageSizeChange.mockReset();
});

// ======================================================
// 1. AFFICHAGE
// ======================================================

describe("IncidentPagination - Affichage", () => {
  it("affiche une navigation accessible", () => {
    renderPagination();

    expect(
      screen.getByRole("navigation", {
        name: "Pagination des incidents",
      }),
    ).toBeInTheDocument();
  });

  it("affiche les quatre tailles disponibles", () => {
    renderPagination();

    const select = screen.getByRole("combobox", {
      name: "Incidents par page",
    });

    const options = within(select).getAllByRole(
      "option",
    );

    expect(options).toHaveLength(4);

    expect(
      options.map((option) => option.getAttribute("value")),
    ).toEqual(["10", "20", "50", "100"]);
  });

  it("sélectionne la taille 20 par défaut", () => {
    renderPagination();

    expect(
      screen.getByRole("combobox", {
        name: "Incidents par page",
      }),
    ).toHaveValue("20");
  });

  it("affiche un message lorsque les données sont absentes", () => {
    renderPagination({
      data: undefined,
    });

    expect(
      screen.getByRole("status"),
    ).toHaveTextContent(
      "Pagination indisponible pendant le chargement ou en cas d’erreur.",
    );

    expect(
      screen.getByText("—"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Précédent",
      }),
    ).toBeDisabled();

    expect(
      screen.getByRole("button", {
        name: "Suivant",
      }),
    ).toBeDisabled();
  });

  it("affiche aucune page lorsque le total est nul", () => {
    renderPagination({
      data: makePage({
        items: [],
        total: 0,
        total_pages: 0,
        has_next: false,
        has_previous: false,
      }),
    });

    expect(
      screen.getByRole("status"),
    ).toHaveTextContent(
      "Affichage de 0 à 0 sur 0 incidents",
    );

    expect(
      screen.getByText("Aucune page"),
    ).toBeInTheDocument();
  });

  it("affiche la bonne plage sur la première page", () => {
    renderPagination();

    expect(
      screen.getByRole("status"),
    ).toHaveTextContent(
      "Affichage de 1 à 20 sur 45 incidents",
    );

    expect(
      screen.getByText("Page 1 sur 3"),
    ).toBeInTheDocument();
  });

  it("affiche la bonne plage sur une page intermédiaire", () => {
    renderPagination({
      data: makePage({
        page: 2,
        has_previous: true,
        has_next: true,
      }),
    });

    expect(
      screen.getByRole("status"),
    ).toHaveTextContent(
      "Affichage de 21 à 40 sur 45 incidents",
    );

    expect(
      screen.getByText("Page 2 sur 3"),
    ).toBeInTheDocument();
  });

  it("affiche correctement une dernière page partielle", () => {
    renderPagination({
      data: makePage({
        page: 3,
        items: Array.from(
          { length: 5 },
          (_, index) => ({ id: index + 41 }),
        ),
        has_previous: true,
        has_next: false,
      }),
    });

    expect(
      screen.getByRole("status"),
    ).toHaveTextContent(
      "Affichage de 41 à 45 sur 45 incidents",
    );

    expect(
      screen.getByText("Page 3 sur 3"),
    ).toBeInTheDocument();
  });

  it("affiche une plage vide si aucun élément n'est retourné", () => {
    renderPagination({
      data: makePage({
        items: [],
        total: 45,
      }),
    });

    expect(
      screen.getByRole("status"),
    ).toHaveTextContent(
      "Affichage de 0 à 0 sur 45 incidents",
    );
  });

  it("permet de personnaliser les libellés", () => {
    renderPagination({
      noun: "événements",
      sizeLabel: "Événements par page",
    });

    expect(
      screen.getByRole("navigation", {
        name: "Pagination des événements",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("combobox", {
        name: "Événements par page",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("status"),
    ).toHaveTextContent(
      "Affichage de 1 à 20 sur 45 événements",
    );
  });
});

// ======================================================
// 2. NAVIGATION ENTRE LES PAGES
// ======================================================

describe("IncidentPagination - Navigation", () => {
  it("désactive Précédent sur la première page", () => {
    renderPagination();

    expect(
      screen.getByRole("button", {
        name: "Précédent",
      }),
    ).toBeDisabled();

    expect(
      screen.getByRole("button", {
        name: "Suivant",
      }),
    ).toBeEnabled();
  });

  it("désactive Suivant sur la dernière page", () => {
    renderPagination({
      data: makePage({
        page: 3,
        items: [{ id: 41 }],
        has_previous: true,
        has_next: false,
      }),
    });

    expect(
      screen.getByRole("button", {
        name: "Précédent",
      }),
    ).toBeEnabled();

    expect(
      screen.getByRole("button", {
        name: "Suivant",
      }),
    ).toBeDisabled();
  });

  it("respecte les indicateurs has_previous et has_next", () => {
    renderPagination({
      data: makePage({
        page: 2,
        has_previous: false,
        has_next: false,
      }),
    });

    expect(
      screen.getByRole("button", {
        name: "Précédent",
      }),
    ).toBeDisabled();

    expect(
      screen.getByRole("button", {
        name: "Suivant",
      }),
    ).toBeDisabled();
  });

  it("transmet la page précédente au parent", async () => {
    const user = userEvent.setup();

    renderPagination({
      data: makePage({
        page: 2,
        has_previous: true,
        has_next: true,
      }),
    });

    await user.click(
      screen.getByRole("button", {
        name: "Précédent",
      }),
    );

    expect(
      onPageChange,
    ).toHaveBeenCalledExactlyOnceWith(1);
  });

  it("transmet la page suivante au parent", async () => {
    const user = userEvent.setup();

    renderPagination({
      data: makePage({
        page: 2,
        has_previous: true,
        has_next: true,
      }),
    });

    await user.click(
      screen.getByRole("button", {
        name: "Suivant",
      }),
    );

    expect(
      onPageChange,
    ).toHaveBeenCalledExactlyOnceWith(3);
  });

  it("ne déclenche aucune navigation si les boutons sont désactivés", async () => {
    const user = userEvent.setup();

    renderPagination({
      data: makePage({
        items: [],
        total: 0,
        total_pages: 0,
        has_previous: false,
        has_next: false,
      }),
    });

    await user.click(
      screen.getByRole("button", {
        name: "Précédent",
      }),
    );

    await user.click(
      screen.getByRole("button", {
        name: "Suivant",
      }),
    );

    expect(
      onPageChange,
    ).not.toHaveBeenCalled();
  });

  it("désactive les deux boutons sur une page unique", () => {
    renderPagination({
      data: makePage({
        items: [{ id: 1 }],
        total: 1,
        page: 1,
        total_pages: 1,
        has_previous: false,
        has_next: false,
      }),
    });

    expect(
      screen.getByRole("button", {
        name: "Précédent",
      }),
    ).toBeDisabled();

    expect(
      screen.getByRole("button", {
        name: "Suivant",
      }),
    ).toBeDisabled();

    expect(
      screen.getByText("Page 1 sur 1"),
    ).toBeInTheDocument();
  });
});

// ======================================================
// 3. TAILLE DES PAGES
// ======================================================

describe("IncidentPagination - Taille des pages", () => {
  it("affiche la taille reçue dans les props", () => {
    renderPagination({
      pageSize: 50,
    });

    expect(
      screen.getByRole("combobox", {
        name: "Incidents par page",
      }),
    ).toHaveValue("50");
  });

  it.each([10, 20, 50, 100])(
    "transmet une taille de %i éléments",
    async (size) => {
      const user = userEvent.setup();

      renderPagination({
        pageSize: size === 20 ? 10 : 20,
      });

      await user.selectOptions(
        screen.getByRole("combobox", {
          name: "Incidents par page",
        }),
        String(size),
      );

      expect(
        onPageSizeChange,
      ).toHaveBeenCalledExactlyOnceWith(size);

      expect(
        onPageChange,
      ).not.toHaveBeenCalled();
    },
  );
});
