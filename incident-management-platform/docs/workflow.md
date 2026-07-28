# Workflow de gestion des incidents

## Statuts

Création
   ↓
OPEN
   ↓ Attribution à un technicien
OPEN
   ↓ Début du traitement
IN_PROGRESS
   ↓ Solution renseignée
RESOLVED
   ↓ Validation de la résolution
CLOSED

## Transitions autorisées

- à la création, le statut initial est `OPEN` ;
- `OPEN → IN_PROGRESS` ;
- `IN_PROGRESS → RESOLVED` ;
- `RESOLVED → CLOSED`.

L’attribution à un technicien ne change pas le statut : l’incident reste `OPEN`

## Conditions de transition

- création → `OPEN` : l’incident est créé avec des données valides ;
- attribution : l’incident existe, n’est pas clôturé et un technicien actif est sélectionné ;
- `OPEN → IN_PROGRESS` : l’incident est attribué et le traitement commence ;
- `IN_PROGRESS → RESOLVED` : une solution non vide est renseignée ;
- `RESOLVED → CLOSED` : la résolution est validée par l’auteur ou un administrateur.

## Actions par rôle

### Utilisateur Classique

Créer un incident
→ consulter son avancement
→ ajouter des commentaires
→ consulter la solution
→ clôturer l’incident résolu

### Technician

Consulter ses incidents attribués
→ commencer le traitement
→ ajouter des commentaires
→ modifier la priorité
→ renseigner une solution
→ résoudre l’incident

### Administrateur 

Consulter tous les incidents
→ qualifier l’incident
→ modifier la priorité
→ attribuer ou réattribuer
→ intervenir sur le statut
→ résoudre si nécessaire
→ clôturer

## Règles générales

- un incident doit être attribué avant de passer à IN_PROGRESS ;
- un technicien ne traite que les incidents qui lui sont attribués ;
- seul un administrateur attribue ou réattribue un incident ;
- une solution est obligatoire avant le passage à RESOLVED ;
- seul un incident RESOLVED peut être clôturé ;
- un incident CLOSED ne peut plus être modifié ;
- chaque attribution, changement de priorité, changement de statut, résolution et clôture est enregistré dans - l’historique ;
- les droits sont toujours vérifiés côté back-end.

## Scénario complet

1. Emile crée un incident
   Statut : OPEN
   Technicien : aucun

2. L’administrateur définit la priorité HIGH
   Statut : OPEN

3. L’administrateur attribue Sarah
   Statut : OPEN
   Technicien : Sarah

4. Sarah commence le traitement
   Statut : IN_PROGRESS

5. Sarah ajoute des commentaires et effectue ses vérifications

6. Sarah renseigne la solution
   Statut : RESOLVED

7. Emile confirme que le problème est corrigé
   Statut : CLOSED