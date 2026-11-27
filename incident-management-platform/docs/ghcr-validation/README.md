# Validation des images GHCR — 27 novembre 2026

## Images exécutées

Tag demandé pour les deux images : latest.
Tag de commit vérifié : sha-ad0889fe07c1cc9de7e06058077f8d5f236f509a.
Les digests des tags de commit sont identiques à ceux de latest.
Ce commit correspond au HEAD local : « ci: publish Docker images to GHCR ».

| Image | Digest OCI testé |
|---|---|
| ghcr.io/emilezehouri/incident-backend:latest | sha256:6f3d05ca3ef0cb209e582d9c04c92905f53219630a50ea680fef6bb024f6fd96 |
| ghcr.io/emilezehouri/incident-frontend:latest | sha256:9426887e8ae94f5c1b8c8b09b2f2cfb0f3b9c766e777594d8304f355ca284d98 |

Plateforme : linux/amd64. Les index contiennent aussi une attestation OCI
unknown/unknown ; ce n'est pas une seconde architecture applicative.
Les services ont utilisé les images épinglées par digest, jamais une reconstruction locale.

## Environnement et démarrage

Projet Compose distinct : incident-ghcr-test.
Frontend : 127.0.0.1:3018, utilisé via http://localhost:3018.
Backend : 127.0.0.1:8019.
PostgreSQL 17 et Redis 7 : réseau privé, aucun port hôte.
Volumes dédiés incident-ghcr-test_postgres_data et incident-ghcr-test_redis_data.
Réseau dédié incident-ghcr-test_default.

Migrations Alembic : succès (code 0) avant démarrage du backend.
PostgreSQL, Redis, backend et frontend : healthy.
Les quatre vérifications HTTP ont répondu 200 :
- http://127.0.0.1:8019/health
- http://127.0.0.1:8019/health/database
- http://localhost:3018
- http://localhost:3018/api/backend/health

Configuration locale HTTP conforme au Compose principal : ENVIRONMENT=development,
avec JWT_REVOCATION_ENABLED, LOGIN_RATE_LIMIT_ENABLED et CSRF_PROTECTION_ENABLED
activés. FRONTEND_ORIGIN=http://localhost:3018.
Les exigences HTTPS du mode production n'ont pas été désactivées dans le code.
Le proxy embarqué pointe vers backend:8000, nom conservé dans le réseau temporaire.

## Tests réellement exécutés

Le parcours frontend/e2e/lifecycle.spec.ts a été copié temporairement et adapté
uniquement pour l'origine, le mot de passe aléatoire et la configuration Playwright
sans webServer. Les trois comptes ont été créés exclusivement dans la base temporaire,
avec les modèles et le hachage provenant de l'image publiée.

Playwright : **1 passed (8.6s)** ; scénario navigateur 6.2 s.
Parcours validé :
- Connexion USER, cookie HttpOnly, création et consultation d'incident.
- Vérification des quatre indicateurs contre les totaux API réels.
- Connexion ADMIN, consultation globale et affectation au technicien.
- Connexion TECHNICIAN, consultation des affectations et indicateurs.
- Passage en cours, résolution et clôture.
- Commentaire, historique et consultation des journaux d'audit.
- USER refusé sur les ressources administrateur (403).
- Requêtes CSRF hostiles refusées, déconnexion avec origine légitime acceptée.
- Session sans cookie refusée après logout.
- Ancien JWT explicitement rejoué deux fois : refusé (401).
- Session administrateur toujours valide après déconnexion du USER.

Test additionnel de persistance :
- Nouvelle connexion, création d'un incident, logout et contrôle du JWT révoqué.
- Arrêt frontend/backend, redémarrage Redis (cache sans persistance).
- Nouvelle exécution alembic upgrade head : succès.
- Redémarrage frontend/backend et healthchecks.
- Ancien JWT toujours refusé (401), grâce à la révocation durable PostgreSQL.
- Reconnexion avec le compte existant et consultation du même incident : succès.

Le rate limiting était activé mais son seuil 429 n'a pas fait l'objet d'un test
spécifique dans cette mission. Il ne faut pas confondre ce constat avec un test de charge.
Le test porte sur linux/amd64 et HTTP local, pas sur ARM64 ou une terminaison TLS de staging.

## Problèmes et recommandations

Aucun défaut fonctionnel bloquant des images n'a été observé.
Les logs ne présentent pas de traceback ou d'erreur critique au démarrage.

Point de traçabilité : le backend hérite des labels de l'image uv :
titre uv, version de uv, date et révision ne décrivent pas l'application.
Le frontend ne renseigne que le label source.
La correspondance avec le dépôt est néanmoins établie par l'égalité des digests
latest/sha-ad0889fe07c1cc9de7e06058077f8d5f236f509a.

Amélioration minimale recommandée pour une prochaine publication :
renseigner explicitement les labels OCI title, description, revision, version,
created et url pour chaque application dans la CI.
Aucun Dockerfile ni workflow n'a été modifié ou reconstruit pour masquer ce point.

## Sécurité et nettoyage

Secrets robustes générés en mémoire pour cette exécution, aucun token GHCR affiché.
Aucun secret existant, .env.docker ou donnée utilisateur principale modifié.
Les paramètres Compose conservés ne contiennent que des références aux variables,
pas les secrets générés. Les traces navigateur contenant potentiellement des cookies
n'ont pas été enregistrées.

Après collecte des preuves :
- Suppression uniquement du projet incident-ghcr-test, de ses deux volumes et réseau.
- Aucun conteneur, volume ou réseau temporaire restant.
- Répertoires de test Playwright et configuration temporaire supprimés.
- Images téléchargées conservées dans le cache Docker ; aucun nettoyage global.
- Identifiants des conteneurs principaux inchangés.
- Frontend/backend/PostgreSQL/Redis principaux toujours healthy.
- http://localhost:3000 répond toujours 200.

## Preuves et reproduction

- results.json : images exactes, healthchecks, persistance, inventaires avant/après.
- playwright.log : résultat navigateur.
- startup.log et containers.log : démarrage, migrations et requêtes.
- migration-rerun.log : nouvelle exécution Alembic.
- compose.json : configuration isolée épinglée par digest, sans secrets.
- ../../scripts/validate_ghcr.py : exécuteur reproductible.

Depuis la racine de incident-management-platform, Docker Desktop en marche :
1. docker pull ghcr.io/emilezehouri/incident-backend:latest
2. docker pull ghcr.io/emilezehouri/incident-frontend:latest
3. uv run --project backend python scripts/validate_ghcr.py

Le script exige les ports 3018/8019 libres, refuse de réutiliser des ressources
du projet temporaire et utilise Microsoft Edge via Playwright installé localement.
Il écrit de nouvelles preuves à chaque exécution. Aucun build local n'est exécuté.

**VALIDÉ : les images GHCR permettent d'exécuter correctement l'application.**
