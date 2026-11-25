import type { ComponentProps } from "react";

import { beforeEach, describe, expect, it, vi } from "vitest";

import { render, screen, waitFor } from "@testing-library/react";

import userEvent from "@testing-library/user-event";

import LoginPage from "@/app/login/page";
import { ApiError } from "@/lib/api";

const mocks = vi.hoisted(() => ({
  login: vi.fn(),
  getMe: vi.fn(),
  replace: vi.fn(),
}));

// Simuler la navigation Next.js
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: mocks.replace,
  }),
}));

// Simuler les appels d'authentification
vi.mock("@/services/auth.service", () => ({
  login: mocks.login,
  getMe: mocks.getMe,
}));

// Isoler les composants UI afin de tester LoginPage
vi.mock("@/components/ui", () => ({
  Brand: () => <div>Incident Management Platform</div>,

  Button: ({ children, ...props }: ComponentProps<"button">) => (
    <button {...props}>{children}</button>
  ),
}));

// Simuler ApiError sans dépendre de son constructeur réel
vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {
    status = 0;
  },
}));

function unauthorizedError() {
  const error = new Error("Unauthorized") as Error & {
    status: number;
  };

  Object.setPrototypeOf(error, ApiError.prototype);
  error.status = 401;

  return error;
}

async function renderLoggedOut() {
  render(<LoginPage />);

  await waitFor(() => {
    expect(mocks.getMe).toHaveBeenCalledTimes(1);
  });
}

async function fillLoginForm() {
  const user = userEvent.setup();

  await user.type(
    screen.getByLabelText("Adresse électronique"),
    "test@example.com",
  );

  await user.type(screen.getByLabelText("Mot de passe"), "Password123!");

  return user;
}

function mockGetMeAfterLogin(result: { is_active: boolean } | Error) {
  mocks.getMe.mockImplementation(() => {
    // Avant la connexion, aucune session n'existe.
    if (mocks.login.mock.calls.length === 0) {
      return Promise.reject(new Error("Utilisateur non connecté"));
    }

    // Après la connexion, simuler la réponse souhaitée.
    if (result instanceof Error) {
      return Promise.reject(result);
    }

    return Promise.resolve(result);
  });
}

beforeEach(() => {
  vi.resetAllMocks();

  window.history.replaceState({}, "", "/login");

  // Au chargement, aucune session n'est active.
  mocks.getMe.mockRejectedValue(new Error("Utilisateur non connecté"));

  mocks.login.mockResolvedValue(undefined);
});

describe("LoginPage - Affichage", () => {
  it("affiche le formulaire de connexion", async () => {
    await renderLoggedOut();

    expect(screen.getByLabelText("Adresse électronique")).toBeInTheDocument();

    expect(screen.getByLabelText("Mot de passe")).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Se connecter",
      }),
    ).toBeInTheDocument();
  });

  it("masque le mot de passe par défaut", async () => {
    await renderLoggedOut();

    const password = screen.getByLabelText("Mot de passe");

    expect(password).toHaveAttribute("type", "password");
  });

  it("permet d'afficher et de masquer le mot de passe", async () => {
    await renderLoggedOut();

    const user = userEvent.setup();

    const password = screen.getByLabelText("Mot de passe");

    await user.click(
      screen.getByRole("button", {
        name: "Afficher le mot de passe",
      }),
    );

    expect(password).toHaveAttribute("type", "text");

    await user.click(
      screen.getByRole("button", {
        name: "Masquer le mot de passe",
      }),
    );

    expect(password).toHaveAttribute("type", "password");
  });

  it("ne soumet pas un formulaire vide", async () => {
    await renderLoggedOut();

    const user = userEvent.setup();

    await user.click(
      screen.getByRole("button", {
        name: "Se connecter",
      }),
    );

    expect(mocks.login).not.toHaveBeenCalled();
  });
});

describe("LoginPage - Authentification", () => {
  it("connecte l'utilisateur et redirige vers le dashboard", async () => {
    await renderLoggedOut();

    mocks.getMe.mockResolvedValueOnce({
      is_active: true,
    });

    const user = await fillLoginForm();

    await user.click(
      screen.getByRole("button", {
        name: "Se connecter",
      }),
    );

    await waitFor(() => {
      expect(mocks.login).toHaveBeenCalledWith(
        "test@example.com",
        "Password123!",
      );

      expect(mocks.replace).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("redirige vers la page demandée après connexion", async () => {
    window.history.replaceState(
      {},
      "",
      "/login?next=%2Fdashboard%2Fadmin%2Fusers",
    );

    await renderLoggedOut();

    mocks.getMe.mockResolvedValueOnce({
      is_active: true,
    });

    const user = await fillLoginForm();

    await user.click(
      screen.getByRole("button", {
        name: "Se connecter",
      }),
    );

    await waitFor(() => {
      expect(mocks.replace).toHaveBeenCalledWith("/dashboard/admin/users");
    });
  });

  it.each(["https://evil.example", "//evil.example", "/dashboard/../../admin"])(
    "refuse une redirection non autorisée : %s",
    async (next) => {
      window.history.replaceState(
        {},
        "",
        `/login?next=${encodeURIComponent(next)}`,
      );

      await renderLoggedOut();

      mocks.getMe.mockResolvedValueOnce({
        is_active: true,
      });

      const user = await fillLoginForm();

      await user.click(
        screen.getByRole("button", {
          name: "Se connecter",
        }),
      );

      await waitFor(() => {
        expect(mocks.replace).toHaveBeenCalledWith("/dashboard");
      });
    },
  );

  it("redirige automatiquement un utilisateur déjà connecté", async () => {
    mocks.getMe.mockResolvedValue({
      is_active: true,
    });

    render(<LoginPage />);

    await waitFor(() => {
      expect(mocks.replace).toHaveBeenCalledWith("/dashboard");
    });

    expect(mocks.login).not.toHaveBeenCalled();
  });

  it("affiche une erreur lorsque les identifiants sont incorrects", async () => {
    await renderLoggedOut();

    mocks.login.mockRejectedValueOnce(unauthorizedError());

    const user = await fillLoginForm();

    await user.click(
      screen.getByRole("button", {
        name: "Se connecter",
      }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Adresse électronique ou mot de passe incorrect.",
    );

    expect(mocks.replace).not.toHaveBeenCalled();
  });

  it("affiche une erreur si la session ne peut pas être conservée", async () => {
    mockGetMeAfterLogin(unauthorizedError());

    await renderLoggedOut();

    const user = await fillLoginForm();

    await user.click(
      screen.getByRole("button", {
        name: "Se connecter",
      }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Identifiants acceptés, mais la session",
    );

    expect(mocks.login).toHaveBeenCalledTimes(1);

    expect(mocks.replace).not.toHaveBeenCalled();
  });

  it("refuse la connexion d'un compte désactivé", async () => {
    mockGetMeAfterLogin({
      is_active: false,
    });

    await renderLoggedOut();

    const user = await fillLoginForm();

    await user.click(
      screen.getByRole("button", {
        name: "Se connecter",
      }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Ce compte ne peut pas accéder à la plateforme.",
    );

    expect(mocks.login).toHaveBeenCalledTimes(1);

    expect(mocks.replace).not.toHaveBeenCalled();
  });

  it("affiche une erreur générique en cas d'échec réseau", async () => {
    await renderLoggedOut();

    mocks.login.mockRejectedValueOnce(
      new Error("Erreur de connexion au serveur"),
    );

    const user = await fillLoginForm();

    await user.click(
      screen.getByRole("button", {
        name: "Se connecter",
      }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Erreur de connexion au serveur",
    );

    expect(mocks.replace).not.toHaveBeenCalled();
  });
});

describe("LoginPage - Chargement", () => {
  it("désactive le formulaire pendant la connexion", async () => {
    await renderLoggedOut();

    let finishLogin: (() => void) | undefined;

    const pendingLogin = new Promise<void>((resolve) => {
      finishLogin = resolve;
    });

    mocks.login.mockReturnValueOnce(pendingLogin);

    mocks.getMe.mockResolvedValueOnce({
      is_active: true,
    });

    const user = await fillLoginForm();

    await user.click(
      screen.getByRole("button", {
        name: "Se connecter",
      }),
    );

    expect(
      screen.getByRole("button", {
        name: "Connexion en cours…",
      }),
    ).toBeDisabled();

    expect(screen.getByLabelText("Adresse électronique")).toBeDisabled();

    expect(screen.getByLabelText("Mot de passe")).toBeDisabled();

    expect(mocks.login).toHaveBeenCalledTimes(1);

    finishLogin?.();

    await waitFor(() => {
      expect(mocks.replace).toHaveBeenCalledWith("/dashboard");
    });
  });
});
