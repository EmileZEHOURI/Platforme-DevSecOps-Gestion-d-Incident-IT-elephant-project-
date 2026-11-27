# État de validation — 26 novembre 2026

## Résultats vérifiés

| Contrôle | Résultat |
| --- | --- |
| Backend `uv run --env-file .env.test pytest -q --tb=short -rs` | 573 tests réussis, 3 avertissements |
| Frontend `npm run test` | 161 tests réussis, 12 fichiers |
| Frontend `npm run lint` | Réussi |
| Frontend `npx tsc --noEmit` (binaire local exécuté directement) | Réussi |
| Frontend `npm run build` | Réussi, Next.js 16.4.6 |
| Playwright, API FastAPI et PostgreSQL réels | 1 parcours multi-rôle réussi, Edge Chromium |

Ces chiffres ne constituent pas un pourcentage de couverture des lignes. Aucun instrumenteur de couverture n'a été installé ou exécuté.

## Architecture réellement examinée

- Next.js App Router : pages sous `frontend/src/app`, shell et contrôle de session dans `app-shell.tsx` et `auth-provider.tsx`.
- Composants métier sous `src/components`, services HTTP sous `src/services`, types sous `src/types`.
- `src/lib/api.ts` centralise les requêtes vers `/api/backend`, avec cookie, `credentials: include`, absence de cache et délai maximal.
- Les réécritures Next.js relaient les appels vers FastAPI. L'annuaire des techniciens possède une route Next.js spécifique avec vérification ADMIN et compatibilité `/auth/technicians`.
- Les autorisations d'affichage réutilisent les règles de `permissions.ts`; la sécurité finale reste dans FastAPI.
- Les listes utilisent l'état React, AbortController et des gardes contre les réponses obsolètes. Aucun cache global de données métier.
- L'historique relit l'API après les notifications des services de mutation. Les commentaires affichés sont uniquement ceux ajoutés pendant la consultation, limitation explicitement indiquée dans l'interface.
- Vitest utilise jsdom, React Testing Library et un nettoyage après chaque test. Les trois suites proposées (filtres, pagination et page détail) étaient présentes et passaient déjà : 130 tests initiaux, et non seulement 80.

## Ajouts de cette étape

`tests/incident-detail.integration.test.tsx` ajoute 19 cas : session, détail, erreurs 401/403/404/422/500, nouvelle tentative, annulation des requêtes, absence de remplacement par une réponse ancienne, commentaires, limites, conservation des saisies, conflit de fermeture, cycle prise en charge/résolution/clôture, assignation ADMIN, permissions et double soumission.

`tests/admin.integration.test.tsx` ajoute 12 cas : refus des rôles non ADMIN, détails d'un utilisateur sans endpoint inventé, comptes ADMIN protégés, activation/désactivation avec confirmation et filtres conservés, conflit technicien, pagination et priorité des incidents, filtres temporels d'audit, détails JSON masqués et erreurs API.

Ces suites gardent les composants, hooks métier, permissions, services et client HTTP réels. Seules la session, la navigation Next.js et la frontière HTTP sont simulées. Les méthodes natives `showModal`/`close`, absentes de jsdom, ont un adaptateur limité au support des tests. Playwright valide les dialogues dans un vrai navigateur.

Correction de test : apostrophe JSX non échappée dans `incident-detail-page.test.tsx`. Aucun assouplissement des assertions existantes. Les modifications préexistantes de `incident-filters-bar.tsx`, `new-incident-page.test.tsx` et les suites non suivies ont été conservées.

## Exécuter les contrôles

Depuis `frontend` :

```powershell
npm ci
npm run test
npm run lint
npx tsc --noEmit
npm run build
```

Depuis `backend` :

```powershell
uv run --env-file .env.test pytest -q --tb=short -rs
```

## Tests de bout en bout réels

Prérequis : PostgreSQL disponible, dépendances backend installées avec uv, Node.js, dépendances frontend, ports 8017 et 3017 libres.

Le fichier local `backend/.env.test`, non versionné, doit fournir `TEST_DATABASE_URL` vers une base PostgreSQL dont le nom finit par `_test`, distincte de `DATABASE_URL`. Utiliser un compte disposant du droit de créer et supprimer ses propres schémas dans cette base de test. Ne pas utiliser de base de production.

Depuis `frontend` :

```powershell
npx playwright install chromium
npm run test:e2e
```

Sur cette machine Windows, Edge installé a été utilisé :

```powershell
$env:PLAYWRIGHT_CHANNEL = 'msedge'
npm run test:e2e
Remove-Item Env:PLAYWRIGHT_CHANNEL
```

`e2e/run.py` valide la cible, crée un schéma `e2e_<uuid>`, crée trois comptes de test, démarre FastAPI sur 8017 puis Playwright. Le serveur Next.js démarre sur 3017 avec un dossier de compilation distinct `.next-e2e`. Aucun serveur déjà présent sur ces ports n'est réutilisé. La clé JWT est générée pour chaque exécution. Les identifiants du scénario sont publics et exclusivement destinés à cet environnement jetable.

Le parcours couvre : connexion réelle et cookie HttpOnly, création, liste et détail, commentaire, assignation ADMIN, prise en charge et résolution par le technicien depuis sa liste assignée, clôture par le créateur, historique, audit ADMIN, refus UI et HTTP 403 d'un utilisateur ordinaire.

Le lanceur arrête FastAPI et supprime uniquement son schéma dans un bloc `finally`. Un arrêt brutal du processus ou de la machine peut laisser un schéma temporaire : contrôler les schémas `e2e_*` dans la base de test avant un nettoyage manuel, sans supprimer les autres données. Les traces en échec et journaux locaux sont ignorés par Git. Ne pas publier de traces issues d'un environnement contenant de vraies données.

## Limites et priorités restantes

1. **Accès au détail des techniciens/ADMIN non créateurs** : `get_incident_detail` interroge encore `get_by_id_and_creator`. Le parcours réel fonctionne depuis les listes opérationnelles, mais l'ouverture du détail par un technicien assigné peut renvoyer 404 alors que l'historique lui est accessible. Décider et tester un contrat d'accès cohérent avant modification.
2. **Couverture non exhaustive** : ces suites couvrent les parcours prioritaires. Restent notamment des tests ciblés du renouvellement de session, du relais d'annuaire, de toutes les branches d'erreurs des dialogues, des changements de rôle en cours de requête et de l'accessibilité clavier complète. Le test Playwright ne couvre pas encore chaque erreur et filtre des 16 US sur API réelle.
3. **Avertissements backend** : migration Starlette/HTTPX, renommage de la constante 422 dépréciée, clé de signature courte dans un test négatif. Les tests passent mais ces avertissements restent à traiter.
4. **Versions** : Next.js est 16.4.6, tandis qu'`eslint-config-next` est encore 16.2.12. Les vérifications passent; aligner les versions lors d'une mise à jour dédiée.
5. **Sécurité à auditer** : stratégie CSRF/CORS selon le déploiement, cookies en HTTPS, expiration/révocation des sessions, limitation des essais de connexion, données d'audit exposées et gestion des secrets. Le masquage JSON côté frontend reste une aide d'affichage, jamais une protection des réponses réseau.
6. **Docker, CI/CD, déploiement et documentation portfolio** : étapes non réalisées dans ce lot de validation. Préparer ensuite la reproductibilité de l'environnement et l'exécution de ces commandes en CI avant de publier une instance.

Le build Next.js peut réécrire son bloc de consignes dans `AGENTS.md` et ajouter les chemins `.next-e2e` à TypeScript. ESLint ignore ces artefacts générés, sans ignorer le code source ni les tests.
