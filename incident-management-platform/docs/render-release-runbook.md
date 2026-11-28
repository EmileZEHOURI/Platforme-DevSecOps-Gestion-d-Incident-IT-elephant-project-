# Mise en production contrôlée — Render / GHCR

## Périmètre et état

Préparation locale du 28 novembre 2026. Ce document complète `render-deployment-validation.md`, qui décrit l’audit initial. Aucun push, publication GHCR, déploiement Render, changement de configuration distante ou migration de production n’a été exécuté. Les contrôles distants de l’audit initial ne constituent pas une recette de la nouvelle image.

Le commit inclut les corrections CORS, les sondes PostgreSQL/Redis, le diagnostic en lecture seule, ses tests, les mises à jour de dépendances et l’audit CI. La publication ajoute désormais le label OCI `org.opencontainers.image.revision` au backend et au frontend. Les fichiers volumineux d’audit, OpenAPI et journaux restent disponibles localement hors commit ; les preuves synthétiques sont versionnées. Aucun fichier .env n’est inclus.

## 1. Publication après autorisation explicite

Depuis la racine Git `elephant-project`, relever le commit préparé et vérifier la destination avant toute publication :

```powershell
git status --short
git log -1 --format='%H %s'
git remote -v
```

La branche locale est main. La commande suivante nécessite un accord de push qui précise qu’elle déclenchera aussi la publication automatique GHCR :

```powershell
git push origin main
```

Ne pas forcer si la branche distante a avancé : examiner et intégrer les changements, puis revalider. Une PR est possible ; elle lance les tests mais la publication n’a lieu qu’après intégration dans main. Le workflow actuel publie **les deux images**, même si les corrections applicatives concernent le backend. Il ne déploie pas Render.

Attendre le succès des jobs backend, frontend, E2E, docker-build et publish-images pour le SHA exact, pas celui d’un ancien run. La publication utilise GITHUB_TOKEN avec packages:write, aucun jeton personnel à ajouter au dépôt.

Images produites :

- `ghcr.io/emilezehouri/incident-backend:sha-<SHA_COMPLET>` et `:latest`
- `ghcr.io/emilezehouri/incident-frontend:sha-<SHA_COMPLET>` et `:latest`

Le workflow reconstruit dans le job de publication : le digest local n’est donc pas le digest GHCR attendu. Relever le digest de la publication réussie et le confirmer :

```powershell
$releaseSha = git rev-parse HEAD
$releaseImage = "ghcr.io/emilezehouri/incident-backend:sha-$releaseSha"
docker buildx imagetools inspect $releaseImage
# Après lecture du digest réel, remplacer le marqueur ci-dessous :
$releasePinned = 'ghcr.io/emilezehouri/incident-backend@sha256:<DIGEST_GHCR>'
docker pull $releasePinned
docker image inspect $releasePinned --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}'
```

Le label doit être égal au SHA complet. Un tag sha reste techniquement remplaçable ; le digest est l’identifiant immuable à déployer. Ne pas confondre digest d’index, digest de manifeste linux/amd64 et identifiant local de configuration : noter leur relation dans la sortie imagetools.

## 2. Déploiement Render après accord séparé

Avant modification, noter dans le dossier de livraison l’identifiant du service backend, la région, l’ancien digest et le dernier déploiement sain. Vérifier que FRONTEND_ORIGIN correspond réellement au frontend HTTPS, ENVIRONMENT=production, SQL_ECHO=false et que les services de données sont ceux attendus. Ne copier aucune valeur secrète dans ce document.

Après autorisation, sélectionner l’image backend par son digest GHCR dans Render puis déclencher le déploiement manuel. Conserver les variables existantes ; ne pas changer la commande de démarrage en commande de migration. Le backend écoute sur 0.0.0.0:8000. Ne pas redéployer le frontend sans décision distincte ; si nécessaire, contrôler son API_URL réel, car la valeur de construction `http://backend:8000` vise Compose, pas automatiquement Render.

Preuves obligatoires de nouvelle image :

1. Référence configurée `...@sha256:<DIGEST_GHCR>` identique à celle approuvée.
2. Nouveau déploiement réussi dans Events/logs, avec image/digest correspondant lorsque Render l’affiche. Si un manifeste de plateforme est affiché, le rapprocher de l’index publié.
3. GET /health = 200 ; GET /health/database = 200 ; nouvelle route GET /health/redis = 200 et JSON attendu. La présence de cette route est un indice de changement, pas une preuve suffisante d’identité à elle seule.
4. Prérequête CORS autorisée pour l’origine configurée ; refus d’une origine hostile et de localhost en production.
5. Archiver SHA, digest, identifiant/date du déploiement et résultats, sans cookies ni secrets. Si le digest actif ne peut pas être confirmé dans les informations accessibles, laisser la vérification d’identité ouverte.

Retour arrière : sur échec des sondes ou de la recette, arrêter la promotion ; demander l’autorisation pour redéployer l’ancien digest sain. Aucun downgrade Alembic automatique. Cette livraison n’ajoute aucune migration ; vérifier toutefois la compatibilité du schéma avant rollback. Revenir à l’image précédente réintroduirait les dépendances vulnérables corrigées : ce serait une mesure temporaire documentée.

Render ne redéploie pas automatiquement une image lorsqu’un tag change. Référence officielle : https://render.com/docs/deploying-an-image.

## 3. Schéma PostgreSQL, Alembic et Redis sans shell gratuit

Le plan web gratuit n’offre pas de shell/SSH ni de job ponctuel. Il peut se mettre en veille ; laisser le temps au démarrage avant de conclure à une panne. La base PostgreSQL gratuite expire après 30 jours. Le Redis gratuit n’est pas persistant : la révocation doit continuer à s’appuyer sur PostgreSQL après une perte du cache, tandis que les compteurs de limitation peuvent être perdus. Sources : https://render.com/docs/free et https://render.com/docs/key-value.

Option A — machine autorisée, accès externe déjà disponible : injecter temporairement, via saisie masquée ou gestionnaire de secrets, les URL externes PostgreSQL et Redis et les paramètres requis. Ne pas réutiliser une URL interne depuis le poste. Redis externe exige TLS et une IP autorisée ; l’ouverture/modification d’une liste réseau nécessite un accord distinct, limité à l’IP nécessaire. Ne pas ouvrir 0.0.0.0/0 pour contourner une limitation.

Exécuter le diagnostic avec l’image publiée épinglée. Les `-e NOM` transmettent les variables déjà chargées, sans mettre leur valeur dans la commande :

```powershell
docker run --rm -e DATABASE_URL -e REDIS_URL -e JWT_SECRET_KEY -e ENVIRONMENT -e FRONTEND_ORIGIN -e SQL_ECHO $releasePinned python -m scripts.verify_deployment
```

Supprimer ensuite les variables temporaires du processus utilisé, sans modifier les variables système ou fichiers existants. Ce diagnostic vérifie la base cible et Redis via les accès externes ; il ne prouve pas la configuration effective du processus web Render. Les sondes HTTP de ce dernier complètent donc le contrôle.

Option B — accès externe indisponible : après approbation, utiliser temporairement une capacité Render payante avec shell ou un service de diagnostic autorisé dans la même région/réseau. L’URL interne nécessite la bonne région. Ne pas créer de ressource payante ni modifier le service sans accord. À défaut, les contrôles restent bloqués ; ne pas exposer une route d’administration publique pour les contourner.

Dans un shell disponible, depuis /app :

```sh
python -m scripts.verify_deployment
alembic heads
alembic current
```

Résultat attendu du diagnostic : pilote postgresql+psycopg, PostgreSQL connecté, schema.ok=true, applied_heads=expected_heads=[c41f9a2d7e10], six tables présentes, clés étrangères cohérentes et Redis ping=true. Vérifier aussi les protections activées et SQL_ECHO=false. Le contrôle CHECK porte sur les noms, pas sur l’équivalence des expressions. L’empreinte de cible masque son adresse mais ne remplace pas l’identification du service dans Render.

Si une migration manque : arrêt, sauvegarde vérifiée, revue de la cible et du SQL à appliquer, puis demande d’autorisation spécifique. Seulement après accord : `alembic upgrade head`, suivi du diagnostic. Pas de DROP, reset, recreate, downgrade, flush ni migration automatique au démarrage. Aucune migration destructive n’est prévue.

## 4. Recette sans toucher aux données métier réelles

Exécuter le scénario complet sur un environnement isolé utilisant **le même digest**, des PostgreSQL/Redis dédiés et des comptes synthétiques USER, TECHNICIAN, ADMIN. Préfixer les incidents `RELEASE-<SHA_COURT>-<UUID>`. Ne pas importer de données réelles. Toute création d’environnement distant, de compte ou de données nécessite l’accord correspondant. Le parcours local existant `npm run test:e2e` crée un schéma *_test isolé et nettoie uniquement ses propres données ; il ne vise pas Render.

| Étape | Opération contrôlée | Résultat attendu |
|---|---|---|
| Accès anonyme | GET /auth/me et /incidents sans cookie | 401 |
| Authentification | POST /auth/login, origine frontend autorisée, identifiants synthétiques | 200 ; access_token HttpOnly, Secure en HTTPS/production, SameSite=Lax ; GET /auth/me = 200 |
| Validation | POST /incidents avec titre trop court | 422 ; aucun incident créé |
| Création | POST /incidents avec title, description, category, priority uniquement | 201 ; id/reference, statut OPEN ; retrouver cet id dans liste et détail |
| Autorisations | Autre utilisateur synthétique consulte cet id | 404 ; aucune exposition du contenu |
| Cycle métier | Assignation administrateur, traitement technicien, résolution, clôture via les routes/UI existantes | États et droits conformes ; commentaire avant clôture accepté, après clôture 409 ; historique/audit cohérents |
| CSRF | POST avec origine hostile, session de test valide | 403 ; session conservée |
| Révocation | Conserver le JWT uniquement en mémoire, logout avec origine autorisée, rejouer le JWT capturé sur /auth/me | Logout réussi ; cookie effacé ; ancien JWT refusé 401 ; nouvelle connexion fonctionnelle |
| Limitation compte | Après remise à zéro naturelle des fenêtres, 11 tentatives erronées sur un compte synthétique depuis une IP dédiée | 10 refus d’authentification puis 429 et Retry-After positif |
| Limitation IP | Nouvelle fenêtre propre ; 21 tentatives réparties sur plusieurs comptes synthétiques, chacun sous 10 | 21e tentative 429 pour plafond 20/300s ; vérifier l’IP vue derrière les proxys |
| TTL | Observer uniquement les clés HMAC des comptes/IP/JTI de test | TTL compte <=900s, IP <=300s ; clé de révocation expirant avec le JWT ; accès réautorisé après fenêtre, sans réduire les protections |
| Panne Redis | Sur environnement isolé seulement, interrompre Redis pendant une tentative de connexion/requête protégée | 503, jamais accès accordé par défaut ; rétablissement après restauration |
| Perte du cache | Sur instance de test dédiée seulement, retirer la seule clé du JWT de test révoqué | Ancien JWT toujours refusé grâce à PostgreSQL ; aucun FLUSHDB |

Les connexions valides consomment aussi des compteurs : réaliser les tests de seuil dans des fenêtres fraîches, après la recette métier. Ne pas lancer ces séries depuis une IP partagée par les utilisateurs réels. Les opérations login/logout génèrent déjà des journaux et de la révocation persistante : elles nécessitent aussi une autorisation si exécutées en production, même sans incident créé.

Ne jamais archiver les valeurs de cookies/JWT ; conserver seulement codes HTTP, identifiants synthétiques, durées et booléens. Nettoyer uniquement l’environnement de recette dédié, pas la production. La réussite du staging ne remplace pas la vérification des dépendances et du parcours minimal du service de production. Pour ce dernier, demander un compte de démonstration autorisé et le périmètre exact des écritures permises ; sinon, garder la recette authentifiée bloquée.

## 5. Checklist de livraison

- [x] Diff et nouveaux fichiers examinés ; corrections ciblées et migrations existantes inchangées.
- [x] Recherche des valeurs sensibles locales et formats de clés ; seul exemple JWT d’une description publique de vulnérabilité dans le rapport brut hors commit.
- [x] Aucun fichier .env dans le commit ou les images ; backend non-root vérifié.
- [x] Ruff, tests backend avec Redis réel, tests frontend, ESLint, TypeScript, compilation Next.js et Playwright relancés.
- [x] Images backend/frontend construites localement ; versions Python corrigées vérifiées dans l’image backend.
- [x] Audit Python : aucune vulnérabilité connue signalée. Cela ne couvre pas les paquets système de l’image.
- [ ] Accord push main **et publication GHCR automatique des deux images**.
- [ ] Pipeline du nouveau SHA entièrement réussi ; digest et label vérifiés dans GHCR.
- [ ] Accord déploiement Render du digest backend choisi ; accès au tableau de bord et ancien digest disponibles.
- [ ] Vérification de l’image active, des trois sondes et de CORS après déploiement.
- [ ] Accès autorisé aux dépendances distantes ; schéma/Alembic et Redis vérifiés.
- [ ] Accord et environnement de recette isolé ; scénario sécurité exécuté sur le digest publié.
- [ ] Compte/périmètre de test production autorisé ; principaux parcours distants vérifiés.

**Déploiement non terminé tant que les cases distantes restent ouvertes.** Le commit local n’autorise aucune des actions suivantes.
