# US-05 — Ajouter un commentaire

La section `IncidentComments` est intégrée à la colonne principale du détail US-04. Elle reprend les panneaux, boutons, badges et styles du formulaire d’incident. Le type `CommentResponse` comprend les identifiants, le contenu, la date de création et la date de mise à jour nullable, conformément au schéma backend.

Le service `createComment` appelle `POST /incidents/{incident_id}/comments` via le client API commun : cookie HttpOnly, credentials include, réécriture Next.js /api/backend. Le body est construit explicitement avec uniquement content, nettoyé des espaces périphériques. Aucun auteur, identifiant d’incident ni date n’est envoyé dans le body.

Validation : 1 à 5000 caractères Unicode après trim. Champs et bouton désactivés pendant l’envoi, verrou contre les doubles soumissions, pas de réessai automatique. Les erreurs conservent la saisie. Les réponses 422, 401, 403, 404, 409 et erreurs réseau/serveur ont des messages adaptés. Une erreur réseau précise que l’enregistrement peut avoir eu lieu pour éviter un doublon. Le formulaire est bloqué pour CLOSED et après un 409 ; le backend reste responsable des permissions et du statut effectif.

Après un 201, le commentaire renvoyé par l’API est ajouté à la section, avec contenu, auteur et date. Le nom du membre connecté est utilisé uniquement si son identifiant correspond à author_id ; sinon l’identifiant est affiché. Les textes sont échappés et les retours à la ligne conservés. Un message de confirmation est annoncé et le champ est vidé uniquement après succès.

Il n’existe pas encore de GET comments ni de commentaires dans IncidentResponse : la section montre uniquement les ajouts confirmés pendant cette consultation et le précise dans l’interface. Un rechargement ou une navigation efface cet affichage local, mais pas les commentaires enregistrés en base. Aucun historique fictif et aucun stockage navigateur ne sont ajoutés. La saisie n’est pas persistée lors d’une reconnexion.

Validation : lint, TypeScript, build ; tests navigateur avec réponses simulées couvrant le body autorisé, trim, limites, double clic, plusieurs ajouts, conservation du texte, états d’erreur, CLOSED et mobile. Un parcours supplémentaire utilise le vrai FastAPI sur PostgreSQL isolé via redirection réseau du navigateur de test : connexion HttpOnly, création d’incident, détail, POST commentaire 201 et affichage immédiat vérifiés. Aucune donnée métier utilisée.
