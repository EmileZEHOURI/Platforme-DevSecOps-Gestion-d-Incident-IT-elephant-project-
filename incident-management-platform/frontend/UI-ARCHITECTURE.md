# Interface

Direction ECC : outil interne sobre, sidebar anthracite, contenu clair, accent vert pétrole. Tokens dans globals.css et composants dans components/ui.tsx. Cibles : 1440x900 et 390x844. La hiérarchie privilégie les incidents et la disponibilité réelle des services.

Routes : / redirige vers /dashboard. Le diagnostic initial est conservé dans /dashboard/services. /login gère la connexion ; /dashboard/incidents prépare le module ; /dashboard/account affiche le profil réel. Les indicateurs restent indisponibles tant que les endpoints incidents n’existent pas.

Authentification : NEXT_PUBLIC_API_URL, credentials include, cookie HttpOnly géré exclusivement par FastAPI. Aucun stockage de jeton dans JavaScript. Vérification /auth/me avant affichage puis à la navigation, au focus et toutes les 60 secondes. Un 401 redirige vers /login. Le garde client ne remplace pas les autorisations serveur : toute future API privée doit contrôler l’identité et les droits côté FastAPI.

En local, utiliser le même hôte pour les deux services : localhost:3000 avec localhost:8000, ou 127.0.0.1:3000 avec 127.0.0.1:8000. Le cookie SameSite=Lax ne permet pas de mélanger localhost et 127.0.0.1. Les deux origines frontend sur le port 3000 sont déjà autorisées par CORS. En production : HTTPS et déploiement compatible avec cette politique de cookie.

États : chargement session et services ; données incidents non disponibles sans faux zéro ; erreurs réseau avec reprise ; succès login et logout ; services partiellement disponibles ; 401 redirigé et 403 explicité. Menu mobile, focus visible, labels, messages accessibles et réduction des animations prévus.

## Correction de session (30 octobre 2026)

Le navigateur appelle désormais /api/backend sur la même origine que le frontend. Next.js transmet les requêtes et cookies à API_URL, ou NEXT_PUBLIC_API_URL en compatibilité. Cette règle remplace la contrainte précédente imposant le même hôte aux deux services : localhost:3000 peut maintenant utiliser le backend 127.0.0.1:8000. Le cookie HttpOnly et SameSite=Lax reste inchangé. Redémarrer Next.js après modification de la cible API.
