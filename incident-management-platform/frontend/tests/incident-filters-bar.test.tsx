
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

import {
  IncidentFiltersBar,
  hasIncidentFilters,
  filterErrors,
} from "@/components/incident-filters-bar";

import {
  incidentStatuses,
  incidentPriorities,
  incidentCategories,
  type IncidentFilters,
} from "@/types/incident";

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
// Utilisation des vraies valeurs des énumérations
// ======================================================

const status = Object.keys(
  incidentStatuses,
)[0] as NonNullable<IncidentFilters["status"]>;

const priority = Object.keys(
  incidentPriorities,
)[0] as NonNullable<IncidentFilters["priority"]>;

const category = Object.keys(
  incidentCategories,
)[0] as NonNullable<IncidentFilters["category"]>;

let onChange: (filters: IncidentFilters) => void;

beforeEach(() => {
  onChange = vi.fn<(filters: IncidentFilters) => void>();
});

function renderFilters(
  filters: IncidentFilters = {},
  count?: number,
) {
  return render(
    <IncidentFiltersBar
      filters={filters}
      onChange={onChange}
      count={count}
    />,
  );
}

// ======================================================
// 1. FONCTIONS UTILITAIRES
// ======================================================

describe("IncidentFiltersBar - Utilitaires", () => {
  it("détecte l'absence de filtres actifs", () => {
    expect(
      hasIncidentFilters({}),
    ).toBe(false);
  });

  it.each([
    [{ status }],
    [{ priority }],
    [{ category }],
  ])(
    "détecte la présence d'un filtre actif",
    (filters) => {
      expect(
        hasIncidentFilters(filters),
      ).toBe(true);
    },
  );

  it("expose les messages d'erreur attendus", () => {
    expect(filterErrors[404]).toBe(
      "Utilisateur introuvable ou inaccessible.",
    );

    expect(filterErrors[422]).toBe(
      "Un filtre est invalide. Modifiez votre sélection puis réessayez.",
    );
  });
});

// ======================================================
// 2. AFFICHAGE
// ======================================================

describe("IncidentFiltersBar - Affichage", () => {
  it("affiche le groupe de filtres", () => {
    renderFilters();

    expect(
      screen.getByRole("group", {
        name: "Filtres des incidents",
      }),
    ).toBeInTheDocument();
  });

  it("affiche les trois champs de sélection", () => {
    renderFilters();

    expect(
      screen.getByRole("combobox", {
        name: "Statut",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("combobox", {
        name: "Priorité",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("combobox", {
        name: "Catégorie",
      }),
    ).toBeInTheDocument();
  });

  it("affiche les options disponibles", () => {
    renderFilters();

    const statusSelect = screen.getByRole(
      "combobox",
      { name: "Statut" },
    );

    const prioritySelect = screen.getByRole(
      "combobox",
      { name: "Priorité" },
    );

    const categorySelect = screen.getByRole(
      "combobox",
      { name: "Catégorie" },
    );

    expect(
      within(statusSelect).getAllByRole("option"),
    ).toHaveLength(
      Object.keys(incidentStatuses).length + 1,
    );

    expect(
      within(prioritySelect).getAllByRole("option"),
    ).toHaveLength(
      Object.keys(incidentPriorities).length + 1,
    );

    expect(
      within(categorySelect).getAllByRole("option"),
    ).toHaveLength(
      Object.keys(incidentCategories).length + 1,
    );
  });

  it("sélectionne tous les éléments par défaut", () => {
    renderFilters();

    expect(
      screen.getByRole("combobox", {
        name: "Statut",
      }),
    ).toHaveValue("");

    expect(
      screen.getByRole("combobox", {
        name: "Priorité",
      }),
    ).toHaveValue("");

    expect(
      screen.getByRole("combobox", {
        name: "Catégorie",
      }),
    ).toHaveValue("");
  });

  it("affiche les filtres déjà sélectionnés", () => {
    renderFilters({
      status,
      priority,
      category,
    });

    expect(
      screen.getByRole("combobox", {
        name: "Statut",
      }),
    ).toHaveValue(status);

    expect(
      screen.getByRole("combobox", {
        name: "Priorité",
      }),
    ).toHaveValue(priority);

    expect(
      screen.getByRole("combobox", {
        name: "Catégorie",
      }),
    ).toHaveValue(category);
  });

  it("n'affiche aucun compteur sans total fourni", () => {
    renderFilters();

    expect(
      screen.queryByRole("status"),
    ).not.toBeInTheDocument();
  });

  it.each([
    [0, "0 résultat"],
    [1, "1 résultat"],
    [5, "5 résultats"],
  ])(
    "affiche correctement le total %i",
    (count, expected) => {
      renderFilters({}, count);

      expect(
        screen.getByRole("status"),
      ).toHaveTextContent(expected);
    },
  );
});

// ======================================================
// 3. CHANGEMENTS DE FILTRES
// ======================================================

describe("IncidentFiltersBar - Interactions", () => {
  it("désactive la réinitialisation sans filtre", () => {
    renderFilters();

    expect(
      screen.getByRole("button", {
        name: "Réinitialiser les filtres",
      }),
    ).toBeDisabled();
  });

  it("active la réinitialisation avec un filtre", () => {
    renderFilters({ status });

    expect(
      screen.getByRole("button", {
        name: "Réinitialiser les filtres",
      }),
    ).toBeEnabled();
  });

  it("réinitialise tous les filtres", async () => {
    const user = userEvent.setup();

    renderFilters({
      status,
      priority,
      category,
    });

    await user.click(
      screen.getByRole("button", {
        name: "Réinitialiser les filtres",
      }),
    );

    expect(onChange).toHaveBeenCalledOnce();

    expect(onChange).toHaveBeenCalledWith({});
  });

  it("modifie le statut en conservant la priorité", async () => {
    const user = userEvent.setup();

    const initialFilters: IncidentFilters = {
      priority,
    };

    renderFilters(initialFilters);

    await user.selectOptions(
      screen.getByRole("combobox", {
        name: "Statut",
      }),
      status,
    );

    expect(onChange).toHaveBeenCalledWith({
      priority,
      status,
    });

    // Les props d'origine ne doivent pas être modifiées.
    expect(initialFilters).toEqual({
      priority,
    });
  });

  it("modifie la catégorie en conservant le statut", async () => {
    const user = userEvent.setup();

    renderFilters({
      status,
    });

    await user.selectOptions(
      screen.getByRole("combobox", {
        name: "Catégorie",
      }),
      category,
    );

    expect(onChange).toHaveBeenCalledWith({
      status,
      category,
    });
  });

  it("modifie la priorité en conservant la catégorie", async () => {
    const user = userEvent.setup();

    renderFilters({
      category,
    });

    await user.selectOptions(
      screen.getByRole("combobox", {
        name: "Priorité",
      }),
      priority,
    );

    expect(onChange).toHaveBeenCalledWith({
      category,
      priority,
    });
  });

  it("supprime uniquement le statut lorsqu'il revient à Tous", async () => {
    const user = userEvent.setup();

    renderFilters({
      status,
      priority,
    });

    await user.selectOptions(
      screen.getByRole("combobox", {
        name: "Statut",
      }),
      "",
    );

    expect(onChange).toHaveBeenCalledWith({
      priority,
    });
  });

  it("supprime uniquement la catégorie lorsqu'elle revient à Toutes", async () => {
    const user = userEvent.setup();

    renderFilters({
      category,
      status,
    });

    await user.selectOptions(
      screen.getByRole("combobox", {
        name: "Catégorie",
      }),
      "",
    );

    expect(onChange).toHaveBeenCalledWith({
      status,
    });
  });
});
