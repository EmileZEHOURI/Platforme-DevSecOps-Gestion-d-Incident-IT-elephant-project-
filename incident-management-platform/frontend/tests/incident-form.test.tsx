
import type { ComponentProps, ReactNode } from "react";

import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";

import userEvent from "@testing-library/user-event";

import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import { IncidentForm } from "@/components/incident-form";
import { ApiError } from "@/lib/api";
import {
  incidentCategories,
  incidentPriorities,
} from "@/types/incident";

// ======================================================
// MOCKS
// ======================================================

const mocks = vi.hoisted(() => ({
  createIncident: vi.fn(),
}));

vi.mock("@/services/incident.service", () => ({
  createIncident: mocks.createIncident,
}));

vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {
    status = 0;
    detail: unknown = undefined;
  },
}));

vi.mock("next/link", () => ({
  default: (props: ComponentProps<"a">) => (
    <a {...props} />
  ),
}));

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

  Badge: ({
    children,
  }: {
    children: ReactNode;
    tone?: string;
  }) => <span>{children}</span>,
}));

// ======================================================
// DONNÉES DE TEST
// ======================================================

const validCategory =
  Object.keys(incidentCategories).includes("ANOMALY")
    ? "ANOMALY"
    : Object.keys(incidentCategories)[0];

const validTitle = "Impossible d'accéder à la messagerie";

const validDescription =
  "La messagerie est inaccessible depuis ce matin.";

const receipt = {
  id: 42,
  reference: "INC-2026-0042",
  title: validTitle,
  description: validDescription,
  status: "OPEN",
  category: validCategory,
  priority: "MEDIUM",
  created_at: "2026-11-25T14:30:00Z",
};

type FormValues = {
  title?: string;
  description?: string;
  category?: string;
  priority?: string;
};

function fillForm({
  title = validTitle,
  description = validDescription,
  category = validCategory,
  priority = "MEDIUM",
}: FormValues = {}) {
  fireEvent.change(
    screen.getByLabelText("Titre"),
    {
      target: { value: title },
    },
  );

  fireEvent.change(
    screen.getByLabelText("Description"),
    {
      target: { value: description },
    },
  );

  if (category) {
    fireEvent.change(
      screen.getByLabelText("Catégorie"),
      {
        target: { value: category },
      },
    );
  }

  fireEvent.change(
    screen.getByLabelText("Priorité"),
    {
      target: { value: priority },
    },
  );
}

async function submitForm() {
  const user = userEvent.setup();

  await user.click(
    screen.getByRole("button", {
      name: "Créer l’incident",
    }),
  );
}

function makeApiError(
  status: number,
  detail?: unknown,
) {
  const error = new Error("API error") as Error & {
    status: number;
    detail?: unknown;
  };

  Object.setPrototypeOf(
    error,
    ApiError.prototype,
  );

  error.status = status;
  error.detail = detail;

  return error;
}

// ======================================================
// INITIALISATION
// ======================================================

beforeEach(() => {
  vi.resetAllMocks();

  mocks.createIncident.mockResolvedValue({
    ...receipt,
  });
});

// ======================================================
// 1. AFFICHAGE
// ======================================================

describe("IncidentForm - Affichage", () => {
  it("affiche tous les champs du formulaire", () => {
    render(<IncidentForm />);

    expect(
      screen.getByRole("heading", {
        name: "Décrire le problème",
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByLabelText("Titre"),
    ).toBeInTheDocument();

    expect(
      screen.getByLabelText("Description"),
    ).toBeInTheDocument();

    expect(
      screen.getByLabelText("Catégorie"),
    ).toBeInTheDocument();

    expect(
      screen.getByLabelText("Priorité"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Créer l’incident",
      }),
    ).toBeEnabled();
  });

  it("initialise le formulaire avec les bonnes valeurs", () => {
    render(<IncidentForm />);

    expect(
      screen.getByLabelText("Titre"),
    ).toHaveValue("");

    expect(
      screen.getByLabelText("Description"),
    ).toHaveValue("");

    expect(
      screen.getByLabelText("Catégorie"),
    ).toHaveValue("");

    expect(
      screen.getByLabelText("Priorité"),
    ).toHaveValue("MEDIUM");
  });

  it("met à jour les compteurs de caractères", () => {
    render(<IncidentForm />);

    fireEvent.change(
      screen.getByLabelText("Titre"),
      {
        target: { value: "  Bonjour  " },
      },
    );

    fireEvent.change(
      screen.getByLabelText("Description"),
      {
        target: {
          value: "Description valide",
        },
      },
    );

    expect(
      screen.getByText("7 / 150"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("18 / 5 000"),
    ).toBeInTheDocument();
  });

  it("propose une annulation vers la liste des incidents", () => {
    render(<IncidentForm />);

    expect(
      screen.getByRole("link", {
        name: "Annuler",
      }),
    ).toHaveAttribute(
      "href",
      "/dashboard/incidents",
    );
  });
});

// ======================================================
// 2. VALIDATION
// ======================================================

describe("IncidentForm - Validation", () => {
  it("refuse un formulaire entièrement vide", async () => {
    render(<IncidentForm />);

    await submitForm();

    expect(
      screen.getByText(
        /Saisissez un titre de 5 à 150 caractères/,
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        /Décrivez l’incident en 10 à 5 000 caractères/,
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Sélectionnez une catégorie."),
    ).toBeInTheDocument();

    expect(
      mocks.createIncident,
    ).not.toHaveBeenCalled();

    expect(
      screen.getByLabelText("Titre"),
    ).toHaveFocus();
  });

  it("refuse un titre trop court", async () => {
    render(<IncidentForm />);

    fillForm({
      title: "ABC",
    });

    await submitForm();

    expect(
      screen.getByLabelText("Titre"),
    ).toHaveAttribute(
      "aria-invalid",
      "true",
    );

    expect(
      mocks.createIncident,
    ).not.toHaveBeenCalled();
  });

  it("refuse les espaces qui masquent un titre trop court", async () => {
    render(<IncidentForm />);

    fillForm({
      title: "    ABC    ",
    });

    await submitForm();

    expect(
      screen.getByLabelText("Titre"),
    ).toHaveAttribute(
      "aria-invalid",
      "true",
    );

    expect(
      mocks.createIncident,
    ).not.toHaveBeenCalled();
  });

  it("refuse un titre de plus de 150 caractères", async () => {
    render(<IncidentForm />);

    fillForm({
      title: "A".repeat(151),
    });

    await submitForm();

    expect(
      screen.getByLabelText("Titre"),
    ).toHaveAttribute(
      "aria-invalid",
      "true",
    );

    expect(
      mocks.createIncident,
    ).not.toHaveBeenCalled();
  });

  it("refuse une description trop courte", async () => {
    render(<IncidentForm />);

    fillForm({
      description: "Court",
    });

    await submitForm();

    expect(
      screen.getByLabelText("Description"),
    ).toHaveAttribute(
      "aria-invalid",
      "true",
    );

    expect(
      mocks.createIncident,
    ).not.toHaveBeenCalled();
  });

  it("refuse une description de plus de 5000 caractères", async () => {
    render(<IncidentForm />);

    fillForm({
      description: "A".repeat(5001),
    });

    await submitForm();

    expect(
      screen.getByLabelText("Description"),
    ).toHaveAttribute(
      "aria-invalid",
      "true",
    );

    expect(
      mocks.createIncident,
    ).not.toHaveBeenCalled();
  });

  it("refuse une catégorie non sélectionnée", async () => {
    render(<IncidentForm />);

    fillForm({
      category: "",
    });

    await submitForm();

    expect(
      screen.getByLabelText("Catégorie"),
    ).toHaveAttribute(
      "aria-invalid",
      "true",
    );

    expect(
      mocks.createIncident,
    ).not.toHaveBeenCalled();
  });

  it("accepte les longueurs maximales autorisées", async () => {
    render(<IncidentForm />);

    const title = "T".repeat(150);
    const description = "D".repeat(5000);

    fillForm({
      title,
      description,
    });

    await submitForm();

    await waitFor(() => {
      expect(
        mocks.createIncident,
      ).toHaveBeenCalledWith({
        title,
        description,
        category: validCategory,
        priority: "MEDIUM",
      });
    });
  });
});

// ======================================================
// 3. CRÉATION
// ======================================================

describe("IncidentForm - Création", () => {
  it("transmet les données correctes au service", async () => {
    render(<IncidentForm />);

    fillForm();

    await submitForm();

    await waitFor(() => {
      expect(
        mocks.createIncident,
      ).toHaveBeenCalledWith({
        title: validTitle,
        description: validDescription,
        category: validCategory,
        priority: "MEDIUM",
      });
    });

    expect(
      mocks.createIncident,
    ).toHaveBeenCalledTimes(1);
  });

  it("permet de modifier la priorité", async () => {
    render(<IncidentForm />);

    const alternatePriority =
      Object.keys(incidentPriorities).find(
        (value) => value !== "MEDIUM",
      );

    expect(alternatePriority).toBeDefined();

    fillForm({
      priority: alternatePriority,
    });

    await submitForm();

    await waitFor(() => {
      expect(
        mocks.createIncident,
      ).toHaveBeenCalledWith(
        expect.objectContaining({
          priority: alternatePriority,
        }),
      );
    });
  });

  it("affiche une confirmation avec la référence", async () => {
    render(<IncidentForm />);

    fillForm();

    await submitForm();

    expect(
      await screen.findByText(
        "Création confirmée",
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        name: /INC-2026-0042/,
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText(validTitle),
    ).toBeInTheDocument();

    expect(
      screen.getByText("Ouvert"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", {
        name: "Retour à l’espace incidents",
      }),
    ).toHaveAttribute(
      "href",
      "/dashboard/incidents",
    );
  });

  it("permet de créer un autre incident après succès", async () => {
    render(<IncidentForm />);

    fillForm();

    await submitForm();

    const user = userEvent.setup();

    await user.click(
      await screen.findByRole("button", {
        name: "Créer un autre incident",
      }),
    );

    expect(
      screen.getByLabelText("Titre"),
    ).toHaveValue("");

    expect(
      screen.getByLabelText("Description"),
    ).toHaveValue("");

    expect(
      screen.getByLabelText("Catégorie"),
    ).toHaveValue("");

    expect(
      screen.getByLabelText("Priorité"),
    ).toHaveValue("MEDIUM");

    expect(
      screen.getByRole("button", {
        name: "Créer l’incident",
      }),
    ).toBeEnabled();
  });

  it("empêche une double soumission pendant l'enregistrement", async () => {
    let completeRequest:
      | ((value: typeof receipt) => void)
      | undefined;

    const pendingRequest = new Promise<
      typeof receipt
    >((resolve) => {
      completeRequest = resolve;
    });

    mocks.createIncident.mockReturnValueOnce(
      pendingRequest,
    );

    render(<IncidentForm />);

    fillForm();

    await submitForm();

    expect(
      screen.getByRole("button", {
        name: "Création en cours…",
      }),
    ).toBeDisabled();

    expect(
      screen.getByLabelText("Titre"),
    ).toBeDisabled();

    expect(
      screen.getByLabelText("Description"),
    ).toBeDisabled();

    expect(
      screen.queryByRole("link", {
        name: "Annuler",
      }),
    ).not.toBeInTheDocument();

    expect(
      mocks.createIncident,
    ).toHaveBeenCalledTimes(1);

    await act(async () => {
      completeRequest?.(receipt);
      await pendingRequest;
    });

    expect(
      await screen.findByText(
        "Création confirmée",
      ),
    ).toBeInTheDocument();

    expect(
      mocks.createIncident,
    ).toHaveBeenCalledTimes(1);
  });
});

// ======================================================
// 4. ERREURS API
// ======================================================

describe("IncidentForm - Erreurs API", () => {
  it("affiche les erreurs de validation retournées en 422", async () => {
    mocks.createIncident.mockRejectedValueOnce(
      makeApiError(422, [
        {
          loc: ["body", "title"],
          msg: "Invalid title",
        },
        {
          loc: ["body", "description"],
          msg: "Invalid description",
        },
        {
          loc: ["body", "category"],
          msg: "Invalid category",
        },
      ]),
    );

    render(<IncidentForm />);

    fillForm();

    await submitForm();

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "Certaines informations ont été refusées.",
    );

    expect(
      screen.getByLabelText("Titre"),
    ).toHaveAttribute(
      "aria-invalid",
      "true",
    );

    expect(
      screen.getByLabelText("Description"),
    ).toHaveAttribute(
      "aria-invalid",
      "true",
    );

    expect(
      screen.getByLabelText("Catégorie"),
    ).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });

  it("propose une reconnexion en cas d'erreur 401", async () => {
    mocks.createIncident.mockRejectedValueOnce(
      makeApiError(401),
    );

    render(<IncidentForm />);

    fillForm();

    await submitForm();

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "Votre session a expiré.",
    );

    expect(
      screen.getByRole("link", {
        name: "Se reconnecter",
      }),
    ).toHaveAttribute(
      "href",
      "/login?next=%2Fdashboard%2Fincidents%2Fnew",
    );
  });

  it("affiche une erreur d'autorisation en cas de 403", async () => {
    mocks.createIncident.mockRejectedValueOnce(
      makeApiError(403),
    );

    render(<IncidentForm />);

    fillForm();

    await submitForm();

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "Votre compte n’est pas autorisé",
    );
  });

  it("affiche une erreur serveur sans perdre la saisie", async () => {
    mocks.createIncident.mockRejectedValueOnce(
      makeApiError(500),
    );

    render(<IncidentForm />);

    fillForm();

    await submitForm();

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "La création n’a pas pu être confirmée.",
    );

    expect(
      screen.getByLabelText("Titre"),
    ).toHaveValue(validTitle);

    expect(
      screen.getByLabelText("Description"),
    ).toHaveValue(validDescription);

    expect(
      screen.getByLabelText("Catégorie"),
    ).toHaveValue(validCategory);
  });

  it("prévient du risque de doublon après une erreur réseau", async () => {
    mocks.createIncident.mockRejectedValueOnce(
      new Error("Network error"),
    );

    render(<IncidentForm />);

    fillForm();

    await submitForm();

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent(
      "L’incident a peut-être été créé",
    );

    expect(
      screen.getByLabelText("Titre"),
    ).toHaveValue(validTitle);
  });

  it("permet de réessayer après une erreur 422", async () => {
    mocks.createIncident
      .mockRejectedValueOnce(
        makeApiError(422, [
          {
            loc: ["body", "title"],
            msg: "Invalid title",
          },
        ]),
      )
      .mockResolvedValueOnce(receipt);

    render(<IncidentForm />);

    fillForm();

    await submitForm();

    expect(
      await screen.findByRole("alert"),
    ).toBeInTheDocument();

    await submitForm();

    expect(
      await screen.findByText(
        "Création confirmée",
      ),
    ).toBeInTheDocument();

    expect(
      mocks.createIncident,
    ).toHaveBeenCalledTimes(2);
  });
});
