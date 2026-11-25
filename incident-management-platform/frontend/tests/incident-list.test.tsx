import type { ComponentProps, ReactNode } from "react";

import { act, render, screen, waitFor } from "@testing-library/react";

import userEvent from "@testing-library/user-event";

import { beforeEach, describe, expect, it, vi } from "vitest";

import { IncidentList } from "@/components/incident-list";
import { ApiError } from "@/lib/api";

// ======================================================
// TYPES UTILISÉS PAR LES DOUBLES DE TEST
// ======================================================

type TestIncident = {
  id: number;
  title: string;
  status: string;
};

type TestFilters = Record<string, unknown>;

type TestPage = {
  items: TestIncident[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
};

// ======================================================
// MOCKS
// ======================================================

const mocks = vi.hoisted(() => ({
  useAuth: vi.fn(),
  canViewAssignedIncidents: vi.fn(),

  listIncidents: vi.fn(),
  listAssignedIncidents: vi.fn(),

  onStartUpdated: null as
    | ((incident: { id: number; title: string; status: string }) => void)
    | null,
}));

vi.mock("@/components/auth-provider", () => ({
  useAuth: mocks.useAuth,
}));

vi.mock("@/lib/permissions", () => ({
  canViewAssignedIncidents: mocks.canViewAssignedIncidents,
}));

vi.mock("@/services/incident.service", () => ({
  listIncidents: mocks.listIncidents,
  listAssignedIncidents: mocks.listAssignedIncidents,
}));

vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {
    status = 0;
  },
}));

vi.mock("next/link", () => ({
  default: (props: ComponentProps<"a">) => <a {...props} />,
}));

vi.mock("@/components/ui", () => ({
  Button: ({
    variant: _variant,
    ...props
  }: ComponentProps<"button"> & {
    variant?: string;
  }) => {
    void _variant;
    return <button {...props} />;
  },

  StatePanel: ({
    title,
    description,
    children,
    error,
  }: {
    title: string;
    description?: string;
    children?: ReactNode;
    error?: boolean;
  }) => (
    <div role={error ? "alert" : undefined}>
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      {children}
    </div>
  ),
}));

vi.mock("@/components/incident-table", () => ({
  IncidentTable: ({
    incidents,
    action,
  }: {
    incidents: TestIncident[];
    action?: (incident: TestIncident) => ReactNode;
  }) => (
    <ul data-testid="incident-table">
      {incidents.map((incident) => (
        <li key={incident.id}>
          {incident.title}
          {action?.(incident)}
        </li>
      ))}
    </ul>
  ),
}));

vi.mock("@/components/incident-filters-bar", () => ({
  filterErrors: {},

  hasIncidentFilters: (filters: TestFilters) => Object.keys(filters).length > 0,

  IncidentFiltersBar: ({
    filters,
    onChange,
    count,
  }: {
    filters: TestFilters;
    onChange: (filters: TestFilters) => void;
    count?: number;
  }) => (
    <div data-testid="filters-bar">
      <span data-testid="current-filters">{JSON.stringify(filters)}</span>

      <span data-testid="filtered-count">{count ?? "-"}</span>

      <button onClick={() => onChange({ priority: "HIGH" })}>
        Filtrer priorité haute
      </button>

      <button onClick={() => onChange({})}>Effacer les filtres</button>
    </div>
  ),
}));

vi.mock("@/components/incident-pagination", () => ({
  IncidentPagination: ({
    data,
    pageSize,
    onPageChange,
    onPageSizeChange,
  }: {
    data?: TestPage;
    pageSize: number;
    onPageChange: (page: number) => void;
    onPageSizeChange: (size: number) => void;
  }) => (
    <div data-testid="incident-pagination">
      <span data-testid="current-page">{data?.page ?? "-"}</span>

      <span data-testid="current-page-size">{pageSize}</span>

      <button onClick={() => onPageChange((data?.page ?? 1) + 1)}>
        Page suivante
      </button>

      <button onClick={() => onPageSizeChange(50)}>Afficher 50</button>
    </div>
  ),
}));

vi.mock("@/components/incident-start", () => ({
  useIncidentStart: (onUpdated: (incident: TestIncident) => void) => {
    mocks.onStartUpdated = onUpdated;

    return {
      feedback: null,
      action: () => null,
    };
  },
}));

vi.mock("@/components/incident-resolve", () => ({
  useIncidentResolve: () => ({
    feedback: null,
    action: () => null,
  }),
}));

// ======================================================
// HELPERS
// ======================================================

function incident(id: number, title = `Incident ${id}`): TestIncident {
  return {
    id,
    title,
    status: "OPEN",
  };
}

function paginatedResponse(
  items: TestIncident[],
  page = 1,
  total = items.length,
  pageSize = 20,
): TestPage {
  const totalPages = Math.ceil(total / pageSize);

  return {
    items,
    total,
    page,
    page_size: pageSize,
    total_pages: totalPages,
    has_next: page < totalPages,
    has_previous: page > 1,
  };
}

function setRole(role: "USER" | "TECHNICIAN" | "ADMIN") {
  mocks.useAuth.mockReturnValue({
    user: {
      id: 7,
      role,
    },
  });
}

function makeApiError(status: number, message: string) {
  const error = new Error(message) as Error & {
    status: number;
  };

  Object.setPrototypeOf(error, ApiError.prototype);

  error.status = status;

  return error;
}

// ======================================================
// CONFIGURATION AVANT CHAQUE TEST
// ======================================================

beforeEach(() => {
  vi.resetAllMocks();

  mocks.onStartUpdated = null;

  setRole("USER");

  mocks.canViewAssignedIncidents.mockImplementation(
    (role: string) => role === "TECHNICIAN" || role === "ADMIN",
  );

  mocks.listIncidents.mockResolvedValue([incident(1)]);

  mocks.listAssignedIncidents.mockResolvedValue(
    paginatedResponse([incident(10, "Incident assigné")]),
  );
});

// ======================================================
// TESTS : MES INCIDENTS
// ======================================================

describe("IncidentList - Mes incidents", () => {
  it("affiche un état de chargement", async () => {
    let finish: ((items: TestIncident[]) => void) | undefined;

    const pending = new Promise<TestIncident[]>((resolve) => {
      finish = resolve;
    });

    mocks.listIncidents.mockReturnValueOnce(pending);

    render(<IncidentList />);

    expect(screen.getByRole("status")).toHaveTextContent(
      "Chargement de vos incidents",
    );

    await act(async () => {
      finish?.([incident(1)]);
    });

    expect(await screen.findByText("Incident 1")).toBeInTheDocument();
  });

  it("récupère et affiche les incidents", async () => {
    mocks.listIncidents.mockResolvedValueOnce([
      incident(1, "Erreur serveur"),
      incident(2, "Problème réseau"),
    ]);

    render(<IncidentList />);

    expect(await screen.findByText("Erreur serveur")).toBeInTheDocument();

    expect(screen.getByText("Problème réseau")).toBeInTheDocument();

    expect(
      screen.getByText(/2 incidents · Du plus récent au plus ancien/),
    ).toBeInTheDocument();

    expect(mocks.listIncidents).toHaveBeenCalledTimes(1);

    expect(mocks.listAssignedIncidents).not.toHaveBeenCalled();
  });

  it("affiche un message lorsque la liste est vide", async () => {
    mocks.listIncidents.mockResolvedValueOnce([]);

    render(<IncidentList />);

    expect(
      await screen.findByText("Aucun incident pour le moment"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", {
        name: "Créer mon premier incident",
      }),
    ).toHaveAttribute("href", "/dashboard/incidents/new");
  });

  it("permet d'actualiser les incidents", async () => {
    mocks.listIncidents
      .mockResolvedValueOnce([incident(1, "Premier incident")])
      .mockResolvedValueOnce([incident(2, "Nouvel incident")]);

    render(<IncidentList />);

    expect(await screen.findByText("Premier incident")).toBeInTheDocument();

    const user = userEvent.setup();

    await user.click(
      screen.getByRole("button", {
        name: /Actualiser/,
      }),
    );

    expect(await screen.findByText("Nouvel incident")).toBeInTheDocument();

    expect(mocks.listIncidents).toHaveBeenCalledTimes(2);
  });

  it("affiche une erreur et permet de réessayer", async () => {
    mocks.listIncidents
      .mockRejectedValueOnce(new Error("Serveur indisponible"))
      .mockResolvedValueOnce([incident(1, "Incident récupéré")]);

    render(<IncidentList />);

    expect(
      await screen.findByText("Impossible de charger les incidents"),
    ).toBeInTheDocument();

    expect(screen.getByText("Serveur indisponible")).toBeInTheDocument();

    const user = userEvent.setup();

    await user.click(
      screen.getByRole("button", {
        name: "Réessayer",
      }),
    );

    expect(await screen.findByText("Incident récupéré")).toBeInTheDocument();

    expect(mocks.listIncidents).toHaveBeenCalledTimes(2);
  });

  it("propose une reconnexion en cas d'erreur 401", async () => {
    mocks.listIncidents.mockRejectedValueOnce(
      makeApiError(401, "Non authentifié"),
    );

    render(<IncidentList />);

    expect(await screen.findByText("Session expirée")).toBeInTheDocument();

    expect(
      screen.getByRole("link", {
        name: "Se reconnecter",
      }),
    ).toHaveAttribute("href", "/login?next=%2Fdashboard%2Fincidents");
  });

  it("met à jour localement un incident modifié", async () => {
    render(<IncidentList />);

    expect(await screen.findByText("Incident 1")).toBeInTheDocument();

    act(() => {
      mocks.onStartUpdated?.({
        id: 1,
        title: "Incident mis à jour",
        status: "IN_PROGRESS",
      });
    });

    expect(screen.getByText("Incident mis à jour")).toBeInTheDocument();

    expect(screen.queryByText("Incident 1")).not.toBeInTheDocument();

    expect(mocks.listIncidents).toHaveBeenCalledTimes(1);
  });
});

// ======================================================
// TESTS : PERMISSIONS
// ======================================================

describe("IncidentList - Permissions", () => {
  it("ne charge rien sans utilisateur authentifié", () => {
    mocks.useAuth.mockReturnValue({
      user: null,
    });

    render(<IncidentList />);

    expect(mocks.listIncidents).not.toHaveBeenCalled();

    expect(mocks.listAssignedIncidents).not.toHaveBeenCalled();
  });

  it("refuse les incidents assignés au rôle USER", () => {
    setRole("USER");

    render(<IncidentList scope="assigned" />);

    expect(screen.getByText("Accès refusé")).toBeInTheDocument();

    expect(
      screen.getByRole("link", {
        name: "Retour à mes incidents",
      }),
    ).toHaveAttribute("href", "/dashboard/incidents");

    expect(mocks.listAssignedIncidents).not.toHaveBeenCalled();
  });

  it.each(["TECHNICIAN", "ADMIN"] as const)(
    "autorise le rôle %s à consulter les incidents assignés",
    async (role) => {
      setRole(role);

      render(<IncidentList scope="assigned" />);

      expect(await screen.findByText("Incident assigné")).toBeInTheDocument();

      expect(mocks.listAssignedIncidents).toHaveBeenCalledTimes(1);
    },
  );
});

// ======================================================
// TESTS : INCIDENTS ASSIGNÉS
// ======================================================

describe("IncidentList - Incidents assignés", () => {
  beforeEach(() => {
    setRole("TECHNICIAN");
  });

  it("envoie les paramètres de pagination initiaux", async () => {
    render(<IncidentList scope="assigned" />);

    await screen.findByText("Incident assigné");

    expect(mocks.listAssignedIncidents).toHaveBeenCalledWith(
      {
        page: 1,
        page_size: 20,
      },
      expect.any(Object),
    );

    expect(screen.getByTestId("current-page")).toHaveTextContent("1");

    expect(screen.getByTestId("current-page-size")).toHaveTextContent("20");
  });

  it("affiche un état vide sans filtres", async () => {
    mocks.listAssignedIncidents.mockResolvedValueOnce(paginatedResponse([]));

    render(<IncidentList scope="assigned" />);

    expect(
      await screen.findByText("Aucun incident assigné"),
    ).toBeInTheDocument();
  });

  it("applique un filtre de priorité", async () => {
    mocks.listAssignedIncidents
      .mockResolvedValueOnce(
        paginatedResponse([incident(1, "Incident initial")]),
      )
      .mockResolvedValueOnce(
        paginatedResponse([incident(2, "Incident prioritaire")]),
      );

    render(<IncidentList scope="assigned" />);

    await screen.findByText("Incident initial");

    const user = userEvent.setup();

    await user.click(
      screen.getByRole("button", {
        name: "Filtrer priorité haute",
      }),
    );

    expect(await screen.findByText("Incident prioritaire")).toBeInTheDocument();

    expect(mocks.listAssignedIncidents).toHaveBeenLastCalledWith(
      {
        priority: "HIGH",
        page: 1,
        page_size: 20,
      },
      expect.any(Object),
    );
  });

  it("propose de réinitialiser les filtres sans résultat", async () => {
    mocks.listAssignedIncidents
      .mockResolvedValueOnce(
        paginatedResponse([incident(1, "Incident initial")]),
      )
      .mockResolvedValueOnce(paginatedResponse([]))
      .mockResolvedValueOnce(
        paginatedResponse([incident(1, "Incident initial")]),
      );

    render(<IncidentList scope="assigned" />);

    await screen.findByText("Incident initial");

    const user = userEvent.setup();

    await user.click(
      screen.getByRole("button", {
        name: "Filtrer priorité haute",
      }),
    );

    expect(await screen.findByText("Aucun résultat")).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", {
        name: "Réinitialiser les filtres",
      }),
    );

    expect(await screen.findByText("Incident initial")).toBeInTheDocument();

    expect(mocks.listAssignedIncidents).toHaveBeenLastCalledWith(
      {
        page: 1,
        page_size: 20,
      },
      expect.any(Object),
    );
  });

  it("passe à la page suivante", async () => {
    mocks.listAssignedIncidents
      .mockResolvedValueOnce(
        paginatedResponse([incident(1, "Page une")], 1, 45),
      )
      .mockResolvedValueOnce(
        paginatedResponse([incident(2, "Page deux")], 2, 45),
      );

    render(<IncidentList scope="assigned" />);

    await screen.findByText("Page une");

    const user = userEvent.setup();

    await user.click(
      screen.getByRole("button", {
        name: "Page suivante",
      }),
    );

    expect(await screen.findByText("Page deux")).toBeInTheDocument();

    expect(mocks.listAssignedIncidents).toHaveBeenLastCalledWith(
      {
        page: 2,
        page_size: 20,
      },
      expect.any(Object),
    );
  });

  it("revient à la page 1 après un changement de taille", async () => {
    mocks.listAssignedIncidents
      .mockResolvedValueOnce(
        paginatedResponse([incident(1, "Page une")], 1, 80),
      )
      .mockResolvedValueOnce(
        paginatedResponse([incident(2, "Page deux")], 2, 80),
      )
      .mockResolvedValueOnce(
        paginatedResponse([incident(3, "Nouvelle taille")], 1, 80, 50),
      );

    render(<IncidentList scope="assigned" />);

    await screen.findByText("Page une");

    const user = userEvent.setup();

    await user.click(
      screen.getByRole("button", {
        name: "Page suivante",
      }),
    );

    await screen.findByText("Page deux");

    await user.click(
      screen.getByRole("button", {
        name: "Afficher 50",
      }),
    );

    expect(await screen.findByText("Nouvelle taille")).toBeInTheDocument();

    expect(mocks.listAssignedIncidents).toHaveBeenLastCalledWith(
      {
        page: 1,
        page_size: 50,
      },
      expect.any(Object),
    );
  });

  it("revient à la dernière page valide si nécessaire", async () => {
    mocks.listAssignedIncidents
      .mockResolvedValueOnce(
        paginatedResponse([incident(1, "Page initiale")], 1, 45),
      )
      .mockResolvedValueOnce({
        ...paginatedResponse([], 2, 10),
        total_pages: 1,
        has_next: false,
      })
      .mockResolvedValueOnce(
        paginatedResponse([incident(1, "Page corrigée")], 1, 10),
      );

    render(<IncidentList scope="assigned" />);

    await screen.findByText("Page initiale");

    const user = userEvent.setup();

    await user.click(
      screen.getByRole("button", {
        name: "Page suivante",
      }),
    );

    expect(await screen.findByText("Page corrigée")).toBeInTheDocument();

    expect(mocks.listAssignedIncidents).toHaveBeenCalledTimes(3);

    expect(mocks.listAssignedIncidents).toHaveBeenLastCalledWith(
      {
        page: 1,
        page_size: 20,
      },
      expect.any(Object),
    );
  });

  it("refuse l'affichage après une erreur API 403", async () => {
    mocks.listAssignedIncidents.mockRejectedValueOnce(
      makeApiError(403, "Vous ne pouvez pas consulter ces incidents."),
    );

    render(<IncidentList scope="assigned" />);

    expect(await screen.findByText("Accès refusé")).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Réessayer",
      }),
    ).toBeInTheDocument();
  });

  it("relance la récupération après la mise à jour d'un incident assigné", async () => {
    render(<IncidentList scope="assigned" />);

    await screen.findByText("Incident assigné");

    act(() => {
      mocks.onStartUpdated?.({
        id: 10,
        title: "Incident démarré",
        status: "IN_PROGRESS",
      });
    });

    await waitFor(() => {
      expect(mocks.listAssignedIncidents).toHaveBeenCalledTimes(2);
    });
  });

  it("annule la requête lorsque le composant est démonté", async () => {
    const { unmount } = render(<IncidentList scope="assigned" />);

    await screen.findByText("Incident assigné");

    const signal = mocks.listAssignedIncidents.mock.calls[0][1] as AbortSignal;

    expect(signal.aborted).toBe(false);

    unmount();

    expect(signal.aborted).toBe(true);
  });
});
