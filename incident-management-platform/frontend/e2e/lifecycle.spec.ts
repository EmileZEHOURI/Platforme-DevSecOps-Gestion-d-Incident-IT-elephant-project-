
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
  "real user → admin assignment → technician detail and resolution → creator closure → audit",
  async ({ browser }) => {
    const userContext = await browser.newContext();
    const adminContext = await browser.newContext();
    const techContext = await browser.newContext();

    const user = await userContext.newPage();
    const admin = await adminContext.newPage();
    const tech = await techContext.newPage();

    try {
      // 1. CONNEXION UTILISATEUR
      await login(user, "user");

      const cookie = (await userContext.cookies()).find(
        (c) => c.name === "access_token",
      );

      expect(cookie?.httpOnly).toBe(true);

      // 2. CRÉATION D'UN INCIDENT
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

      const detailPageUrl = `/dashboard/incidents/${incident.id}`;
      const detailApiUrl = `/api/backend/incidents/${incident.id}`;

      // 3. LE CRÉATEUR CONSULTE SON INCIDENT
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

      // 4. AJOUT D'UN COMMENTAIRE
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

      // 5. TEST DE SÉCURITÉ AVANT ASSIGNATION
      // Le technicien n'est ni créateur ni assigné.

      await login(tech, "technician");

      const deniedResponse = await tech.request.get(
        detailApiUrl,
      );

      expect(deniedResponse.status()).toBe(404);

      // Vérification également dans le navigateur.
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

      // 6. ASSIGNATION PAR L'ADMINISTRATEUR
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

      // 7. TEST DE LA CORRECTION GET_INCIDENT_DETAIL
      // Le même technicien est maintenant assigné.

      const allowedResponse = await tech.request.get(
        detailApiUrl,
      );

      expect(allowedResponse.status()).toBe(200);

      const assignedIncident = await allowedResponse.json();

      expect(assignedIncident.id).toBe(incident.id);
      expect(assignedIncident.reference).toBe(
        incident.reference,
      );
      expect(assignedIncident.title).toBe(incidentTitle);

      // Vérification dans la véritable interface Next.js.
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

      // 8. PRISE EN CHARGE PAR LE TECHNICIEN
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

      // 9. RÉSOLUTION PAR LE TECHNICIEN
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

      // 10. CLÔTURE PAR LE CRÉATEUR
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

      // 11. VÉRIFICATION DE L'HISTORIQUE
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

      // 12. AUDIT ADMIN
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

      // 13. INTERDICTION D'ACCÈS ADMIN POUR USER
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
    } finally {
      await userContext.close();
      await adminContext.close();
      await techContext.close();
    }
  },
);
