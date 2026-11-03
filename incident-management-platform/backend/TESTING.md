# Tests du backend

Les tests API utilisent exclusivement `TEST_DATABASE_URL`. Ils ne réutilisent jamais la base configurée dans `.env`.

## Préparer PostgreSQL

Avec un compte administrateur PostgreSQL, créer une base dédiée terminant par `_test`, par exemple `incident_management_test`, dont le propriétaire est le rôle utilisé pour les tests. Ce rôle doit pouvoir créer un schéma dans cette base. Ne pas utiliser une base contenant des données métier.

Dans PowerShell, depuis `backend`, définir la connexion vers cette base, puis lancer les tests :

```powershell
$env:TEST_DATABASE_URL = 'postgresql+psycopg://ROLE:MOT_DE_PASSE@127.0.0.1:5432/incident_management_test'
python -m pytest
python -m ruff check app tests
```

Remplacer les paramètres par ceux de la base de test ; ne pas versionner les identifiants. Pour un mot de passe contenant des caractères réservés, les encoder dans l’URL.

Sans `TEST_DATABASE_URL`, les tests nécessitant PostgreSQL sont explicitement ignorés ; les tests unitaires continuent à fonctionner. Un résultat comportant des tests ignorés ne valide donc pas l’intégration complète. Une URL fournie mais invalide ou inaccessible entraîne une erreur.

## Isolation

- Refus des bases qui ne se terminent pas par `_test`, ou qui ont le même nom que la base applicative.
- Création d’un schéma temporaire unique `pytest_<uuid>` par session de tests, contenant les tables et énumérations PostgreSQL.
- Remplacement de la dépendance FastAPI `get_db` pour tous les tests ; aucune requête de test ne retombe sur la session applicative.
- Transaction externe par test et savepoints SQLAlchemy : les `commit()` des routes ne persistent pas les données après le test.
- Suppression du seul schéma temporaire créé par la session en fin d’exécution. Aucune suppression de compte ou d’incident préexistant.

Ces tests vérifient les modèles SQLAlchemy. La validation des migrations Alembic sur une base vierge reste une vérification distincte.

## Couverture US-02

Création et valeurs par défaut, auteur issu de la session, référence distincte, historique et audit, refus des comptes désactivés et requêtes anonymes, champs obligatoires, valeurs invalides, limites de longueur, nettoyage des espaces et rejet des champs gérés par le serveur. Les tests injectent aussi des échecs après écriture de l’historique ou de l’audit et vérifient l’annulation complète avant une nouvelle tentative réussie.
