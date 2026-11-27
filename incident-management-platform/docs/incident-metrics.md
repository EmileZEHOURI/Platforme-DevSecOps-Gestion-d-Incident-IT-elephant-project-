# Indicateurs d'incidents — 27 novembre 2026

## Calcul et périmètre

Les quatre cartes existantes sont conservées :
- Incidents ouverts : status=OPEN.
- En cours : status=IN_PROGRESS.
- Critiques actifs : priority=CRITICAL et status OPEN ou IN_PROGRESS.
- Résolus : status=RESOLVED uniquement, sans CLOSED.

Les compteurs se recouvrent : un critique actif est aussi ouvert ou en cours.
Source : total des réponses paginées, calculé côté PostgreSQL.
Le nombre de lignes de la page n'est jamais utilisé comme compteur.

USER : GET /incidents, ses déclarations.
TECHNICIAN : GET /incidents/assigned, ses affectations.
ADMIN : GET /incidents/all, toute la plateforme selon les permissions existantes.

Cinq requêtes parallèles par rafraîchissement (deux pour les critiques actifs),
chacune avec page=1&page_size=1 et les filtres nécessaires.
Cela réutilise les services et les contrôles RBAC existants sans nouvelle API,
ni téléchargement intégral des incidents.
Les totaux sont ceux de chaque requête, sans garantie de snapshot transactionnel
commun si des modifications concurrentes interviennent entre les cinq lectures.

## Rafraîchissement et états

Le composant est réinitialisé au changement d'identité ou de rôle.
Il recharge au montage, sur Actualiser, au retour de focus et via
subscribeIncidentUpdates après les mutations existantes.
La création émet désormais également notifyIncidentUpdate après succès.
Les anciennes réponses sont ignorées et les requêtes annulées au démontage.
Les compteurs du technicien restent ses affectations même lorsqu'il consulte
l'onglet Mes déclarations du tableau, conformément au périmètre demandé.

Chargement discret, vrais zéros, erreur avec nouvelle tentative.
Aucun résultat partiel n'est présenté comme une réussite complète.
Un 401 propose la reconnexion ; focus et mutations ne relancent plus les requêtes
tant que cette session reste expirée.
Les appels utilisent /api/backend, credentials: include et cache: no-store.

## Fichiers de cette mission

Créés :
- frontend/src/components/incident-metrics.tsx
- frontend/tests/incident-metrics.test.tsx
- docs/incident-metrics.md

Modifiés :
- frontend/src/app/dashboard/page.tsx
- frontend/src/services/incident.service.ts
- frontend/src/lib/incident-updates.ts (commentaire descriptif)
- frontend/e2e/lifecycle.spec.ts

Aucun fichier backend, secret, fichier .env ou règle RBAC modifié par cette mission.
Les modifications déjà présentes, notamment IncidentOverview et sa pagination,
sont conservées.

## Vérifications réellement exécutées

- npm test : 183 tests réussis, 14 fichiers (12.37 s).
- Après correction de typage du test : npm test -- --run tests/incident-metrics.test.tsx,
  10 tests réussis (2.89 s).
- npm run lint : réussi.
- npx tsc --noEmit : réussi.
- npm run build : réussi.
- PLAYWRIGHT_CHANNEL=msedge npm run test:e2e :
  1 parcours réussi (22.5 s), incluant comparaison des quatre cartes avec les totaux
  réels FastAPI pour USER, TECHNICIAN et ADMIN.
- git diff --check : aucune erreur.
- Backend non modifié : pytest et Ruff non relancés pour cette mission.

Les tests couvrent les valeurs multi-pages, zéro, chargement, erreur partielle,
reconnexion, chacun des trois endpoints, correspondance des enums, refresh,
création et rejet des réponses devenues obsolètes.

## Docker

docker compose --env-file .env.docker up -d --build frontend : réussi.
Le PATH de la commande inclut le dossier bin de Docker Desktop.
Les services frontend, backend, PostgreSQL et Redis sont healthy.
http://localhost:3000 répond 200.
Les trois endpoints de compteurs via /api/backend répondent 401 sans session.

Limite de vérification : les trois rôles ont été testés par Playwright dans
l'environnement isolé sur 3017 avec PostgreSQL réel, pas avec les comptes personnels
de la base Docker sur 3000. Sur 3000, la disponibilité et le proxy protégé ont été
vérifiés sans connexion à ces comptes.
