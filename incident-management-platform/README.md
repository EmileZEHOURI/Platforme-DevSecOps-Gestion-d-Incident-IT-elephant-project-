# Plateforme DevSecOps de gestion d’incidents IT

> Projet personnel en cours de développement — MVP prévu sur 4 semaines.

## Présentation

Cette application a pour objectif de centraliser la déclaration, l’attribution, le suivi et la résolution d’incidents IT ou de sécurité.

Le projet est conçu comme une démonstration complète de compétences en :

- développement full-stack ;
- sécurité applicative ;
- gestion des rôles et des autorisations ;
- conteneurisation ;
- tests automatisés ;
- intégration et déploiement continus ;
- journalisation et traçabilité ;
- documentation technique.

L’objectif n’est pas uniquement de construire un gestionnaire de tickets, mais de mettre en place une application pensée selon une démarche **DevSecOps**, où la sécurité, les tests et l’automatisation sont intégrés dès le début du développement.

---

## Objectifs du MVP

Le MVP doit permettre de couvrir le cycle de vie principal d’un incident :

```text
Création
   ↓
Qualification
   ↓
Attribution
   ↓
Traitement
   ↓
Résolution
   ↓
Clôture
```

À la fin de la première version, un utilisateur devra pouvoir déclarer un incident, un technicien devra pouvoir le prendre en charge et un administrateur devra pouvoir superviser l’ensemble du processus.

---

## Fonctionnalités prévues

### Authentification et comptes

- connexion et déconnexion ;
- gestion sécurisée des mots de passe ;
- contrôle d’accès fondé sur les rôles ;
- désactivation d’un compte par un administrateur ;
- protection des routes sensibles.

### Gestion des incidents

- création d’un incident ;
- consultation de la liste des incidents ;
- consultation du détail d’un incident ;
- modification du statut ;
- modification de la priorité ;
- attribution à un technicien ;
- ajout de commentaires ;
- historique des changements ;
- recherche et filtres simples.

### Tableau de bord

- nombre total d’incidents ;
- répartition par statut ;
- répartition par priorité ;
- incidents récemment créés ;
- incidents assignés à un technicien.

### Traçabilité et sécurité

- journalisation des actions sensibles ;
- historique métier des incidents ;
- validation des données entrantes ;
- gestion centralisée des erreurs ;
- gestion des secrets par variables d’environnement ;
- tests des autorisations ;
- analyse statique du code ;
- scan des dépendances ;
- scan des images Docker.

### DevOps

- exécution locale avec Docker Compose ;
- pipeline CI avec GitHub Actions ;
- linting du front-end et du back-end ;
- tests automatisés ;
- build des applications ;
- construction d’images Docker ;
- déploiement cloud dans une étape ultérieure.

---

## Rôles utilisateurs

### Utilisateur

- créer un incident ;
- consulter ses propres incidents ;
- suivre leur progression ;
- ajouter un commentaire sur un incident accessible.

### Technicien

- consulter les incidents qui lui sont accessibles ;
- prendre en charge un incident ;
- modifier son statut ;
- modifier sa priorité ;
- ajouter des commentaires techniques ;
- résoudre un incident.

### Administrateur

- consulter tous les incidents ;
- attribuer ou réattribuer un incident ;
- gérer les utilisateurs et leurs rôles ;
- accéder aux journaux d’audit ;
- superviser les indicateurs globaux.

Les autorisations seront vérifiées côté back-end. Le masquage d’un bouton dans l’interface ne constituera jamais, à lui seul, une mesure de sécurité.

---

## Stack technique

### Front-end

- Next.js
- React
- TypeScript
- Tailwind CSS
- Zod
- Vitest ou Jest

### Back-end

- Python
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- Pytest
- Ruff
- Bandit

### Base de données

- PostgreSQL

### DevOps et sécurité

- Docker
- Docker Compose
- GitHub Actions
- pip-audit
- npm audit
- Trivy
- gestion des secrets par variables d’environnement

### Déploiement envisagé

- Google Cloud Run ou AWS

---

## Architecture envisagée

```text
incident-management-platform/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── services/
│   ├── types/
│   └── tests/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── security/
│   ├── migrations/
│   └── tests/
│
├── infrastructure/
│   ├── docker/
│   └── scripts/
│
├── docs/
│   ├── architecture/
│   ├── security/
│   └── api/
│
├── .github/
│   └── workflows/
│
├── docker-compose.yml
├── .env.example
└── README.md
```

L’application sera développée dans un monorepo afin de centraliser le code, les workflows CI/CD, la documentation et le suivi des évolutions.

---

## Modèle de données initial

### Utilisateurs

```text
users
- id
- email
- password_hash
- full_name
- role
- is_active
- created_at
- updated_at
```

### Incidents

```text
incidents
- id
- title
- description
- category
- status
- priority
- created_by
- assigned_to
- created_at
- updated_at
- resolved_at
- closed_at
```

### Commentaires

```text
incident_comments
- id
- incident_id
- author_id
- content
- created_at
```

### Historique métier

```text
incident_history
- id
- incident_id
- actor_id
- action
- old_value
- new_value
- created_at
```

### Journal d’audit

```text
audit_logs
- id
- user_id
- event_type
- resource_type
- resource_id
- ip_address
- user_agent
- created_at
```

L’historique métier retracera l’évolution d’un incident. Le journal d’audit enregistrera les événements sensibles liés à la sécurité et à l’utilisation de l’application.

---

## Statuts et priorités

### Statuts

```text
OPEN
IN_PROGRESS
RESOLVED
CLOSED
```

### Priorités

```text
LOW
MEDIUM
HIGH
CRITICAL
```

### Catégories initiales

```text
SUPPORT
SECURITY
ACCESS
ANOMALY
DATA
```

---

## Sécurité

Le projet suivra progressivement les bonnes pratiques suivantes :

- hachage sécurisé des mots de passe avec Argon2 ou bcrypt ;
- contrôle d’accès par rôles ;
- validation des entrées avec Pydantic et Zod ;
- utilisation de requêtes paramétrées via SQLAlchemy ;
- gestion des secrets hors du dépôt Git ;
- limitation des données sensibles dans les logs ;
- protection contre les accès horizontaux non autorisés ;
- tests automatisés des permissions ;
- analyse des dépendances ;
- revue des risques inspirée de l’OWASP Top 10.

### Risques à traiter

- élévation de privilèges ;
- accès à l’incident d’un autre utilisateur ;
- modification non autorisée d’un statut ;
- injection SQL ;
- brute force sur l’authentification ;
- fuite de jetons ;
- exposition de données sensibles dans les logs ;
- dépendances vulnérables.

Une matrice de risques et un document de sécurité seront ajoutés dans `docs/security/`.

---

## Pipeline CI envisagé

```text
Pull Request
   ↓
Lint du front-end
   ↓
Lint du back-end
   ↓
Tests du front-end
   ↓
Tests du back-end
   ↓
Audit des dépendances
   ↓
Analyse de sécurité
   ↓
Build des applications
   ↓
Build des images Docker
   ↓
Déploiement
```

La première version du pipeline sera volontairement simple, puis enrichie au fur et à mesure du projet.

---

## Installation locale

> Cette section sera complétée au fur et à mesure de l’implémentation.

### Prérequis

- Git
- Docker
- Docker Compose
- Node.js
- Python 3.12 ou version compatible

### Cloner le dépôt

```bash
git clone <URL_DU_DEPOT>
cd incident-management-platform
```

### Variables d’environnement

Copier le fichier d’exemple :

```bash
cp .env.example .env
```

Exemple de variables prévues :

```env
POSTGRES_DB=incident_management
POSTGRES_USER=incident_user
POSTGRES_PASSWORD=change_me
DATABASE_URL=postgresql+psycopg://incident_user:change_me@db:5432/incident_management

JWT_SECRET_KEY=change_me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

NEXT_PUBLIC_API_URL=http://localhost:8000
```

Aucune valeur sensible ne devra être publiée dans le dépôt.

### Lancer l’application

```bash
docker compose up --build
```

Services prévus :

- front-end : `http://localhost:3000`
- API : `http://localhost:8000`
- documentation OpenAPI : `http://localhost:8000/docs`
- PostgreSQL : port `5432`

---

## Tests

### Back-end

```bash
cd backend
pytest
```

### Linting back-end

```bash
cd backend
ruff check .
```

### Front-end

```bash
cd frontend
npm test
```

### Linting front-end

```bash
cd frontend
npm run lint
```

Les commandes seront ajustées lorsque les outils seront définitivement configurés.

---

## Cas de test prioritaires

- un utilisateur peut créer un incident ;
- un utilisateur peut consulter ses propres incidents ;
- un utilisateur ne peut pas consulter l’incident d’un autre utilisateur ;
- un utilisateur ne peut pas devenir administrateur ;
- un technicien peut prendre en charge un incident ;
- un technicien peut modifier uniquement les champs autorisés ;
- un administrateur peut consulter tous les incidents ;
- chaque modification importante crée une entrée d’historique ;
- chaque action sensible crée une entrée dans le journal d’audit.

---

## Feuille de route sur 4 semaines

### Semaine 1 — Fondations

- initialisation du monorepo ;
- configuration de Next.js et FastAPI ;
- configuration de PostgreSQL ;
- création de Docker Compose ;
- conception du modèle de données ;
- configuration de SQLAlchemy et Alembic ;
- création des utilisateurs et des rôles ;
- authentification ;
- première version de la CI.

### Semaine 2 — Gestion des incidents

- création d’un incident ;
- liste des incidents ;
- consultation détaillée ;
- modification du statut ;
- modification de la priorité ;
- attribution à un technicien ;
- commentaires ;
- contrôles d’autorisation côté API.

### Semaine 3 — DevSecOps

- historique des changements ;
- journal d’audit ;
- filtres ;
- tableau de bord minimal ;
- tests des permissions ;
- linting ;
- analyse statique ;
- audits de dépendances ;
- scan Docker.

### Semaine 4 — Livraison

- déploiement ;
- correction des principaux bugs ;
- documentation d’installation ;
- schéma d’architecture ;
- captures d’écran ;
- matrice de risques ;
- comptes de démonstration ;
- préparation de la présentation CV et LinkedIn.

---

## Périmètre reporté après le MVP

Les fonctionnalités suivantes ne sont pas prioritaires pour la première version :

- export PDF ;
- notifications en temps réel ;
- pièces jointes avancées ;
- graphiques complexes ;
- authentification multifacteur ;
- intégration à un SIEM ;
- architecture microservices ;
- Kubernetes ;
- Terraform ;
- intelligence artificielle de classification des incidents ;
- tests end-to-end exhaustifs.

Elles pourront être intégrées dans une version ultérieure.

---

## Critères de réussite du MVP

Le MVP sera considéré comme présentable lorsque le scénario suivant sera démontrable :

1. un utilisateur se connecte ;
2. il crée un incident ;
3. un administrateur consulte cet incident ;
4. il l’attribue à un technicien ;
5. le technicien modifie sa priorité ;
6. il ajoute un commentaire ;
7. il résout l’incident ;
8. les changements apparaissent dans l’historique ;
9. les actions sensibles apparaissent dans les logs ;
10. la CI exécute les tests et les contrôles de qualité ;
11. l’application est exécutable avec Docker Compose ;
12. le dépôt contient une documentation claire.

---

## État du projet

```text
Statut : cadrage initial
Version : 0.1.0
Durée prévue pour le MVP : 4 semaines
Charge de travail prévue : 25 à 30 heures par semaine
```

### Progression

- [x] définition générale du projet ;
- [x] définition du périmètre MVP ;
- [x] choix initial de la stack ;
- [x] première version du README ;
- [ ] création du dépôt ;
- [ ] initialisation du front-end ;
- [ ] initialisation du back-end ;
- [ ] configuration de PostgreSQL ;
- [ ] configuration de Docker Compose ;
- [ ] implémentation de l’authentification ;
- [ ] implémentation de la gestion des incidents ;
- [ ] tests automatisés ;
- [ ] pipeline CI ;
- [ ] déploiement.

---

## Auteur

**Emile Zehouri**

Projet réalisé dans le cadre du développement de compétences en développement full-stack, cybersécurité, Cloud et DevOps.

---

## Licence

La licence du projet sera définie avant sa publication publique.