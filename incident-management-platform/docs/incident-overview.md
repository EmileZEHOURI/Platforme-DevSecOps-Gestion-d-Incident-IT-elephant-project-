# Suivi des incidents sur le tableau de bord

## Interface et périmètre

La section provisoire est remplacée par IncidentOverview sur /dashboard.
La page / redirige déjà vers /dashboard.
Le tableau, les badges, les filtres, la pagination et les états utilisent les composants existants.
Référence cliquable, titre, catégorie, priorité, statut et date de création sont affichés.
Le tableau conserve son défilement horizontal accessible sur les petits écrans.
Le reste du tableau de bord, dont ses indicateurs provisoires, est conservé.

| Rôle | Titre | Données |
|---|---|---|
| USER | Mes incidents | Ses déclarations, tous statuts |
| TECHNICIAN | Mes incidents | Ses affectations par défaut ; bouton Mes déclarations |
| ADMIN | Suivi des incidents | Tous les incidents autorisés par la vue administrateur |

## API et sécurité

- USER / déclarations : GET /incidents?page=1&page_size=10.
- Affectations : GET /incidents/assigned?page=1&page_size=10.
- Administration : GET /incidents/all?page=1&page_size=10.
- Tous les appels utilisent le helper existant, /api/backend et credentials: include.
- Aucun created_by_id n'est envoyé par le frontend. Le backend utilise current_user.id.
- Les routes /assigned et /all et leurs contrôles RBAC ne sont pas modifiés.

La pagination des déclarations n'existait pas. Elle est ajoutée en option à GET /incidents,
sans nouvelle route : sans page, la réponse reste une liste pour les clients existants.
Avec page, la réponse est PaginatedIncidentsResponse. Filtrage et LIMIT/OFFSET sont SQL.
Filtres : statut, priorité, catégorie. Ordre : created_at DESC, id DESC.
10 incidents par défaut ; sélecteur existant 10/20/50/100.
Un changement de filtre ou taille revient à la page 1. Une page devenue vide au-delà
de la dernière page revient à celle-ci.

Les réponses obsolètes sont ignorées et les requêtes annulées au démontage.
Un changement d'identité, de rôle ou de périmètre réinitialise la vue.
Chargement, vide adapté au rôle, absence de résultat, erreur avec Réessayer,
401 avec lien Se reconnecter sont traités séparément. Aucun retry automatique sur 401.

## Fichiers

Créés :
- frontend/src/components/incident-overview.tsx
- frontend/tests/incident-overview.test.tsx
- backend/tests/api/test_created_incident_pagination.py
- docs/incident-overview.md

Modifiés :
- frontend/src/app/dashboard/page.tsx
- frontend/src/app/globals.css
- frontend/src/services/incident.service.ts
- frontend/e2e/lifecycle.spec.ts
- backend/app/api/routes/incidents.py
- backend/app/repositories/incident_repository.py
- backend/app/services/incident_service.py
- backend/app/schemas/audit.py : uniquement rangement des imports pour Ruff ;
  les modifications fonctionnelles préexistantes de l'utilisateur sont conservées.

.env.docker.example préexistant est inchangé. Aucun secret, fichier .env,
migration ou règle de permission n'a été modifié.

## Validations du 27 novembre 2026

- npm test : 173 tests réussis dans 13 fichiers, dont 12 nouveaux (16.02 s).
- npm run lint : réussi.
- npx tsc --noEmit : réussi.
- npm run build : réussi, également dans Docker.
- PLAYWRIGHT_CHANNEL=msedge npm run test:e2e : 1 parcours réussi (27.3 s).
  Vérification des trois rôles sur le dashboard, lien réel vers le détail,
  largeur mobile 390 px sans débordement du document, et cycle métier existant.
- uv run ruff check backend depuis la racine (via uv run --project backend) :
  All checks passed!
- uv run --env-file .env.test pytest -q --tb=short -rs :
  665 passed, 3 warnings in 73.51s, Redis réel activé avec
  RUN_REAL_REDIS_TESTS=1 et TEST_REVOCATION_REDIS_URL=redis://127.0.0.1:6380/0.
- git diff --check : réussi.

Les nouveaux tests backend utilisent une vraie connexion et PostgreSQL :
isolement des déclarations pour les trois rôles, filtres, pagination,
tri déterministe, compatibilité de la liste historique, validation et absence de session.
Les tests existants continuent de vérifier les permissions des endpoints /all et /assigned.

Les premiers essais ont détecté des erreurs dans les nouvelles fixtures de test,
corrigées sans affaiblir les contraintes de la base. Les résultats ci-dessus sont
ceux des dernières exécutions.

## Docker et vérification locale

docker compose --env-file .env.docker up -d --build frontend backend : réussi.
Le dossier bin de Docker Desktop a été ajouté au PATH de la commande uniquement.
Frontend, backend, PostgreSQL et Redis sont healthy.
http://localhost:3000 répond 200.
GET http://localhost:3000/api/backend/incidents?page=1&page_size=10 sans session
répond 401 application/json, confirmant le proxy et la protection de la route.
Le parcours authentifié est validé par Playwright avec des utilisateurs de test isolés.

Trois avertissements backend préexistants restent présents :
dépréciation httpx/TestClient, ancien nom HTTP 422 et clé courte du test négatif JWT.
