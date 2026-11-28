# Validation du déploiement Render — 28 novembre 2026

Les exports bruts et journaux cités ci-dessous sont conservés localement hors commit. Voir `render-release-runbook.md` pour la préparation ultérieure et `render-dependency-summary.json` pour la preuve synthétique versionnée. Les résultats suivants décrivent l’audit initial, pas le déploiement de la nouvelle image.

## Conclusion

Validation partielle du service https://incident-backend-sha.onrender.com. Le service public et sa connexion PostgreSQL répondent. Les corrections ci-dessous sont locales, non publiées et non déployées. Aucun secret, paramètre Render ou donnée métier de production n’a été modifié. La version du schéma distant, Redis distant et le parcours authentifié distant restent à vérifier avec les accès appropriés.

## Matrice de validation

| Composant | Statut | Preuve | Action restante |
|---|---|---|---|
| PostgreSQL | Connexion distante validée ; schéma distant non vérifié | GET /health/database : 200 ; SELECT 1 exécuté par le code de cette route | Exécuter le diagnostic dans l’environnement Render |
| Alembic | Chaîne complète validée localement | Test de migration depuis un schéma vide puis second upgrade idempotent ; comparaison modèles/migrations | Confirmer la révision distante c41f9a2d7e10 et les six tables |
| Redis/Valkey | Code et tests locaux contrôlés ; connexion distante non vérifiée | Tests de révocation/limitation et indisponibilité ; nouveau health check testé | PING depuis Render, puis tests contrôlés TTL/révocation/limitation |
| FastAPI | Accès public et refus d’accès validés | /health, /docs, /openapi.json : 200 ; /auth/me, /incidents, /incidents/all, /users, /audit-logs : 401 sans session | Parcours authentifié sur compte de test autorisé |
| CI/CD | Dernier pipeline public réussi ; déploiement Render non automatisé par ce workflow | Run 46075266238, commit 79444576c6a93c32aeec9b89c638999bf98a0c93 | Publier les corrections après accord ; vérifier le digest réellement déployé |
| Sécurité | Protections inspectées et testées localement ; CSRF distant validé | POST login/logout/incidents depuis origine hostile : 403 ; audit Python corrigé localement | Vérifier le mode production et appliquer les corrections après accord |

Les réponses publiques sont conservées dans render-public-checks.json, render-security-checks.json et render-openapi.json. Le dernier succès GitHub précède les changements locaux de cette intervention ; il ne les valide pas.

## Corrections locales

- `backend/app/core/config.py` : origines CORS issues de FRONTEND_ORIGIN ; origines localhost conservées uniquement en dehors de production sans origine configurée.
- `backend/app/main.py` : utilisation de cette configuration CORS ; erreur de connexion PostgreSQL renvoyée en 503 sans détail sensible ; ajout GET /health/redis utilisant PING avec réponse 503 en cas de panne.
- `backend/pyproject.toml` et `backend/uv.lock` : mises à jour ciblées de PyJWT, certifi, dnspython et urllib3. Minimum PyJWT fixé à 2.15.0.
- `backend/scripts/verify_deployment.py` : diagnostic en lecture seule, transaction PostgreSQL READ ONLY et délais bornés ; contrôle de la révision, des tables, des différences de métadonnées, des contraintes nommées et des clés étrangères ; PING Redis ; aucune URL ni mot de passe dans les résultats.
- `backend/tests/test_deployment_health.py` : sept cas CORS et disponibilité des dépendances, incluant la non-divulgation des erreurs.
- `backend/tests/security/test_full_migration_chain.py` : un test de toute la chaîne Alembic, dans un schéma isolé d’une base *_test ; nettoyage limité à ce schéma de test.
- `../.github/workflows/ci.yml` : audit des dépendances Python de production, bloquant en cas de vulnérabilité connue.
- `docs/` : ce rapport, preuves JSON, export des dépendances auditées et comptes rendus des tests.

Aucune migration existante, règle métier, permission, configuration secrète ou assertion existante n’a été modifiée.

## Audit technique

### PostgreSQL et migrations

Le pilote attendu est Psycopg 3 via postgresql+psycopg et psycopg[binary]. Le moteur existant active pool_pre_ping et les sessions sont fermées par la dépendance FastAPI. Le pool par défaut autorise cinq connexions persistantes et dix supplémentaires par processus ; vérifier ce budget avec les limites du plan et le nombre de processus. Le moteur applicatif ne définit pas de délai de connexion explicite ; le nouveau diagnostic en définit un. Garder SQL_ECHO désactivé en production pour éviter de journaliser des valeurs métier.

Six tables attendues : users, incidents, incident_comments, incident_history, audit_logs, revoked_tokens. Révisions : b8ef9b6eac65, b7920b10f87c, c41f9a2d7e10. Aucune nouvelle migration nécessaire selon le test local. Le Dockerfile ne lance pas Alembic et le service migrate de Compose ne s’exécute pas automatiquement sur Render : un démarrage réussi ne prouve pas la présence du schéma.

Le contrôle des CHECK du diagnostic compare les noms, pas leurs expressions SQL exactes ; la chaîne de migrations a également été relue. Ce contrôle ne remplace pas une revue de modifications manuelles du schéma distant.

### Redis et authentification

Le client accepte redis:// et rediss:// via Redis.from_url, avec délais de connexion et d’opération d’une seconde. Valkey doit exposer le protocole compatible Redis ; ne pas inventer un schéma valkey://.

Les compteurs de connexion sont atomiques via Lua, avec fenêtres et expiration. La révocation conserve une preuve PostgreSQL et une clé Redis expirant à l’expiration JWT ; un cache manquant entraîne une consultation SQL. Une indisponibilité des dépendances de sécurité provoque un refus 503, sans désactivation silencieuse. En production, les contrôles imposent Redis, une clé JWT suffisante et une origine HTTPS exacte.

Cookie access_token HttpOnly, Secure en production et SameSite=Lax. Le proxy Next.js permet le flux même origine. Une intégration directe entre sites distincts exige de revalider le comportement navigateur. Les limites IP dépendent de request.client.host : vérifier le traitement des proxys Render/Next et ne pas faire confiance arbitrairement aux en-têtes envoyés par le client.

### CORS et dépendances

Anomalie réelle : l’application utilisait une liste localhost codée en dur au lieu de FRONTEND_ORIGIN. La prérequête distante localhost a reçu 200 ; une origine hostile a reçu 400. La correction est testée localement, mais n’est pas encore présente sur Render.

L’audit initial signale 22 occurrences sur quatre paquets : certifi 2, dnspython 2, PyJWT 15, urllib3 3. Ce sont des occurrences du rapport, pas nécessairement 22 vulnérabilités distinctes. Après mise à jour : zéro vulnérabilité connue signalée. Versions retenues : certifi 2026.11.20, dnspython 2.9.2, PyJWT 2.15.1, urllib3 2.8.0. Preuves : backend-dependency-audit.json et backend-dependency-audit-after.json.

L’analyse concerne les dépendances Python résolues pour l’environnement local ; elle ne couvre pas les paquets système de l’image ni ne prouve la version actuellement déployée. Le nouvel audit CI effectuera aussi le contrôle sous Linux.

### CI/CD et hébergement

Le workflow enchaîne tests PostgreSQL/Redis, contrôles frontend, parcours Playwright, construction Docker et publication GHCR sur main. Un échec de test bloque la suite. Dernier run consulté : https://github.com/EmileZEHOURI/Platforme-DevSecOps-Gestion-d-Incident-IT-elephant-project-/actions/runs/46075266238.

Le workflow ne déclenche pas Render. Un service Render fondé sur une image ne se redéploie pas automatiquement lorsque le tag latest change : https://render.com/docs/deploying-an-image. Il faut une action de déploiement explicite et vérifier le digest. Une amélioration consiste à promouvoir exactement l’image testée plutôt que reconstruire pour publier.

Selon la documentation Render, les offres gratuites peuvent mettre le web en veille après 15 minutes, utilisent un disque éphémère et la base PostgreSQL gratuite expire après 30 jours. Le shell et les jobs ponctuels ne sont pas disponibles sur le web gratuit. Vérifier le plan réel avant présentation ; aucune offre effective n’a été présumée : https://render.com/docs/free.

## Procédure distante restante

1. Dans Render, identifier le service, son image/digest et les services PostgreSQL/Redis associés. Contrôler sans copier les secrets : ENVIRONMENT=production, FRONTEND_ORIGIN exacte, SQL_ECHO=false, URL PostgreSQL avec Psycopg 3, URL Redis compatible et TLS selon le service.
2. Une fois les corrections publiées et déployées avec accord, ouvrir un shell du service si le plan le permet, se placer dans le répertoire backend contenant alembic.ini et exécuter :

```sh
.venv/bin/python -m scripts.verify_deployment
.venv/bin/alembic heads
.venv/bin/alembic current
```

Le diagnostic doit indiquer schema.ok=true, redis.ping=true, le pilote attendu et les protections activées. L’empreinte de cible permet de comparer deux exécutions sans exposer l’adresse ; elle ne suffit pas à identifier seule la bonne base. Vérifier la cible dans Render au préalable. Les commandes Alembic présupposent une configuration valide ; ne pas partager de trace brute contenant des paramètres de connexion.

Si le plan ne propose pas de shell, exécuter le diagnostic depuis une machine autorisée avec les connexions externes Render injectées dans un environnement temporaire sécurisé. Ne pas utiliser les URL internes Render depuis le poste et ne pas écrire les secrets dans Git ou l’historique du terminal. Avec un checkout et uv, la commande équivalente depuis backend est `uv run python -m scripts.verify_deployment`.

3. Si une révision manque : sauvegarder, confirmer la cible, examiner les révisions manquantes et leur impact. Alors seulement appliquer `alembic upgrade head` avec l’environnement ciblé, puis relancer le diagnostic. Aucune migration distante n’a été exécutée pendant cet audit.
4. Refaire GET /health, /health/database et /health/redis après déploiement. Utiliser /health comme sonde de vie et les deux autres pour surveiller indépendamment les dépendances.
5. Avec un compte de test explicitement autorisé, réaliser login → me → création/lecture/gestion d’incident → logout → refus du JWT révoqué. Utiliser l’origine frontend configurée et conserver les cookies, sans afficher le token. Vérifier les écritures et journaux d’audit. Les commentaires et autres données de test étant persistants, ne pas exécuter ce scénario en production sans autorisation.
6. Sur staging isolé, vérifier expiration Redis, seuils de limitation et panne Redis → 503 ; ne pas provoquer volontairement une panne du service de production. Ne pas utiliser FLUSHDB sur les services réels.

## Priorités

- **Bloquant pour déclarer la validation complète** : schéma/révision et Redis distants non confirmés ; parcours authentifié distant non exécuté faute de compte de test autorisé ; corrections locales non déployées.
- **Important** : corriger CORS et publier les dépendances mises à jour ; confirmer le mode production, le digest, les limites de connexion, la confiance des proxys et la procédure de migration. Valider la persistance et la durée de vie du plan choisi.
- **Amélioration** : scanner aussi l’image et produire une SBOM ; promouvoir un digest unique ; vérifier la restauration des sauvegardes Render/hors site ; ajouter une purge maîtrisée des révocations SQL expirées et une surveillance des 5xx/dépendances.

Pour une démonstration en entretien : conserver un environnement de test reproductible, les preuves CI, un diagramme du flux cookie/CSRF/révocation et un exercice de restauration documenté. Ne pas présenter les contrôles locaux comme des preuves de fonctionnement distant.

## Commandes et résultats réellement obtenus

Depuis `backend` :

```powershell
uv run ruff check .
$env:TEST_REVOCATION_REDIS_URL = 'redis://127.0.0.1:6380/0'
$env:RUN_REAL_REDIS_TESTS = '1'
uv run --env-file .env.test pytest -q --tb=short -rs
```

- Ruff : `All checks passed!`.
- Backend : **673 passed, 3 warnings in 119.90s**, zéro échec et aucun test ignoré annoncé. Sortie complète : render-backend-tests.txt.
- Les avertissements concernent TestClient/httpx, le nom déprécié du code HTTP 422 et une clé volontairement courte dans un test de signature invalide. Ils ne prouvent pas une clé courte en production.
- Une première exécution, avant disponibilité de Docker/Redis local, avait donné 50 échecs et 615 réussites. Après démarrage du Redis de test, les cas affectés puis toute la suite sont passés. Aucun test n’a été désactivé. Une invocation depuis un mauvais répertoire avait aussi échoué au chargement de la configuration ; les résultats ci-dessus viennent du bon répertoire backend.
- Vérification ciblée des huit nouveaux cas avant la suite complète : **8 passed, 1 warning in 0.93s**.

Depuis `frontend` :

```powershell
npm test
$env:PLAYWRIGHT_CHANNEL = 'msedge'
npm run test:e2e
```

- Frontend : **14 fichiers, 183 tests réussis**, 18.46s ; render-frontend-tests.txt.
- Playwright : **1 passed (40.5s)**, parcours réel API/navigateur avec permissions, CSRF et audit ; render-e2e-tests.txt. Avertissement bénin NO_COLOR/FORCE_COLOR.
- Les tests PostgreSQL et le parcours navigateur emploient des schémas isolés dans une base *_test et nettoient leurs propres schémas ; ils ne visent pas Render.

Audit des dépendances depuis `backend` :

```powershell
uv export --frozen --no-dev --no-emit-project --format requirements-txt --output-file ../docs/backend-audit-requirements.txt
uvx pip-audit -r ../docs/backend-audit-requirements.txt --disable-pip --no-deps --format json --output ../docs/backend-dependency-audit-after.json
```

pip-audit 2.10.1 : **No known vulnerabilities found** après les mises à jour. L’audit initial avec le même outil est archivé séparément.

`git diff --check` : aucune erreur. `git diff --stat` exécuté ; il ne compte pas les nouveaux fichiers non suivis. Le dépôt était propre au début de cette intervention. Aucun commit ni push effectué. La nouvelle étape CI n’a pas été exécutée sur GitHub, et l’image Docker corrigée n’a pas été reconstruite/publiée pendant cette intervention. Les contrôles frontend lint/typecheck/build n’ont pas été relancés séparément ; aucun fichier frontend n’a été modifié.
