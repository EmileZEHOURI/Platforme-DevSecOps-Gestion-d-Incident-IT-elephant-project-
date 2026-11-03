# US-02 — Créer un incident

La page `/dashboard/incidents/new` utilise le layout authentifié existant et les composants Button, Badge et PageHeader. Elle est accessible depuis `/dashboard/incidents`, dont le message indique désormais que la création est disponible mais que la consultation reste à venir.

`src/types/incident.ts` contient les types de requête/réponse et les libellés des catégories et priorités. `src/services/incident.service.ts` construit explicitement un JSON contenant uniquement title, description, category et priority. L’appel utilise le client commun, `/api/backend/incidents` et `credentials: include` ; Next.js transmet la requête au `POST /incidents` de FastAPI.

La validation compte les caractères Unicode après suppression des espaces périphériques, comme le schéma backend. Les limites sont 5–150 pour le titre et 10–5000 pour la description. La priorité initiale est MEDIUM. Les contrôles clients complètent la validation serveur sans la remplacer.

Le formulaire annonce les erreurs, place le focus sur le premier champ invalide et désactive les champs pendant la soumission. Un verrou empêche les envois concurrents. Il conserve la saisie sur erreur et distingue 422, 401, 403, erreurs serveur et absence de réponse. Aucun réessai automatique n’est effectué : le backend ne fournit pas de clé d’idempotence. La saisie n’est pas stockée dans le navigateur et n’est donc pas conservée après un rechargement ou une reconnexion.

Après un 201, la confirmation affiche la référence, le titre, le statut, la catégorie, la priorité et la date renvoyés par l’API. Deux actions permettent de revenir à l’espace incidents ou de créer un nouveau signalement. Aucune route de détail ou liste API inexistante n’est appelée.

Vérifications : lint et TypeScript ; parcours navigateur simulant 422, 401, 403, 500 et panne réseau ; validation des limites, champs JSON autorisés, doubles clics, confirmation, remise à zéro et annulation ; captures desktop 1440×1000 et mobile 390×844. Un parcours supplémentaire a utilisé le vrai FastAPI connecté à un PostgreSQL temporaire isolé, via redirection réseau du navigateur de test : connexion HttpOnly et création 201 confirmées. Les données applicatives n’ont pas été utilisées.
