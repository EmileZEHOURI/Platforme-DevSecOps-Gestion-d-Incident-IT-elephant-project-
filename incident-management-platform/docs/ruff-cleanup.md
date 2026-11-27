# Nettoyage Ruff — 27 novembre 2026

## Résultat

86 erreurs initiales, 0 restante : `All checks passed!`.
37 fichiers Python modifiés pour ce nettoyage, plus ce rapport.
Les changements préexistants de révocation JWT et E2E ont été conservés.

| Règle | Nombre initial | Correction |
|---|---:|---|
| UP017 | 51 | datetime.UTC remplace timezone.utc |
| I001 | 29 | Organisation des imports |
| F811 | 3 | Une méthode masquée retirée, tests renommés |
| E402 | 1 | Import pytest déplacé en tête de module |
| F401 | 1 | Import SessionLocal inutilisé retiré |
| UP035 | 1 | Iterator importé depuis collections.abc |

Les corrections automatiques sûres ont été prévisualisées puis appliquées.
Le nombre de corrections automatiques annoncé peut dépasser le nombre initial :
la modernisation UTC entraîne aussi des ajustements d'imports.
Aucune règle changée, aucun noqa ajouté, aucune correction unsafe utilisée.
Aucun fichier .env ou migration modifié par cette mission.

## Corrections nécessitant une analyse fonctionnelle

- IncidentService.list_all_incidents : retrait de la première définition, déjà
  écrasée à la création de la classe par la seconde. La méthode réellement utilisée,
  sa signature avec actor_id et son contrôle ADMIN sont conservés.
  Les références ont été vérifiées avant suppression.
- test_incident_repository.py : deux tests homonymes renommés selon la méthode
  vérifiée (get_by_id_and_creator et get_by_id). Toutes les assertions conservées.
- test_user_admin.py : le second test homonyme est renommé. Ses impressions de
  débogage sont remplacées par des assertions sur le statut, les utilisateurs
  attendus et les seuls champs publics autorisés. Le premier test, auparavant
  masqué, conserve toutes ses assertions, dont l'absence de password_hash.
- Deux tests auparavant masqués sont de nouveau collectés : 654 devient 656.
- UTC est le même objet que timezone.utc et reste compatible avec la cible Python
  3.12 de Ruff (exécution sous Python 3.14.6).
- Les 34 autres fichiers ont été comparés par AST à Git HEAD en neutralisant
  uniquement les imports et timezone.utc/UTC : aucun autre changement de code.
  Ces fichiers n'avaient pas de modifications préexistantes.

## Commandes réellement exécutées

Depuis backend :

```powershell
uv run ruff check . --statistics
uv run ruff check . --output-format concise
uv run ruff check . --diff
uv run ruff check . --fix
uv run ruff check .
uv run --env-file .env.test pytest -q --tb=short -rs

$env:TEST_REVOCATION_REDIS_URL = "redis://127.0.0.1:6380/0"
$env:RUN_REAL_REDIS_TESTS = "1"
uv run --env-file .env.test pytest -q --tb=short -rs
```

Depuis frontend :

```powershell
npm test
$env:PLAYWRIGHT_CHANNEL = "msedge"
npm run test:e2e
```

Contrôles Git et dernière vérification depuis la racine du projet :

```powershell
git diff --check
git diff --stat
uv run --project backend ruff check backend
```

## Résultats exacts

- Ruff : All checks passed!
- Backend sans activation Redis : 652 passed, 4 skipped, 3 warnings in 75.32s.
  Les quatre skips correspondent uniquement aux tests Redis opt-in.
- Backend avec Redis réel : 656 passed, 3 warnings in 72.45s. Aucun skip.
- Frontend : 12 fichiers réussis, 161 tests réussis (20.40s).
- Playwright : 1 passed (32.5s), parcours réel permissions, CSRF et audit,
  incluant la vérification du rejeu d'un JWT révoqué.
- git diff --check : aucune erreur.
- git diff --stat exécuté ; son total inclut aussi les modifications préexistantes.
- Pas de nouveau build ou lint frontend : aucun code frontend changé par ce nettoyage.

## Points de vigilance

Trois avertissements préexistants restent visibles, sans échec :
dépréciation httpx dans Starlette TestClient, ancien nom HTTP 422,
clé HMAC courte utilisée par le test négatif de signature JWT.
Ils ne sont ni masqués ni modifiés dans ce nettoyage ciblé.

## Liste exhaustive des fichiers de code modifiés pour cette mission

- `backend/app/api/routes/audit_logs.py`
- `backend/app/api/routes/incidents.py`
- `backend/app/api/routes/users.py`
- `backend/app/main.py`
- `backend/app/repositories/incident_repository.py`
- `backend/app/services/audit_service.py`
- `backend/app/services/incident_service.py`
- `backend/app/services/user_service.py`
- `backend/tests/api/test_admin_lists.py`
- `backend/tests/api/test_audit_logs.py`
- `backend/tests/api/test_audit_logs_dates.py`
- `backend/tests/api/test_auth_rate_limit.py`
- `backend/tests/api/test_incident_assignment.py`
- `backend/tests/api/test_incident_close.py`
- `backend/tests/api/test_incident_comment.py`
- `backend/tests/api/test_incident_filters.py`
- `backend/tests/api/test_incident_history.py`
- `backend/tests/api/test_incident_pagination.py`
- `backend/tests/api/test_incident_priority.py`
- `backend/tests/api/test_incident_resolve.py`
- `backend/tests/api/test_incident_status_change.py`
- `backend/tests/api/test_user_admin.py`
- `backend/tests/integration/test_real_redis.py`
- `backend/tests/repositories/test_audit_repository_dates.py`
- `backend/tests/repositories/test_audit_repository_pagination.py`
- `backend/tests/repositories/test_incident_history_list.py`
- `backend/tests/repositories/test_incident_repository.py`
- `backend/tests/repositories/test_incident_repository_pagination.py`
- `backend/tests/security/test_config.py`
- `backend/tests/security/test_csrf.py`
- `backend/tests/services/test_audit_service_dates.py`
- `backend/tests/services/test_incident_detail_permissions.py`
- `backend/tests/services/test_incident_service_close.py`
- `backend/tests/services/test_incident_service_filters.py`
- `backend/tests/services/test_incident_service_history.py`
- `backend/tests/services/test_incident_service_pagination.py`
- `backend/tests/services/test_incident_service_resolve.py`
