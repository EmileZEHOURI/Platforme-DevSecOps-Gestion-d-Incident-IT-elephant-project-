# US-03 — Consulter mes incidents

La page existante `/dashboard/incidents` utilise `IncidentList` et conserve le shell, PageHeader, Button, Badge et StatePanel. Le tableau affiche référence, titre, catégorie, priorité, statut et date de création ; sur écran étroit, sa zone défile horizontalement au clavier ou au toucher.

`listIncidents()` dans `src/services/incident.service.ts` appelle `GET /incidents` via le helper API existant, donc `/api/backend/incidents` depuis le navigateur, avec le cookie HttpOnly et `credentials: include`. Aucun paramètre utilisateur ni body n’est envoyé. Le composant affiche la liste dans l’ordre reçu sans tri ni filtrage local.

États : chargement annoncé, liste vide avec accès au formulaire, erreurs réseau/serveur avec réessai, 401 avec lien de reconnexion et 403 explicite. Le bouton Actualiser recharge la réponse. Les requêtes sont annulées au démontage et expirent après 12 secondes ; les réponses obsolètes ne modifient pas la page. Un changement de session réinitialise la vue. Aucune donnée n’est stockée dans le navigateur.

Le retour depuis la confirmation US-02 charge la liste réelle. Il n’existe pas encore de route de détail branchée : les lignes ne proposent donc pas de lien factice. Cette intégration remplace les mentions de consultation à venir dans la page incidents ; elle ne branche pas les indicateurs du dashboard.

Vérifications : lint, TypeScript, build ; tests navigateur pour ordre exact, GET sans paramètres/body, six colonnes, chargement, liste vide, 401/403/500, panne réseau, réessai, navigation et largeur mobile. Parcours réel sur FastAPI/PostgreSQL isolés, avec redirection des requêtes dans le navigateur de test : connexion HttpOnly, création 201, retour à la liste 200 et comparaison exacte des références affichées à la réponse backend. Aucune donnée métier modifiée.
