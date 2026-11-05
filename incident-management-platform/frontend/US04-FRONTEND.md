# US-04 — Détail d’un incident

Route : `/dashboard/incidents/[id]`, dans le layout authentifié existant. La page attend les `params` Next.js puis transmet l’identifiant au composant client. La référence de chaque ligne de la liste est un lien accessible au clavier vers cette page.

`getIncident(id, signal)` appelle `GET /incidents/{id}` via le helper API commun et la réécriture `/api/backend`. Le cookie HttpOnly est transmis avec `credentials: include`. Aucun identifiant d’auteur n’est envoyé et aucun filtrage d’autorisation n’est effectué côté frontend. Les données viennent de l’appel de détail, pas d’une copie de la liste.

Le détail affiche référence, titre, description, catégorie, priorité, statut, affectation, résolution et les quatre dates. Les valeurs optionnelles absentes ont des libellés explicites. Le nom du technicien n’étant pas fourni par cette API, une affectation existante affiche son identifiant sans inventer de nom. Les textes restent échappés par React et conservent leurs sauts de ligne.

Les badges de statut et priorité sont partagés entre la liste et le détail dans `incident-badges.tsx`. Les panneaux, boutons, titre et états d’erreur reprennent les composants existants.

États : chargement annoncé ; 404 avec le même message pour un incident inexistant ou inaccessible ; 422 de route invalide présenté comme indisponible ; 401 avec reconnexion conservant la destination ; autres erreurs avec réessai. Retour à la liste toujours disponible. Les requêtes sont annulées au démontage, limitées à 12 secondes, et les réponses obsolètes ignorées. Le composant se réinitialise lorsque l’utilisateur ou l’identifiant change.

Vérifications : lint, TypeScript, build ; tests navigateur pour lien au clavier, rechargement direct, appel GET sans body ni paramètre utilisateur, valeurs optionnelles absentes et présentes, échappement du texte, 404/401/403/422/500 et panne réseau, réessai, chargement, retour et mobile. Parcours réel FastAPI/PostgreSQL isolés avec redirection réseau du navigateur de test : connexion HttpOnly, création, liste, détail 200 et détail inexistant 404. Aucune donnée métier modifiée.
