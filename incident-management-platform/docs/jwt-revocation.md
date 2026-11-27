# Révocation des JWT — fonctionnement et exploitation

## Architecture

Chaque nouveau JWT contient un `jti` aléatoire de 128 bits (`secrets.token_hex(16)`), indépendant de l'utilisateur. Les claims existants `sub`, `type`, `iat`, `exp`, la signature HS256, l'expiration et les dates numériques restent vérifiés. Un `jti` malformé est rejeté. Quand la révocation est requise, les anciens tokens sans `jti` sont rejetés avec 401 : une nouvelle connexion est nécessaire.

`get_current_user` décode une fois le JWT, contrôle Redis puis PostgreSQL si la clé Redis manque, et conserve les claims vérifiés dans l'état de la requête pour `/auth/logout`. Il conserve ensuite les contrôles d'existence et d'activation du compte. Les autorisations de rôle ne changent pas.

Redis contient uniquement `auth:revoked:<digest HMAC-SHA256>` avec la valeur `1`. Le JWT, l'identité utilisateur et le `jti` brut ne sont pas stockés. L'expiration absolue Redis `EXAT` est celle du JWT. Une répétition ne prolonge pas sa durée de vie. Un token déjà expiré n'ajoute pas de clé.

La table PostgreSQL `revoked_tokens` conserve le même digest et `expires_at`. Cette trace est nécessaire parce que Redis de développement n'a pas de persistance. Une éviction, un redémarrage à vide ou la disparition d'une clé Redis ne rend pas un JWT révoqué utilisable : la lecture SQL le retrouve et recharge le cache. Aucune réponse négative n'est mise en cache, pour éviter une fenêtre de rejeu après la déconnexion.

Le client Redis avec délais de connexion et de lecture d'une seconde est partagé avec le rate limiting. Les clés et la logique métier restent distinctes.

## Ordre de déconnexion et erreurs

1. Vérification CSRF existante, puis authentification et contrôle de révocation.
2. Dans une transaction SQL : insertion de la révocation durable et audit `LOGOUT/SUCCESS`.
3. Commit SQL.
4. Écriture Redis avec expiration absolue.
5. Suppression du cookie et réponse 200.

| Situation | Comportement |
| --- | --- |
| JWT invalide, expiré, révoqué ou ancien sans `jti` lorsque requis | 401 |
| Redis indisponible lors du contrôle | 503, aucun accès autorisé par défaut |
| Erreur SQL dans le contrôle de révocation | 503 |
| Échec de la transaction SQL de logout | Rollback de l'audit et de la révocation, 503, aucune écriture Redis |
| Échec Redis après commit SQL | 503, pas de confirmation ni de suppression du cookie ; le JWT reste durablement révoqué |
| Cache Redis perdu après une déconnexion réussie | Refus via PostgreSQL ; réhydratation Redis |

Dans le cas d'un échec Redis après commit, l'audit de succès désigne la révocation durable effectivement enregistrée, pas la réussite du transport HTTP. Après rétablissement, le token est refusé (401) ; une répétition du logout ne produit pas de nouvel audit. Il n'existe pas de transaction atomique distribuée SQL/Redis : cet ordre privilégie la sécurité sans annoncer un succès Redis fictif.

## Configuration et migration

Variables d'exemple, sans secrets réels :

```dotenv
JWT_REVOCATION_ENABLED=true
REDIS_URL=redis://127.0.0.1:6380/0
```

En développement/test, le flag est explicitement activable et vaut `false` par défaut pour rester compatible avec les environnements locaux existants. En production, la révocation est toujours requise, même si le flag vaut `false`. `REDIS_URL` est obligatoire dès qu'elle est requise. Les contraintes existantes de secret JWT, d'algorithme, de durée, d'origine HTTPS et de rate limiting restent applicables.

**Avant d'activer la révocation sur une base existante**, appliquer la migration Alembic avec la configuration de la base visée :

```powershell
uv run alembic upgrade head
```

Migration ajoutée : `c41f9a2d7e10_add_revoked_tokens.py`, après `b7920b10f87c`. Cette mission a vérifié la nouvelle migration sur une base de test isolée ; elle n'a pas migré de base applicative ni déployé en production. Ne pas activer le mécanisme sans cette table : les requêtes seront refusées avec 503.

En production : PostgreSQL durable avec commits synchrones, stockage persistant, sauvegardes et procédures de restauration ; Redis privé, authentifié/TLS selon le réseau. La sécurité de révocation ne repose pas sur la persistance Redis. Configurer néanmoins Redis pour limiter les évictions et assurer sa disponibilité, car une panne bloque volontairement les accès protégés.

Un retour PostgreSQL à une sauvegarde antérieure peut perdre les révocations récentes : à la restauration, changer la clé JWT de tous les processus avant réouverture afin d'invalider les anciens tokens. Synchroniser les horloges des serveurs.

Les lignes SQL expirées n'autorisent pas de rejeu (la signature expirée est rejetée). Pour contenir la taille de la table, planifier cette purge sur la base applicative concernée :

```sql
DELETE FROM revoked_tokens WHERE expires_at <= CURRENT_TIMESTAMP;
```

Ne pas purger les lignes non expirées et ne pas revenir en arrière sur cette migration tant que des tokens signés peuvent encore être utilisés. Le contrôle SQL sur les absences Redis ajoute une lecture indexée par requête authentifiée. Une requête déjà authentifiée avant le commit de logout peut terminer : la révocation bloque les vérifications ultérieures, pas les opérations déjà en cours.

## Tests et isolation

Depuis `backend` :

```powershell
$env:TEST_REVOCATION_REDIS_URL = 'redis://127.0.0.1:6380/0'
$env:RUN_REAL_REDIS_TESTS = '1'
uv run --env-file .env.test pytest -q --tb=short -rs
uv run ruff check .
```

Les nouveaux tests utilisent FakeRedis et la fixture PostgreSQL existante (`*_test`, schéma unique, transactions isolées). Le test Redis réel de révocation est opt-in via `TEST_REVOCATION_REDIS_URL` et supprime uniquement sa propre clé à digest aléatoire. Il vérifie également l'expiration réelle. Le flag existant `RUN_REAL_REDIS_TESTS=1` active les trois tests Redis réels du rate limiting, dans leur base de test dédiée.

Les nouveaux tests couvrent également : unicité/validation du `jti`, anciens JWT, signatures invalides, TTL, écriture refusée, panne de lecture/écriture Redis, panne SQL, atomicité audit/révocation, deux sessions du même compte, rejeu répété, comptes désactivés, rôles, CSRF, perte d'une clé et migration upgrade/downgrade.

Depuis `frontend` :

```powershell
npm run test
npm run lint
npx tsc --noEmit
npm run build
$env:PLAYWRIGHT_CHANNEL = 'msedge' # ou Chromium installé via Playwright
npm run test:e2e
```

Le runner E2E active maintenant la révocation et la protection CSRF avec le vrai Redis (`E2E_REDIS_URL`, défaut local `redis://127.0.0.1:6380/0`). Il utilise un schéma PostgreSQL et une clé JWT éphémères. Son nettoyage retire uniquement les clés de révocation de ce schéma ; si Redis est indisponible au nettoyage, les clés expirent naturellement et le nettoyage SQL se poursuit. Le scénario conserve une copie du JWT, se déconnecte, rejoue deux fois la copie (401) et vérifie qu'une autre session demeure valide.

## Fichiers concernés

- `app/security/token.py` : création et décodage des claims.
- `app/security/redis_client.py` et `login_rate_limit.py` : client partagé sans changement des limites.
- `app/security/token_revocation.py` : stockage et consultation de révocation.
- `app/models/revoked_token.py`, registre des modèles, migration Alembic : durabilité SQL.
- `app/core/config.py` : activation explicite et obligation en production.
- `app/api/dependencies.py`, `app/api/routes/auth.py` : refus des tokens révoqués, transaction logout.
- Trois nouveaux fichiers de tests backend et deux fichiers E2E adaptés.

Ruff global présentait déjà 90 erreurs avant ce travail. Les vérifications ciblées sur les fichiers backend créés/modifiés passent ; les erreurs restantes hors de ce périmètre sont détaillées dans le rapport de validation. Aucun secret réel ni fichier `.env` existant n'a été modifié.

## Résultats vérifiés le 27 novembre 2026

- Suite backend complète avec les deux options Redis réel activées : **654 réussis, 0 échoué, 0 ignoré** ; 3 avertissements préexistants (Starlette/HTTPX, constante HTTP 422, clé courte dans un test négatif).
- Nouveaux tests de révocation et migration : **35 réussis** (inclus dans les 654).
- Frontend Vitest : **161 réussis, 0 échoué, 0 ignoré**, 12 fichiers.
- Frontend ESLint, TypeScript et compilation Next.js : réussis.
- Playwright avec FastAPI, PostgreSQL, Redis et Edge Chromium réels : **1 parcours réussi, 0 échec**, dont rejeu explicite du JWT déconnecté, CSRF et autres fonctionnalités.
- Migration : upgrade/downgrade vérifiés dans un schéma PostgreSQL jetable.
- `uv run ruff check .` : **86 erreurs globales restantes**, contre 90 avant modification ; ces erreurs préexistantes hors périmètre concernent notamment imports, anciens alias datetime, définitions dupliquées. Le contrôle Ruff ciblé sur tous les fichiers backend créés/modifiés, hors migration exclue par la configuration existante, passe sans erreur.

La mission ne corrige pas les erreurs Ruff sans rapport avec la révocation. L’installation sur une base applicative existante nécessite encore la migration et l’activation documentées ; aucun déploiement de production n’a été effectué.
