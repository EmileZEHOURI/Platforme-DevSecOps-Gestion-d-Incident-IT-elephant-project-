
import { test, expect, type Page } from "@playwright/test";

async function login(page: Page, role: string) {
  await page.goto("/login");

  await page
    .getByLabel("Adresse électronique")
    .fill(`${role}@e2e.example.com`);

  await page
    .getByLabel("Mot de passe", { exact: true })
    .fill("e2e-only-password");

  await page
    .getByRole("button", {
      name: "Se connecter",
      exact: true,
    })
    .click();

  await expect(page).toHaveURL(/\/dashboard$/);
}

test(
  "real lifecycle with permissions, CSRF and audit",
  async ({ browser }) => {
    const userContext = await browser.newContext();
    const adminContext = await browser.newContext();
    const techContext = await browser.newContext();

    const user = await userContext.newPage();
    const admin = await adminContext.newPage();
    const tech = await techContext.newPage();

    try {
      // ===================================
      // 1. AUTHENTIFICATION USER
      // ===================================

      await login(user, "user");

      const cookie = (await userContext.cookies()).find(
        (c) => c.name === "access_token",
      );

      expect(cookie?.httpOnly).toBe(true);

      // ===================================
      // 2. NOUVEAU : TESTS CSRF
      // ===================================

      const csrfCases: {
        name: string;
        headers: Record<string, string>;
      }[] = [
        {
          name: "Origine étrangère",
          headers: {
            Origin: "https://attacker.example",
          },
        },
        {
          name: "Referer étranger",
          headers: {
            Referer: "https://attacker.example/page",
          },
        },
        {
          name: "Origine opaque",
          headers: {
            Origin: "null",
          },
        },
        {
          name: "Origin étranger malgré un Referer autorisé",
          headers: {
            Origin: "https://attacker.example",
            Referer: "http://127.0.0.1:3017/dashboard",
          },
        },
      ];

      for (const scenario of csrfCases) {
        const csrfResponse = await user.request.post(
          "/api/backend/auth/logout",
          {
            headers: scenario.headers,
          },
        );

        expect(
          csrfResponse.status(),
          scenario.name,
        ).toBe(403);

        expect(
          (await csrfResponse.json()).detail,
        ).toBe("Origine de la requête non autorisée.");
      }

      // Les tentatives bloquées ne doivent
      // pas avoir déconnecté l'utilisateur.

      const sessionAfterCsrf = await user.request.get(
        "/api/backend/auth/me",
      );

      expect(sessionAfterCsrf.status()).toBe(200);

      // ===================================
      // 3. CRÉATION D'INCIDENT
      // ===================================

      const incidentTitle = "E2E panne du portail";

      await user.goto("/dashboard/incidents/new");

      await user
        .getByLabel("Titre", { exact: true })
        .fill(incidentTitle);

      await user
        .getByLabel("Description", { exact: true })
        .fill("Le portail ne répond plus aux demandes.");

      await user
        .getByLabel("Catégorie", { exact: true })
        .selectOption("ANOMALY");

      const created = user.waitForResponse(
        (r) =>
          r.url().endsWith("/api/backend/incidents") &&
          r.request().method() === "POST",
      );

      await user
        .getByRole("button", {
          name: "Créer l’incident",
          exact: true,
        })
        .click();

      const response = await created;

      expect(response.status()).toBe(201);

      const incident = await response.json();

      const detailPageUrl =
        `/dashboard/incidents/${incident.id}`;

      const detailApiUrl =
        `/api/backend/incidents/${incident.id}`;

      // ===================================
      // 4. DÉTAIL ET COMMENTAIRE USER
      // ===================================

      await user.goto("/dashboard/incidents");

      await user
        .getByRole("link", {
          name: `Voir le détail de ${incident.reference}`,
        })
        .click();

      await expect(
        user.getByRole("heading", {
          name: incidentTitle,
          exact: true,
        }),
      ).toBeVisible();

      await user
        .getByLabel("Ajouter un commentaire")
        .fill("Reproduction confirmée par le demandeur.");

      await user
        .getByRole("button", {
          name: "Ajouter le commentaire",
          exact: true,
        })
        .click();

      await expect(
        user.getByText(
          "Commentaire ajouté avec succès.",
          { exact: true },
        ),
      ).toBeVisible();

      // ===================================
      // 5. TECHNICIEN NON ENCORE ASSIGNÉ
      // ===================================

      await login(tech, "technician");

      const deniedResponse = await tech.request.get(
        detailApiUrl,
      );

      expect(deniedResponse.status()).toBe(404);

      const deniedPageResponse = tech.waitForResponse(
        (r) =>
          new URL(r.url()).pathname === detailApiUrl &&
          r.request().method() === "GET",
      );

      await tech.goto(detailPageUrl);

      expect(
        (await deniedPageResponse).status(),
      ).toBe(404);

      await expect(
        tech.getByRole("heading", {
          name: incidentTitle,
          exact: true,
        }),
      ).toHaveCount(0);

      // ===================================
      // 6. ASSIGNATION ADMIN
      // ===================================

      await login(admin, "admin");

      await admin.goto("/dashboard/admin/incidents");

      const adminRow = admin
        .getByRole("row")
        .filter({ hasText: incident.reference });

      await adminRow
        .getByRole("button", {
          name: "Assigner",
          exact: true,
        })
        .click();

      await admin
        .getByLabel("Nouveau responsable")
        .selectOption({
          label:
            "E2E TECHNICIAN — technician@e2e.example.com",
        });

      await admin
        .getByRole("button", {
          name: "Confirmer",
          exact: true,
        })
        .click();

      await expect(
        admin.getByRole("dialog"),
      ).toHaveCount(0);

      // ===================================
      // 7. TECHNICIEN ASSIGNÉ : ACCÈS 200
      // ===================================

      const allowedResponse = await tech.request.get(
        detailApiUrl,
      );

      expect(allowedResponse.status()).toBe(200);

      const assignedIncident =
        await allowedResponse.json();

      expect(assignedIncident.id).toBe(incident.id);

      expect(assignedIncident.reference).toBe(
        incident.reference,
      );

      expect(assignedIncident.title).toBe(incidentTitle);

      const allowedPageResponse = tech.waitForResponse(
        (r) =>
          new URL(r.url()).pathname === detailApiUrl &&
          r.request().method() === "GET",
      );

      await tech.goto(detailPageUrl);

      expect(
        (await allowedPageResponse).status(),
      ).toBe(200);

      await expect(
        tech.getByRole("heading", {
          name: incidentTitle,
          exact: true,
        }),
      ).toBeVisible();

      // ===================================
      // 8. PRISE EN CHARGE
      // ===================================

      await tech.goto("/dashboard/incidents/assigned");

      const techRow = tech
        .getByRole("row")
        .filter({ hasText: incident.reference });

      await techRow
        .getByRole("button", {
          name: "Commencer le traitement",
          exact: true,
        })
        .click();

      // ===================================
      // 9. RÉSOLUTION
      // ===================================

      await techRow
        .getByRole("button", {
          name: "Résoudre l’incident",
          exact: true,
        })
        .click();

      await tech
        .getByLabel("Description de la résolution")
        .fill(
          "Service redémarré et fonctionnement vérifié.",
        );

      await tech
        .getByRole("button", {
          name: "Confirmer la résolution",
          exact: true,
        })
        .click();

      await expect(
        tech.getByRole("dialog"),
      ).toHaveCount(0);

      // ===================================
      // 10. CLÔTURE PAR LE CRÉATEUR
      // ===================================

      await user.goto(detailPageUrl);

      await user
        .getByRole("button", {
          name: "Clôturer l’incident",
          exact: true,
        })
        .click();

      await user
        .getByRole("button", {
          name: "Confirmer la clôture",
          exact: true,
        })
        .click();

      await expect(
        user.getByLabel("Ajouter un commentaire"),
      ).toBeDisabled();

      // ===================================
      // 11. HISTORIQUE
      // ===================================

      const history = user.getByRole("region", {
        name: "Historique de l’incident",
      });

      await expect(
        history.getByRole("heading", {
          name: "Incident clôturé",
          exact: true,
        }),
      ).toBeVisible();

      await expect(
        history.getByRole("heading", {
          name: "Commentaire ajouté",
          exact: true,
        }),
      ).toBeVisible();

      // ===================================
      // 12. AUDIT ADMIN
      // ===================================

      await admin.goto("/dashboard/admin/audit-logs");

      await admin
        .getByLabel("Événement", { exact: true })
        .selectOption("INCIDENT_CLOSED");

      await expect(
        admin
          .getByRole("table")
          .getByText("Incident clôturé", {
            exact: true,
          }),
      ).toBeVisible();

      // ===================================
      // 13. CONTRÔLE D'ACCÈS ADMIN
      // ===================================

      await user.goto("/dashboard/admin/users");

      await expect(
        user.getByRole("heading", {
          name: "Accès refusé",
          exact: true,
        }),
      ).toBeVisible();

      const forbidden = await user.request.get(
        "/api/backend/users",
      );

      expect(forbidden.status()).toBe(403);

      // ===================================
      // 14. NOUVEAU : DÉCONNEXION AUTORISÉE
      // ===================================

      const logoutResponse = await user.request.post(
        "/api/backend/auth/logout",
        {
          headers: {
            Origin: "http://127.0.0.1:3017",
          },
        },
      );

      expect(logoutResponse.status()).toBe(200);

      // Après suppression du cookie,
      // la session doit être invalide.

      const sessionAfterLogout = await user.request.get(
        "/api/backend/auth/me",
      );

      expect(sessionAfterLogout.status()).toBe(401);
    } finally {
      await userContext.close();
      await adminContext.close();
      await techContext.close();
    }
  },
);
