# User stories — Plateforme DevSecOps de gestion d’incidents

## US-01 — Se connecter à la plateforme

### User story

En tant qu’utilisateur disposant d’un compte,  
je veux me connecter à la plateforme,  
afin d’accéder aux fonctionnalités autorisées par mon rôle.

### Priorité

Must

### Préconditions

- un compte correspondant à l’adresse électronique saisie existe ;
- le compte est actif ;
- un mot de passe a été défini pour ce compte.

### Règles métier

- seuls les comptes actifs peuvent accéder à la plateforme ;
- l’utilisateur accède aux fonctionnalités correspondant à son rôle : `USER`, `TECHNICIAN` ou `ADMIN` ;
- une session expirée oblige l’utilisateur à se reconnecter ;
- la déconnexion met fin à la session.

### Règles de sécurité

- le mot de passe est haché et n’apparaît jamais dans les logs ;
- le rôle et l’état du compte sont vérifiés côté back-end ;
- un message générique est affiché lorsque la connexion échoue ;
- le jeton ou la session possède une durée limitée ;
- les tentatives de connexion sont journalisées.

### Informations affichées

- champs adresse électronique et mot de passe ;
- message de validation ou d’erreur ;
- redirection vers l’espace correspondant au rôle.

### Critères d’acceptation

- un utilisateur actif avec des identifiants valides peut se connecter ;
- un mot de passe incorrect ou un compte désactivé entraîne un refus ;
- un utilisateur non connecté ne peut pas accéder aux routes protégées ;
- le rôle est récupéré après la connexion ;
- une session expirée est refusée.

### Cas d’erreur

- compte inexistant ;
- mot de passe incorrect ;
- compte désactivé ;
- champs manquants ou invalides ;
- session ou jeton expiré.

### Dépendances

- modèle `User` ;
- rôles utilisateurs ;
- stockage sécurisé des mots de passe ;
- système de session ou de jeton.

### Tâches techniques

- créer le modèle `User` et l’énumération `UserRole` ;
- créer le schéma et la route d’authentification ;
- vérifier le mot de passe et l’état du compte ;
- générer et vérifier la session ou le jeton ;
- créer la page de connexion ;
- protéger les routes privées ;
- ajouter les tests et les logs d’audit.

---

## US-02 — Créer un incident

### User story

En tant qu’utilisateur connecté,  
je veux déclarer un incident,  
afin de signaler un problème informatique ou de sécurité.

### Priorité

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- les catégories et priorités disponibles sont définies.

### Règles métier

- le titre et la description sont obligatoires ;
- la catégorie doit être valide ;
- la priorité par défaut est `MEDIUM` ;
- le statut initial est toujours `OPEN` ;
- l’auteur est automatiquement l’utilisateur connecté ;
- l’incident n’est pas attribué à sa création ;
- une référence unique et une date de création sont générées ;
- la création est enregistrée dans l’historique.

### Règles de sécurité

- l’auteur est déterminé côté back-end ;
- l’utilisateur ne peut pas choisir le statut initial ;
- les données sont validées côté front-end et back-end ;
- la taille du titre et de la description est limitée ;
- aucune donnée sensible inutile n’est enregistrée dans les logs.

### Informations affichées

- titre, description, catégorie et priorité ;
- message de confirmation après la création ;
- référence et statut du nouvel incident.

### Critères d’acceptation

- un utilisateur actif peut créer un incident avec des données valides ;
- l’incident reçoit le statut `OPEN` ;
- la priorité devient `MEDIUM` si elle n’est pas renseignée ;
- l’incident apparaît dans la liste de l’utilisateur ;
- une entrée d’historique et un événement d’audit sont créés.

### Cas d’erreur

- utilisateur non authentifié ou compte désactivé ;
- titre ou description manquant ;
- catégorie ou priorité invalide ;
- données trop longues ;
- erreur lors de l’enregistrement.

### Dépendances

- US-01 — Se connecter à la plateforme ;
- modèles `User` et `Incident` ;
- rôles utilisateurs ;
- PostgreSQL, SQLAlchemy et Alembic ;
- catégories, priorités et statuts.

### Tâches techniques

- créer le modèle SQLAlchemy `Incident` ;
- créer les énumérations de statut, priorité et catégorie ;
- créer les schémas `IncidentCreate` et `IncidentResponse` ;
- créer la migration de la table `incidents` ;
- créer la route `POST /incidents` ;
- créer le formulaire Next.js ;
- enregistrer l’historique et le log d’audit ;
- ajouter les validations et les tests.

---

## US-03 — Consulter ses incidents

### User story

En tant qu’utilisateur connecté,  
je veux consulter la liste de mes incidents,  
afin de suivre leur état d’avancement.

### Priorité

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif.

### Règles métier

- un utilisateur classique ne consulte que les incidents dont il est l’auteur ;
- les incidents sont classés du plus récent au plus ancien ;
- tous les statuts restent consultables ;
- une liste vide est un résultat valide.

### Règles de sécurité

- l’identité de l’utilisateur est récupérée côté back-end ;
- le client ne peut pas choisir librement l’identifiant de l’utilisateur ;
- aucun incident appartenant à un autre utilisateur ne doit être exposé ;
- l’accès est refusé si le compte est inactif ou non authentifié.

### Informations affichées

- référence ;
- titre ;
- catégorie ;
- priorité ;
- statut ;
- dates de création et de modification ;
- technicien attribué, s’il existe.

### Critères d’acceptation

- un utilisateur actif peut consulter ses incidents ;
- seuls ses propres incidents sont affichés ;
- les incidents les plus récents apparaissent en premier ;
- un message adapté apparaît si la liste est vide ;
- sélectionner un incident ouvre sa page de détail.

### Cas d’erreur

- utilisateur non authentifié ;
- compte désactivé ;
- échec de récupération des incidents ;
- paramètres de tri ou de pagination invalides ;
- tentative d’accès aux incidents d’un autre utilisateur.

### Dépendances

- US-01 — Se connecter à la plateforme ;
- US-02 — Créer un incident ;
- modèles `User` et `Incident` ;
- relation entre l’auteur et l’incident ;
- schéma `IncidentListItem` ou `IncidentResponse`.

### Tâches techniques

- créer la route `GET /incidents` ou `GET /incidents/me` ;
- filtrer avec l’identité de l’utilisateur connecté ;
- trier les résultats par date décroissante ;
- créer la page « Mes incidents » ;
- gérer le chargement, la liste vide et les erreurs ;
- ajouter les tests d’accès et de filtrage.

---

## US-04 — Consulter le détail d’un incident

### User story

En tant qu’utilisateur autorisé,  
je veux consulter le détail d’un incident,  
afin de connaître le problème déclaré et l’état de son traitement.

### Priorité

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- l’incident existe ;
- l’utilisateur possède les droits nécessaires pour le consulter.

### Règles métier

- un utilisateur classique consulte uniquement les incidents dont il est l’auteur ;
- un technicien consulte les incidents qui lui sont attribués ;
- un administrateur consulte tous les incidents ;
- un incident résolu ou clôturé reste consultable ;
- la consultation seule ne modifie aucune information.

### Règles de sécurité

- l’identité du demandeur est récupérée depuis l’authentification ;
- les autorisations sont vérifiées côté back-end ;
- modifier l’identifiant dans l’URL ne permet pas de contourner les droits ;
- aucune information n’est exposée en cas d’accès non autorisé.

### Informations affichées

- référence, titre et description ;
- catégorie, priorité et statut ;
- auteur et technicien attribué ;
- dates de création, modification, résolution et clôture.

### Critères d’acceptation

- un utilisateur autorisé peut consulter le détail ;
- les informations correspondent à l’incident demandé ;
- un utilisateur classique ne voit pas l’incident d’un autre utilisateur ;
- un technicien voit un incident qui lui est attribué ;
- un administrateur voit tous les incidents ;
- actualiser la page ne modifie pas l’incident.

### Cas d’erreur

- utilisateur non authentifié ou compte désactivé ;
- identifiant d’incident invalide ;
- incident introuvable ;
- utilisateur non autorisé ;
- échec de récupération des informations.

### Dépendances

- US-01 — Se connecter à la plateforme ;
- US-02 — Créer un incident ;
- US-03 — Consulter ses incidents ;
- modèles `User` et `Incident` ;
- schéma `IncidentResponse`.

### Tâches techniques

- créer la route `GET /incidents/{incident_id}` ;
- rechercher l’incident par son identifiant ;
- vérifier les droits selon le rôle et la propriété ;
- retourner le schéma `IncidentResponse` ;
- créer la page de détail Next.js ;
- ajouter les tests de consultation et d’autorisation.

---

## US-05 — Ajouter un commentaire

### User story

En tant qu’utilisateur ou technicien autorisé,  
je veux ajouter un commentaire à un incident,  
afin d’échanger des informations sur son traitement.

### Priorité

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- l’incident existe ;
- l’utilisateur possède les droits nécessaires pour le consulter ;
- l’incident n’a pas le statut `CLOSED`.

### Règles métier

- un utilisateur classique commente uniquement les incidents dont il est l’auteur ;
- un technicien commente uniquement les incidents qui lui sont attribués ;
- un administrateur peut commenter tous les incidents ;
- le commentaire ne peut pas être vide ;
- chaque commentaire est associé à son auteur et à sa date de création.

### Règles de sécurité

- l’auteur du commentaire est déterminé côté back-end ;
- les droits d’accès à l’incident sont vérifiés avant l’ajout ;
- la taille du commentaire est limitée ;
- le contenu est validé avant son affichage ;
- le commentaire complet n’est pas copié dans les logs techniques.

### Informations affichées

- contenu du commentaire ;
- nom ou rôle de l’auteur ;
- date et heure de publication.

### Critères d’acceptation

- un utilisateur autorisé peut publier un commentaire valide ;
- le commentaire apparaît dans les échanges de l’incident ;
- un commentaire vide est refusé ;
- un incident clôturé ne peut plus recevoir de commentaire ;
- l’auteur et la date sont enregistrés automatiquement.

### Cas d’erreur

- utilisateur non authentifié ou compte désactivé ;
- incident introuvable ;
- utilisateur non autorisé ;
- incident clôturé ;
- commentaire vide, invalide ou trop long.

### Dépendances

- US-01 — Se connecter à la plateforme ;
- US-04 — Consulter le détail d’un incident ;
- modèles `User`, `Incident` et `IncidentComment` ;
- gestion des autorisations.

### Tâches techniques

- créer le modèle `IncidentComment` ;
- créer les schémas de création et de réponse ;
- créer la route `POST /incidents/{incident_id}/comments` ;
- ajouter le formulaire de commentaire ;
- afficher les commentaires sur la page de détail ;
- ajouter les validations et les tests.

---

## US-06 — Consulter les incidents à traiter

### User story

En tant que technicien,  
je veux consulter les incidents qui me sont attribués,  
afin d’organiser mon travail.

### Priorité

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- il possède le rôle `TECHNICIAN` ou `ADMIN`.

### Règles métier

- un utilisateur classique ne peut pas accéder à la file de travail des techniciens ;
- un technicien ne consulte que les incidents qui lui sont attribués ;
- un administrateur peut consulter tous les incidents ;
- les incidents clôturés ne sont pas affichés dans la liste principale ;
- une liste vide est un résultat valide ;
- les incidents sont classés par priorité, puis par ancienneté.

### Règles de sécurité

- le rôle est vérifié côté back-end ;
- le filtrage utilise l’identité du technicien connecté ;
- un technicien ne peut pas consulter la file de travail d’un autre technicien ;
- aucun incident non autorisé n’est exposé.

### Informations affichées

- référence et titre ;
- priorité, statut et catégorie ;
- date de création ;
- auteur de l’incident ;
- date d’attribution.

### Critères d’acceptation

- un technicien voit uniquement les incidents qui lui sont attribués ;
- un administrateur peut voir l’ensemble des incidents ;
- les incidents clôturés sont exclus de la liste principale ;
- les incidents prioritaires et anciens apparaissent en premier ;
- un message adapté apparaît si la liste est vide.

### Cas d’erreur

- utilisateur non authentifié ou compte désactivé ;
- utilisateur sans rôle autorisé ;
- échec de récupération de la liste ;
- paramètres de tri invalides.

### Dépendances

- US-01 — Se connecter à la plateforme ;
- US-07 — Attribuer un incident ;
- modèles `User` et `Incident` ;
- relation `assigned_to` ;
- gestion des rôles.

### Tâches techniques

- créer la route de consultation des incidents attribués ;
- filtrer par technicien connecté ;
- exclure les incidents clôturés ;
- appliquer le tri par priorité et ancienneté ;
- créer la page « Incidents à traiter » ;
- ajouter les tests de rôle et de filtrage.

---

## US-07 — Attribuer un incident

### User story

En tant qu’administrateur,  
je veux attribuer un incident à un technicien,  
afin qu’une personne soit responsable de son traitement.

### Priorité

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- il possède le rôle `ADMIN` ;
- l’incident existe et n’est pas clôturé ;
- le technicien sélectionné possède un compte actif.

### Règles métier

- seul un administrateur peut attribuer ou réattribuer un incident ;
- un incident ne peut être attribué qu’à un utilisateur `TECHNICIAN` ;
- un incident peut être réattribué à un autre technicien ;
- chaque attribution est enregistrée dans l’historique ;
- le technicien attribué devient responsable du traitement.

### Règles de sécurité

- le rôle de l’administrateur est vérifié côté back-end ;
- le technicien sélectionné doit être actif et posséder le bon rôle ;
- le client ne peut pas attribuer un incident à un utilisateur arbitraire ;
- l’ancienne et la nouvelle attribution sont journalisées.

### Informations affichées

- incident concerné ;
- technicien actuellement attribué ;
- liste des techniciens actifs ;
- confirmation de l’attribution.

### Critères d’acceptation

- un administrateur peut attribuer un incident à un technicien actif ;
- le technicien attribué apparaît dans le détail de l’incident ;
- l’incident apparaît dans la file de travail du technicien ;
- une réattribution remplace l’ancienne attribution ;
- l’historique conserve chaque changement.

### Cas d’erreur

- utilisateur non authentifié, inactif ou non administrateur ;
- incident introuvable ou clôturé ;
- technicien introuvable, inactif ou avec un rôle invalide ;
- erreur lors de l’enregistrement.

### Dépendances

- US-01 — Se connecter à la plateforme ;
- US-04 — Consulter le détail d’un incident ;
- modèles `User` et `Incident` ;
- rôles utilisateurs ;
- relation `assigned_to` ;
- historique des incidents.

### Tâches techniques

- créer le schéma `IncidentAssign` ;
- créer la route d’attribution ;
- récupérer les techniciens actifs ;
- vérifier les rôles et le statut de l’incident ;
- mettre à jour `assigned_to` ;
- enregistrer l’historique ;
- créer l’interface d’attribution ;
- ajouter les tests.

---

## US-08 — Modifier la priorité

### User story

En tant que technicien ou administrateur,  
je veux modifier la priorité d’un incident,  
afin de refléter sa gravité réelle.

### Priorité

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- il possède le rôle `TECHNICIAN` ou `ADMIN` ;
- l’incident existe et n’est pas clôturé.

### Règles métier

- un utilisateur classique ne peut pas modifier la priorité ;
- un technicien modifie uniquement les incidents qui lui sont attribués ;
- un administrateur peut modifier tous les incidents ;
- la priorité doit être `LOW`, `MEDIUM`, `HIGH` ou `CRITICAL` ;
- l’ancienne et la nouvelle priorité sont enregistrées dans l’historique.

### Règles de sécurité

- le rôle et l’accès à l’incident sont vérifiés côté back-end ;
- seules les priorités autorisées sont acceptées ;
- le client ne peut pas modifier d’autres champs avec cette action ;
- l’auteur de la modification est enregistré automatiquement.

### Informations affichées

- priorité actuelle ;
- priorités disponibles ;
- confirmation après la modification.

### Critères d’acceptation

- un technicien autorisé peut modifier la priorité de son incident ;
- un administrateur peut modifier la priorité de tous les incidents ;
- une valeur invalide est refusée ;
- la nouvelle priorité est immédiatement visible ;
- l’historique conserve l’ancienne et la nouvelle valeur ;
- la liste est mise à jour si elle est triée par priorité.

### Cas d’erreur

- utilisateur non authentifié ou compte désactivé ;
- rôle insuffisant ;
- incident introuvable ou clôturé ;
- technicien non attribué à l’incident ;
- priorité invalide.

### Dépendances

- US-01 — Se connecter à la plateforme ;
- US-04 — Consulter le détail d’un incident ;
- US-07 — Attribuer un incident ;
- énumération `IncidentPriority` ;
- historique des incidents.

### Tâches techniques

- créer le schéma `IncidentPriorityUpdate` ;
- créer la route de modification de priorité ;
- vérifier le rôle et l’attribution ;
- mettre à jour la priorité ;
- enregistrer l’historique ;
- ajouter le contrôle dans l’interface ;
- créer les tests.

---

## US-09 — Modifier le statut

### User story

En tant que technicien ou administrateur,  
je veux modifier le statut d’un incident,  
afin d’indiquer l’avancement de son traitement.

### Priorité

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- il possède le rôle `TECHNICIAN` ou `ADMIN` ;
- l’incident existe et n’est pas clôturé.

### Règles métier

- un utilisateur classique ne peut pas modifier le statut ;
- un technicien modifie uniquement les incidents qui lui sont attribués ;
- un administrateur peut modifier tous les incidents ;
- les transitions suivent le cycle `OPEN → IN_PROGRESS → RESOLVED → CLOSED` ;
- les passages à `RESOLVED` et `CLOSED` respectent les règles des US-10 et US-11 ;
- chaque changement est enregistré dans l’historique.

### Règles de sécurité

- le rôle, l’attribution et la transition sont vérifiés côté back-end ;
- le client ne peut pas imposer une transition interdite ;
- l’auteur du changement est récupéré depuis l’authentification ;
- seules les informations nécessaires sont modifiées.

### Informations affichées

- statut actuel ;
- prochains statuts autorisés ;
- justification, lorsqu’elle est requise ;
- confirmation du changement.

### Critères d’acceptation

- un utilisateur autorisé peut effectuer une transition valide ;
- une transition non autorisée est refusée ;
- l’ancien et le nouveau statut sont enregistrés ;
- l’historique indique l’auteur et la date ;
- la liste est mise à jour si elle est filtrée par statut.

### Cas d’erreur

- utilisateur non authentifié ou compte désactivé ;
- rôle insuffisant ;
- incident introuvable ou clôturé ;
- technicien non attribué ;
- transition non autorisée ;
- justification obligatoire absente.

### Dépendances

- US-01 — Se connecter à la plateforme ;
- US-04 — Consulter le détail d’un incident ;
- US-07 — Attribuer un incident ;
- US-10 — Résoudre un incident ;
- US-11 — Clôturer un incident ;
- énumération `IncidentStatus` ;
- historique des incidents.

### Tâches techniques

- créer le schéma `IncidentStatusUpdate` ;
- créer la route de modification du statut ;
- vérifier les transitions autorisées ;
- enregistrer les dates et l’historique ;
- créer le contrôle de statut dans l’interface ;
- ajouter les tests.

---

## US-10 — Résoudre un incident

### User story

En tant que technicien ou administrateur,  
je veux indiquer la solution appliquée et marquer un incident comme résolu,  
afin de signaler que le problème a été corrigé.

### Priorité

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- il possède le rôle `TECHNICIAN` ou `ADMIN` ;
- l’incident existe et possède le statut `IN_PROGRESS` ;
- pour un technicien, l’incident lui est attribué.

### Règles métier

- un utilisateur classique ne peut pas résoudre un incident ;
- un technicien résout uniquement les incidents qui lui sont attribués ;
- un administrateur peut résoudre tous les incidents ;
- une description non vide de la solution est obligatoire ;
- le statut devient `RESOLVED` ;
- une date de résolution est enregistrée ;
- l’incident reste consultable et n’est pas encore clôturé.

### Règles de sécurité

- le rôle et l’attribution sont vérifiés côté back-end ;
- la solution est validée et sa taille est limitée ;
- l’auteur de la résolution est récupéré depuis l’authentification ;
- la résolution et le changement de statut sont enregistrés ensemble.

### Informations affichées

- solution appliquée ;
- auteur de la résolution ;
- date de résolution ;
- nouveau statut.

### Critères d’acceptation

- un technicien autorisé peut résoudre un incident qui lui est attribué ;
- la résolution est refusée si la solution est vide ;
- le statut devient `RESOLVED` ;
- la solution et la date sont enregistrées ;
- l’auteur de l’incident peut consulter la solution ;
- la résolution apparaît dans l’historique.

### Cas d’erreur

- utilisateur non authentifié ou compte désactivé ;
- rôle insuffisant ;
- incident introuvable ;
- incident non attribué au technicien ;
- statut différent de `IN_PROGRESS` ;
- solution vide ou invalide.

### Dépendances

- US-01 — Se connecter à la plateforme ;
- US-04 — Consulter le détail d’un incident ;
- US-07 — Attribuer un incident ;
- US-09 — Modifier le statut ;
- historique des incidents.

### Tâches techniques

- créer le schéma `IncidentResolve` ;
- créer la route de résolution ;
- vérifier le statut et l’attribution ;
- enregistrer la solution et la date ;
- passer le statut à `RESOLVED` ;
- enregistrer l’historique ;
- créer le formulaire de résolution ;
- ajouter les tests.

---

## US-11 — Clôturer un incident

### User story

En tant qu’administrateur ou utilisateur autorisé,  
je veux clôturer un incident résolu,  
afin de terminer officiellement son cycle de traitement.

### Priorité

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- l’incident existe ;
- l’incident possède le statut `RESOLVED` ;
- l’utilisateur est l’auteur de l’incident ou possède le rôle `ADMIN`.

### Règles métier

- seul l’auteur de l’incident ou un administrateur peut le clôturer ;
- seul un incident résolu peut être clôturé ;
- le statut devient `CLOSED` ;
- une date de clôture est enregistrée ;
- un incident clôturé reste consultable mais ne peut plus être modifié ;
- la clôture est enregistrée dans l’historique.

### Règles de sécurité

- le rôle ou la propriété de l’incident est vérifié côté back-end ;
- le client ne peut pas clôturer directement un incident non résolu ;
- l’auteur de la clôture est récupéré depuis l’authentification ;
- aucune autre donnée de l’incident n’est modifiée.

### Informations affichées

- solution appliquée ;
- date de résolution ;
- bouton de clôture pour les utilisateurs autorisés ;
- date et auteur de la clôture.

### Critères d’acceptation

- l’auteur ou un administrateur peut clôturer un incident résolu ;
- le statut devient `CLOSED` ;
- la date de clôture est enregistrée ;
- l’incident ne peut plus recevoir de commentaire ou de modification ;
- la clôture apparaît dans l’historique.

### Cas d’erreur

- utilisateur non authentifié ou compte désactivé ;
- incident introuvable ;
- utilisateur non autorisé ;
- incident non résolu ;
- incident déjà clôturé.

### Dépendances

- US-01 — Se connecter à la plateforme ;
- US-04 — Consulter le détail d’un incident ;
- US-10 — Résoudre un incident ;
- énumération `IncidentStatus` ;
- historique des incidents.

### Tâches techniques

- créer la route de clôture ;
- vérifier le statut et les droits ;
- passer le statut à `CLOSED` ;
- enregistrer la date et l’historique ;
- ajouter le bouton de clôture ;
- bloquer les modifications ultérieures ;
- créer les tests.

---

## US-12 — Consulter l’historique

### User story

En tant qu’utilisateur autorisé,  
je veux consulter l’historique d’un incident,  
afin de connaître les actions et les modifications réalisées.

### Priorité

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- l’incident existe ;
- l’utilisateur possède le droit de le consulter.

### Règles métier

- l’auteur consulte l’historique de ses incidents ;
- le technicien consulte l’historique des incidents qui lui sont attribués ;
- l’administrateur consulte tous les historiques ;
- l’historique est en lecture seule ;
- les événements sont classés du plus récent au plus ancien ;
- les modifications importantes sont conservées.

### Règles de sécurité

- les droits sont vérifiés côté back-end ;
- un utilisateur ne peut pas modifier ou supprimer l’historique ;
- aucune donnée sensible des logs techniques n’est exposée ;
- seules les informations utiles à la traçabilité métier sont affichées.

### Informations affichées

- type d’action ;
- auteur de l’action ;
- ancienne et nouvelle valeur, si nécessaire ;
- date et heure ;
- justification ou solution, lorsqu’elle existe.

### Critères d’acceptation

- un utilisateur autorisé peut consulter l’historique ;
- chaque événement présente son auteur et sa date ;
- les changements de priorité, statut et attribution sont visibles ;
- un utilisateur non autorisé ne voit aucune information ;
- l’historique ne peut pas être modifié depuis l’interface.

### Cas d’erreur

- utilisateur non authentifié ou compte désactivé ;
- incident introuvable ;
- utilisateur non autorisé ;
- échec de récupération de l’historique.

### Dépendances

- US-04 — Consulter le détail d’un incident ;
- US-05 — Ajouter un commentaire ;
- US-07 à US-11 ;
- modèle `IncidentHistory` ;
- relations avec les utilisateurs et les incidents.

### Tâches techniques

- créer le modèle `IncidentHistory` ;
- créer le schéma de réponse ;
- enregistrer les événements métier ;
- créer la route de consultation ;
- afficher une chronologie sur la page de détail ;
- ajouter les tests de lecture et d’autorisation.

---

## US-13 — Filtrer les incidents

### User story

En tant que technicien ou administrateur,  
je veux filtrer les incidents par statut, priorité et catégorie,  
afin de retrouver rapidement les incidents pertinents.

### Priorité

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- il possède le rôle `TECHNICIAN` ou `ADMIN` ;
- la liste des incidents est accessible.

### Règles métier

- les filtres peuvent être utilisés séparément ou ensemble ;
- un technicien filtre uniquement les incidents auxquels il a accès ;
- un administrateur filtre tous les incidents ;
- une recherche sans résultat retourne une liste vide ;
- la suppression des filtres restaure la liste par défaut.

### Règles de sécurité

- le périmètre d’accès est appliqué avant les filtres ;
- les valeurs de filtre sont validées côté back-end ;
- un filtre ne permet pas d’accéder à un incident non autorisé ;
- les paramètres invalides sont refusés.

### Informations affichées

- filtres actifs ;
- nombre de résultats ;
- liste des incidents correspondants ;
- message si aucun résultat n’est trouvé.

### Critères d’acceptation

- les incidents peuvent être filtrés par statut, priorité et catégorie ;
- plusieurs filtres peuvent être combinés ;
- les résultats respectent les droits de l’utilisateur ;
- retirer les filtres réaffiche la liste initiale ;
- une liste vide est affichée si aucun incident ne correspond.

### Cas d’erreur

- utilisateur non authentifié ou compte désactivé ;
- rôle insuffisant ;
- valeur de filtre invalide ;
- échec de récupération des résultats.

### Dépendances

- US-03 — Consulter ses incidents ;
- US-06 — Consulter les incidents à traiter ;
- énumérations de statut, priorité et catégorie ;
- système de gestion des rôles.

### Tâches techniques

- ajouter les paramètres de filtre aux routes de liste ;
- valider les valeurs reçues ;
- construire les requêtes SQLAlchemy ;
- créer les contrôles de filtre dans l’interface ;
- gérer l’état vide ;
- ajouter les tests de combinaison et d’autorisation.

---

## US-14 — Consulter le tableau de bord

### User story

En tant que technicien ou administrateur,  
je veux consulter une synthèse des incidents,  
afin d’identifier rapidement les incidents ouverts, critiques ou en retard.

### Priorité

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- il possède le rôle `TECHNICIAN` ou `ADMIN` ;
- des données d’incidents sont disponibles.

### Règles métier

- un technicien voit les indicateurs de ses incidents attribués ;
- un administrateur voit les indicateurs globaux ;
- les indicateurs sont calculés à partir des données actuelles ;
- un incident en retard est un incident non clôturé dépassant le délai défini ;
- l’absence d’incident produit des valeurs égales à zéro.

### Règles de sécurité

- les statistiques respectent le périmètre d’accès du rôle ;
- les agrégations sont calculées côté back-end ;
- aucune information d’un incident non autorisé n’est exposée ;
- les données sensibles ne sont pas affichées dans les graphiques.

### Informations affichées

- nombre d’incidents ouverts et en cours ;
- nombre d’incidents critiques ;
- nombre d’incidents résolus et clôturés ;
- nombre d’incidents en retard ;
- liste des incidents récents ou prioritaires.

### Critères d’acceptation

- un technicien voit uniquement les indicateurs liés à ses incidents ;
- un administrateur voit les indicateurs globaux ;
- les compteurs correspondent aux incidents enregistrés ;
- les indicateurs sont mis à jour après une modification ;
- des valeurs nulles sont affichées si aucun incident n’existe.

### Cas d’erreur

- utilisateur non authentifié ou compte désactivé ;
- rôle insuffisant ;
- échec du calcul ou de la récupération des indicateurs ;
- délai de retard non configuré.

### Dépendances

- US-06 — Consulter les incidents à traiter ;
- US-08 — Modifier la priorité ;
- US-09 — Modifier le statut ;
- modèles `Incident` et `User` ;
- règle définissant les incidents en retard.

### Tâches techniques

- créer les requêtes d’agrégation ;
- créer la route du tableau de bord ;
- appliquer le périmètre selon le rôle ;
- créer les cartes et graphiques simples ;
- gérer le chargement et les erreurs ;
- ajouter les tests des indicateurs.

---

## US-15 — Gérer les comptes

### User story

En tant qu’administrateur,  
je veux créer, désactiver et modifier les comptes utilisateurs,  
afin de contrôler l’accès à la plateforme.

### Priorité

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- il possède le rôle `ADMIN`.

### Règles métier

- seul un administrateur peut gérer les comptes ;
- l’adresse électronique d’un compte est unique ;
- un compte possède un rôle `USER`, `TECHNICIAN` ou `ADMIN` ;
- un compte désactivé ne peut plus se connecter ;
- les comptes liés à des incidents ne sont pas supprimés définitivement ;
- chaque modification de compte est journalisée.

### Règles de sécurité

- les droits administrateur sont vérifiés côté back-end ;
- les mots de passe sont hachés ;
- un administrateur ne peut pas choisir un mot de passe visible pour un utilisateur ;
- les changements de rôle et d’état sont enregistrés ;
- les informations sensibles ne sont jamais retournées par l’API.

### Informations affichées

- nom et adresse électronique ;
- rôle ;
- état actif ou désactivé ;
- date de création ;
- actions autorisées.

### Critères d’acceptation

- un administrateur peut créer un compte valide ;
- il peut modifier le rôle d’un compte ;
- il peut activer ou désactiver un compte ;
- un compte désactivé ne peut plus se connecter ;
- une adresse électronique déjà utilisée est refusée ;
- les changements apparaissent dans le journal d’audit.

### Cas d’erreur

- utilisateur non authentifié, inactif ou non administrateur ;
- adresse électronique invalide ou déjà utilisée ;
- rôle invalide ;
- compte introuvable ;
- tentative de suppression définitive d’un compte lié à des incidents.

### Dépendances

- US-01 — Se connecter à la plateforme ;
- modèle `User` ;
- énumération `UserRole` ;
- système de hachage des mots de passe ;
- journal d’audit.

### Tâches techniques

- créer les schémas de création et de modification de compte ;
- créer les routes d’administration ;
- vérifier l’unicité de l’adresse électronique ;
- hacher les mots de passe ;
- créer la page de gestion des comptes ;
- journaliser les modifications ;
- ajouter les tests de rôle et de validation.

---

## US-16 — Consulter les journaux d’audit

### User story

En tant qu’administrateur,  
je veux consulter les événements sensibles de l’application,  
afin de détecter les actions anormales et de garantir la traçabilité.

### Priorité

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- il possède le rôle `ADMIN` ;
- des événements d’audit ont été enregistrés.

### Règles métier

- seul un administrateur peut consulter les journaux d’audit ;
- les événements sont affichés du plus récent au plus ancien ;
- les journaux sont en lecture seule ;
- les connexions, refus d’accès et actions sensibles sont enregistrés ;
- l’absence d’événement produit une liste vide.

### Règles de sécurité

- l’accès est vérifié côté back-end ;
- les mots de passe, jetons et contenus sensibles ne sont jamais enregistrés ;
- les journaux ne peuvent pas être modifiés depuis l’application ;
- seules les informations nécessaires à l’analyse sont affichées ;
- les consultations du journal peuvent elles-mêmes être journalisées.

### Informations affichées

- type d’événement ;
- utilisateur concerné, s’il est connu ;
- ressource concernée ;
- résultat de l’action ;
- date et heure ;
- adresse IP ou informations techniques utiles.

### Critères d’acceptation

- un administrateur peut consulter les événements d’audit ;
- les événements sont classés par date décroissante ;
- les connexions réussies et échouées sont visibles ;
- les changements de rôle, d’attribution, de priorité et de statut sont traçables ;
- aucune donnée sensible n’est affichée ;
- un utilisateur non administrateur ne peut pas accéder aux journaux.

### Cas d’erreur

- utilisateur non authentifié ou compte désactivé ;
- utilisateur non administrateur ;
- échec de récupération des journaux ;
- paramètres de filtre invalides.

### Dépendances

- US-01 — Se connecter à la plateforme ;
- US-07 à US-11 ;
- US-15 — Gérer les comptes ;
- modèle `AuditLog` ;
- mécanisme de journalisation des événements.

### Tâches techniques

- créer le modèle `AuditLog` ;
- créer le service de journalisation ;
- enregistrer les événements sensibles ;
- créer la route réservée aux administrateurs ;
- créer la page de consultation ;
- ajouter des filtres simples ;
- ajouter les tests d’accès et de confidentialité.