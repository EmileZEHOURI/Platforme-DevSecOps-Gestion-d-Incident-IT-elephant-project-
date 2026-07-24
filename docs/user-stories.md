## US-XX — Nom de la fonctionnalité

### User story

En tant que [rôle],
je veux [action],
afin de [objectif].

### Priorité

Must / Should / Could

### Préconditions

### Règles métier

- règle 1 ;
- règle 2 ;
- règle 3.

### Règles de sécurité

### Critères d’acceptation

- critère 1 ;
- critère 2 ;
- critère 3.

### Cas d’erreur

### Dépendances

- autre user story nécessaire ;
- composant ou fonctionnalité préalable.

### Tâches techniques

- tâche front-end ;
- tâche back-end ;
- tâche base de données ;
- tests ;
- sécurité.

## US-01 — Se connecter à la plateforme

### User story

En tant qu’utilisateur disposant d’un compte,
je veux me connecter à la plateforme,
afin d’accéder aux fonctionnalités autorisées par mon rôle.

### Priorité

Must

### Préconditions 

- un compte correspondant à l’adresse électronique saisie doit exister ;
- le compte doit être actif ;
- un mot de passe doit avoir été défini pour ce compte ;
- l’utilisateur ne doit pas déjà être connecté avec une session valide.

### Règles métier

- seuls les comptes actifs peuvent accéder à la plateforme ;
- l’utilisateur accède aux fonctionnalités correspondant à son rôle : USER, TECHNICIAN ou ADMIN ;
- une session expirée oblige l’utilisateur à se reconnecter ;
- la déconnexion met fin à la session.

### Règles de sécurité 

- le mot de passe est haché et n’apparaît jamais dans les logs ;
- le rôle et l’état du compte sont vérifiés côté back-end ;
- un message générique est affiché lorsque la connexion échoue ;
- le jeton ou la session possède une durée limitée ;
- les tentatives de connexion sont journalisées.

### Critères d’acceptation

- un utilisateur avec des identifiants valides peut se connecter ;
- un utilisateur avec un mot de passe incorrect ne peut pas se connecter ;
- un utilisateur avec un compte désactivé ne peut pas se connecter ;
- un utilisateur connecté est redirigé vers son tableau de bord ;
- le rôle de l’utilisateur est récupéré après la connexion ;
- le mot de passe n’est jamais enregistré ou transmis en clair dans les journaux.

### Cas d’erreur

### Dépendances

- modèle utilisateur ;
- rôles ;
- stockage sécurisé des mots de passe.

### Tâches techniques

- créer la page de connexion ;
- créer le formulaire ;
- créer la route d’authentification ;
- vérifier le mot de passe ;
- générer la session ou le jeton ;
- protéger les routes privées ;
- créer les tests de connexion ;
- journaliser les tentatives.


## US-02 — Créer un incident

### User story

En tant qu’utilisateur, je veux déclarer un incident afin de signaler un problème informatique ou de sécurité.

### Priorité

Must 

### Préconditions 

- l’utilisateur est authentifié ;
- son compte est actif ;
- les catégories et priorités disponibles sont définies.

### Règles métier

- le titre et la description sont obligatoires ;
- la catégorie doit être valide ;
- la priorité par défaut est MEDIUM ;
- le statut initial est toujours OPEN ;
- l’auteur est automatiquement l’utilisateur connecté ;
- l’incident n’est pas attribué à sa création ;
- une référence unique et une date de création sont générées ;
- la création est enregistrée dans l’historique.

### Règles de sécurité

- l’auteur est déterminé côté back-end ;
- l’utilisateur ne peut pas choisir le statut initial ;
- les données sont validées côté front-end et back-end ;
- la taille du titre et de la description est limitée ;
- aucune donnée sensible inutile n’est enregistrée dans les logs ;
- la création est refusée si l’utilisateur n’est pas autorisé.

### Critères d’acceptation

- un utilisateur actif peut créer un incident avec des données valides ;
- l’incident reçoit le statut OPEN ;
- la priorité devient MEDIUM si elle n’est pas renseignée ;
- l’incident apparaît dans la liste de l’utilisateur ;
- les données manquantes ou invalides sont refusées ;
- l’utilisateur ne peut pas créer un incident au nom d’une autre personne ;
- une entrée d’historique et un événement d’audit sont créés.

### Cas d’erreur

### Dépendances

- US-01 — Se connecter à la plateforme ;
- l’existence du modèle User ;
- la définition des rôles ;
- la protection des routes privées ;
- la connexion à PostgreSQL ;
- la configuration de SQLAlchemy ;
- la gestion des migrations avec Alembic ;
- la définition des catégories, priorités et statuts.

### Tâches techniques

- créer le modèle SQLAlchemy Incident ;
- créer les énumérations de statut, priorité et catégorie ;
- créer les schémas IncidentCreate et IncidentResponse ;
- créer la migration de la table incidents ;
- créer la route POST /incidents ;
- récupérer l’utilisateur authentifié ;
- enregistrer l’incident, l’historique et le log d’audit ;
- créer le formulaire Next.js ;
- ajouter la validation et les tests.


## US-03 — Consulter ses incidents

### User story

En tant qu’utilisateur, je veux consulter la liste de mes incidents afin de suivre leur état d’avancement.

### Priorité

Must 

### Préconditions 

- l’utilisateur est authentifié ;
- son compte est actif ;
- des incidents peuvent être associés à son compte.

### Règles métier

- un utilisateur classique ne consulte que les incidents dont il est l’auteur ;
- les incidents sont classés du plus récent au plus ancien ;
- tous les statuts restent consultables ;
- une liste vide est un résultat valide ;
- chaque incident affiche les informations essentielles : référence, titre, catégorie, priorité, statut et date de création.

### Règles de sécurité

- l’identité de l’utilisateur est récupérée côté back-end ;
- le client ne peut pas choisir librement l’identifiant de l’utilisateur ;
- aucun incident appartenant à un autre utilisateur ne doit être exposé ;
- l’accès est refusé si le compte est inactif ou non authentifié.

### Critères d’acceptation

- un utilisateur actif peut consulter ses incidents ;
- seuls ses propres incidents sont affichés ;
- les incidents les plus récents apparaissent en premier ;
- chaque incident présente les informations essentielles ;
- un message adapté apparaît si la liste est vide ;
- sélectionner un incident permet d’accéder à sa page de détail.

### Informations affichées

Chaque incident présente au minimum :

- sa référence ;
- son titre ;
- sa catégorie ;
- sa priorité ;
- son statut ;
- sa date et son heure de création ;
- sa date de dernière modification ;
- le technicien attribué, s’il existe.

### Cas d’erreur

- l’utilisateur n’est pas authentifié : accès refusé ;
- le compte est désactivé : accès refusé ;
- la récupération des incidents échoue : un message d’erreur est affiché ;
- aucun incident n’est trouvé : une liste vide est affichée, ce n’est pas une erreur ;
- une tentative d’accès aux incidents d’un autre utilisateur est refusée ;
- si les paramètres de tri ou de pagination sont invalides, la requête est rejetée.

### Dépendances

- US-01 — Se connecter à la plateforme ;
- US-02 — Créer un incident ;
- modèle SQLAlchemy User ;
- modèle SQLAlchemy Incident ;
- relation entre Incident.created_by et User.id ;
- système d’authentification permettant de récupérer l’utilisateur connecté ;
- schéma de réponse IncidentListItem ou IncidentResponse ;
- connexion à PostgreSQL et repository de consultation des incidents.


### Tâches techniques

- créer la route GET /incidents ou GET /incidents/me ;
- filtrer les incidents avec l’identifiant de l’utilisateur connecté ;
- créer un schéma léger comme IncidentListItem ;
- trier les résultats par date décroissante ;
- créer la page « Mes incidents » ;
- gérer l’état vide, le chargement et les erreurs ;
- ajouter les tests d’accès et de filtrage.




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
- l’incident demandé existe.
- l’utilisateur possède les droits nécessaires pour le consulter.

### Règles métier

- un utilisateur classique ne peut consulter que les incidents dont il est l’auteur ;
- un technicien peut consulter les incidents qui lui sont attribués ;
- un administrateur peut consulter tous les incidents ;
- un incident résolu ou clôturé reste consultable ;
- la consultation seule ne modifie aucune information de l’incident ;
- toute modification doit passer par une action dédiée ;
- seules les informations autorisées pour le rôle connecté sont présentées.

### Règles de sécurité 

- l’identité du demandeur est récupérée depuis l’authentification ;
- les autorisations sont vérifiées côté back-end ;
- le front-end ne peut pas imposer l’identité du demandeur ;
- aucune information de l’incident n’est exposée en cas d’accès non autorisé.

### Informations affichées

- référence ;
- titre ;
- description ;
- catégorie ;
- priorité ;
- statut ;
- auteur ;
- technicien attribué ;
- date de création ;
- date de dernière modification ;
- date de résolution, si elle existe ;
- date de clôture, si elle existe.

### Critères d'acceptation

- un utilisateur autorisé peut consulter le détail d’un incident ;
- les informations affichées correspondent à l’incident demandé ;
- un utilisateur classique ne peut pas consulter l’incident d’un autre utilisateur ;
- un technicien peut consulter un incident qui lui est attribué ;
- un administrateur peut consulter n’importe quel incident ;
- consulter ou actualiser la page ne modifie pas l’incident.

### Cas d’erreur

- si l’incident n’existe pas, l’application indique qu’il est introuvable ;
- si l’utilisateur n’est pas authentifié, l’accès est refusé ;
- si son compte est désactivé, l’accès est refusé ;
- s’il n’a pas le droit de consulter l’incident, aucune information n’est exposée.

### Dépendances

- US-01 — Se connecter à la plateforme ;
- US-02 — Créer un incident ;
- US-03 — Consulter la liste de ses incidents ;
- modèles User et Incident ;
- relations entre l’incident, son auteur et son technicien ;
- système d’authentification et gestion des rôles ;
- schéma IncidentResponse.

### Tâches techniques

- créer la route GET /incidents/{incident_id} ;
- rechercher l’incident par son identifiant ;
- vérifier les droits selon le rôle et la propriété de l’incident ;
- retourner le schéma IncidentResponse ;
- créer la page de détail Next.js ;
- afficher les données, le chargement et les erreurs ;
- ajouter les tests d’autorisation et de consultation.




## US-05 — Ajouter un commentaire

### User story

En tant qu’utilisateur ou technicien autorisé
je veux ajouter un commentaire à un incident 
afin d’échanger des informations sur son traitement.

### Priorité 

Must

### Préconditions

-	L’utilisateur est authentifié ;
-	Son compte est actif ;
-	L’incident demandé existe ;
-	L’utilisateur possède les droits nécessaires pour le consulter ;
-	L’incident n’est pas CLOSED.


### Règles métier

-	Un utilisateur classique peut commenter uniquement les incidents dont il est l’auteur ; 
-	Un technicien peut commenter uniquement les incidents qui lui sont attribués ; 
-	Un administrateur peut commenter tous les incidents ; 
-	Le commentaire doit contenir du texte et ne peut pas être vide ; 
-	Chaque commentaire est associé à son auteur et à sa date de création ; 
-	Un commentaire publié ne peut pas être attribué à un autre utilisateur.


### Règles de sécurité 

### Informations affichées

### Critères d'acceptation

### Cas d’erreur

### Dépendances

### Tâches techniques


## US-06 — Consulter les incidents à traiter

### User story

En tant que technicien, 
je veux consulter les incidents qui me sont attribués 
afin d’organiser mon travail.


### Priorité 

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- l’utilisateur possède le rôle TECHNICIAN ou ADMIN.

### Règles métier

- un utilisateur classique ne peut pas accéder à la file de travail des techniciens ;
- un technicien ne consulte que les incidents qui lui sont attribués ;
- un administrateur peut consulter tous les incidents ;
- les incidents clôturés ne sont pas affichés dans la liste principale des incidents à traiter ;
- une liste vide est un résultat valide ;
- les incidents sont classés par priorité, puis par ancienneté.

### Règles de sécurité 

### Informations affichées

### Critères d'acceptation

### Cas d’erreur

### Dépendances

### Tâches techniques


## US-07 — Attribuer un incident

### User story

En tant qu’administrateur,
je veux attribuer un incident à un technicien 
afin qu’une personne soit responsable de son traitement.

### Priorité

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- l’utilisateur possède le rôle ADMIN ;
- l’incident existe ;
- l’incident n’a pas le statut CLOSED ;
- le technicien sélectionné possède un compte actif.

### Règles métier

- seul un administrateur peut attribuer ou réattribuer un incident ;
- un incident ne peut être attribué qu’à un utilisateur ayant le rôle TECHNICIAN ;
- un incident ne peut pas être attribué à un utilisateur classique ou à un administrateur ;
- un incident peut être réattribué à un autre technicien ;
- chaque attribution ou réattribution doit être enregistrée dans l’historique ;
- le technicien attribué devient responsable du traitement de l’incident.

### Règles de sécurité 

### Informations affichées

### Critères d'acceptation

### Cas d’erreur

### Dépendances

### Tâches techniques


## US-08 — Modifier la priorité

### User story

En tant que technicien ou administrateur, 
je veux modifier la priorité d’un incident 
afin de refléter sa gravité réelle.

### Priorité 

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- l’utilisateur possède le rôle TECHNICIAN ou ADMIN ;
- l’incident existe ;
- l’incident n’a pas le statut CLOSED.

### Règles métier

- un utilisateur classique ne peut pas modifier la priorité d’un incident ;
- un technicien ne peut modifier que la priorité des incidents qui lui sont attribués ;
- un administrateur peut modifier la priorité de tous les incidents ;
- la priorité doit être LOW, MEDIUM, HIGH ou CRITICAL ;
- chaque modification doit enregistrer l’ancienne et la nouvelle priorité dans l’historique ;
- la nouvelle priorité remplace immédiatement l’ancienne ;
- si une liste est triée par priorité, l’incident est repositionné après la modification.ù

### Règles de sécurité 

### Informations affichées

### Critères d'acceptation

### Cas d’erreur

### Dépendances

### Tâches techniques


## US-09 — Modifier le statut

### User story

En tant que technicien, 
je veux modifier le statut d’un incident 
afin d’indiquer l’avancement de son traitement.

### Priorité 

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- il possède le rôle TECHNICIAN ou ADMIN ;
- l’incident existe ;
- l’incident n’a pas le statut CLOSED.

### Règles métier

- un utilisateur classique ne peut pas modifier le statut d’un incident ;
- un technicien ne peut modifier que les incidents qui lui sont attribués ;
- un administrateur peut modifier le statut de tous les incidents ;
- les transitions autorisées sont OPEN → IN_PROGRESS → RESOLVED → CLOSED ;
- le passage à RESOLVED nécessite une description de la solution appliquée ;
- chaque changement enregistre l’ancien statut, le nouveau statut, l’auteur et la date dans l’historique ;
- une date de résolution est enregistrée lors du passage à RESOLVED ;
- une date de clôture est enregistrée lors du passage à CLOSED.

### Règles de sécurité 

### Informations affichées

### Critères d'acceptation

- une transition non autorisée est refusée ;
- un commentaire obligatoire ne peut pas être vide ;
- les utilisateurs autorisés peuvent consulter la justification du changement ;
- si la liste est filtrée ou triée par statut, l’incident est repositionné après la modification.

## US-10 — Résoudre un incident

### User story

En tant que technicien, 
je veux indiquer la solution appliquée et marquer un incident comme résolu 
afin de signaler que le problème a été corrigé.

### Priorité 

Must

### Préconditions

- l’utilisateur est authentifié ;
- son compte est actif ;
- il possède le rôle TECHNICIAN ou ADMIN ;
- l’incident existe ;
- l’incident possède le statut IN_PROGRESS ;
- pour un technicien, l’incident doit lui être attribué.

### Règles métier

- un utilisateur classique ne peut pas résoudre un incident ;
- un technicien ne peut résoudre que les incidents qui lui sont attribués ;
- un administrateur peut résoudre tous les incidents ;
- le passage à RESOLVED nécessite une description non vide de la solution appliquée ;
- le statut devient RESOLVED après validation ;
- une date de résolution est enregistrée automatiquement ;
- la résolution est ajoutée à l’historique de l’incident ;
- un incident résolu reste consultable et n’est pas encore considéré comme clôturé.

### Règles de sécurité 

### Informations affichées

### Critères d'acceptation

- un technicien autorisé peut résoudre un incident qui lui est attribué ;
- la résolution est refusée si aucune solution n’est renseignée ;
- après validation, le statut devient RESOLVED ;
- la solution et la date de résolution sont enregistrées ;
- l’auteur de l’incident peut consulter la solution appliquée ;
- un technicien non attribué ne peut pas résoudre l’incident ;
- la résolution apparaît dans l’historique.


### Cas d’erreur

### Dépendances

### Tâches techniques



## US-11 — Clôturer un incident

### User story

En tant qu’administrateur ou utilisateur autorisé, 
je veux clôturer un incident résolu 
afin de terminer officiellement son cycle de traitement.

### Priorité 

Must

### Préconditions

### Règles métier


### Règles de sécurité 

### Informations affichées

### Critères d'acceptation

### Cas d’erreur

### Dépendances

### Tâches techniques


## US-12 — Consulter l’historique

### User story

En tant qu’utilisateur autorisé, 
je veux consulter l’historique d’un incident 
afin de connaître les actions et les modifications réalisées.

### Priorité :

Must


### Préconditions

### Règles métier


### Règles de sécurité 

### Informations affichées

### Critères d'acceptation

### Cas d’erreur

### Dépendances

### Tâches techniques



## US-13 — Filtrer les incidents

### User story

En tant que technicien ou administrateur, je veux filtrer les incidents par statut, priorité et catégorie afin de retrouver rapidement les incidents pertinents.

### Priorité :

Must


### Préconditions

### Règles métier


### Règles de sécurité 

### Informations affichées

### Critères d'acceptation

### Cas d’erreur

### Dépendances

### Tâches techniques



## US-14 — Consulter le tableau de bord

### User story

En tant que technicien ou administrateur, je veux consulter une synthèse des incidents afin d’identifier rapidement les incidents ouverts, critiques ou en retard.

### Priorité :

Must


### Préconditions

### Règles métier


### Règles de sécurité 

### Informations affichées

### Critères d'acceptation

### Cas d’erreur

### Dépendances

### Tâches techniques



## US-15 — Gérer les comptes

### User story

En tant qu’administrateur, je veux créer, désactiver et modifier les comptes utilisateurs afin de contrôler l’accès à la plateforme.

### Priorité :

Must


### Préconditions

### Règles métier


### Règles de sécurité 

### Informations affichées

### Critères d'acceptation

### Cas d’erreur

### Dépendances

### Tâches techniques



## US-16 — Consulter les journaux d’audit

### User story

En tant qu’administrateur, je veux consulter les événements sensibles de l’application afin de détecter les actions anormales et de garantir la traçabilité.