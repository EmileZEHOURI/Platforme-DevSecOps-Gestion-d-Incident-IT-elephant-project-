# Sauvegardes PostgreSQL du staging\r
\r
## Fonctionnement et prérequis\r
\r
scripts/backup_staging.ps1 est compatible Windows PowerShell 5.1.\r
Les chemins absolus viennent de PSScriptRoot, sans dépendre du dossier courant.\r
Projet incident-staging, service db, compose.staging.yaml et .env.staging.\r
Les labels du conteneur, POSTGRES_USER=incident_staging et\r
POSTGRES_DB=incident_management_staging sont vérifiés avant le dump.\r
Un changement volontaire de ces noms nécessite d'adapter les garde-fous.\r
\r
Docker Desktop doit être démarré avec le compte disposant de l'accès au moteur,\r
PostgreSQL staging doit être sain et l'espace disque suffisant.\r
Le script trouve docker.exe dans PATH ou dans le dossier standard Docker Desktop.\r
\r
Étapes :\r
1. Journal horodaté et verrou exclusif empêchant les lancements concurrents.\r
2. pg_dump -Fc dans un fichier temporaire unique du conteneur.\r
3. Vérification pg_restore --list.\r
4. SHA256 distant, copie Docker vers .partial et contrôle SHA256 local.\r
5. Suppression du fichier temporaire distant.\r
6. Renommage sans écrasement de la copie complète, puis journal SUCCESS.\r
7. Sortie 0 ; tout échec essentiel renvoie un code non nul et FAILURE.\r
\r
Les codes Docker sont explicitement contrôlés, y compris sous PowerShell 5.1.\r
Leurs sorties sont capturées mais les erreurs brutes ne sont pas inscrites dans\r
les logs pour éviter une éventuelle exposition de valeurs de configuration :\r
l'étape et le code natif sont indiqués.\r
Seuls les fichiers temporaires de l'exécution sont nettoyés.\r
\r
Archives : incident-management-platform/backups/\r
Logs : incident-management-platform/backups/logs/\r
Noms : staging_DATE_HEURE_GUID.dump, le GUID évite les collisions dans la même seconde.\r
Le fichier .backup-staging.lock peut rester : le handle exclusif constitue le verrou.\r
backups/ est entièrement ignoré par Git. Aucune archive antérieure n'est supprimée.\r
\r
## Exécution manuelle\r
\r
Depuis n'importe quel dossier :\r
\r
~~~powershell\r
powershell.exe -NoProfile -NonInteractive -File "C:\Users\Emile\Desktop\Bureau\elephant-project\incident-management-platform\scripts\backup_staging.ps1"\r
$LASTEXITCODE\r
~~~\r
\r
DestinationDirectory, optionnel, permet de choisir un sous-dossier de backups/\r
et de simuler une destination indisponible sans toucher à la base.\r
\r
## Planificateur Windows\r
\r
Tâche existante : Incident Staging - Backup PostgreSQL, sans doublon.\r
Compte Emile, session Interactive, niveau Limited, sans mot de passe enregistré.\r
Elle utilise déjà le chemin absolu du script et s'exécute chaque jour à 02 h 00.\r
\r
État réellement observé :\r
- Ready.\r
- Dernière exécution : 27 novembre 2026 à 20:16:35, résultat 0.\r
- Prochaine exécution : 28 novembre 2026 à 02:00:00, Europe/Paris.\r
- StartWhenAvailable=False : aucun rattrapage automatique actuellement.\r
- MultipleInstances=IgnoreNew, lancement à la demande autorisé.\r
- Ne démarre pas sur batterie, arrêt si passage sur batterie.\r
- Limite existante : 72 heures.\r
\r
La mise à jour Set-ScheduledTask a été refusée par Windows avec HRESULT\r
0x80070005, Accès refusé. Ce n'est pas un refus de revue automatique.\r
La tâche existante a néanmoins pu être déclenchée et a réussi.\r
\r
scripts/register_backup_staging_task.ps1 prépare une mise à jour idempotente :\r
chemin absolu de PowerShell 5.1, déclenchement quotidien à 02 h,\r
StartWhenAvailable=True, IgnoreNew, limite 30 minutes, compte Interactive Limited.\r
Ces nouveaux paramètres n'ont PAS été appliqués faute de droits de modification.\r
\r
Pour activer le rattrapage, utiliser le compte propriétaire autorisé à modifier\r
la tâche ; si nécessaire, ouvrir PowerShell élevé sous le même compte Emile :\r
\r
~~~powershell\r
& "C:\Users\Emile\Desktop\Bureau\elephant-project\incident-management-platform\scripts\register_backup_staging_task.ps1"\r
~~~\r
\r
Cette élévation éventuelle sert seulement à modifier la tâche protégée.\r
Son exécution quotidienne restera Limited. Ne pas contourner la politique\r
d'exécution Windows ni une restriction de sécurité.\r
\r
Pour exécuter et contrôler la tâche :\r
\r
~~~powershell\r
Start-ScheduledTask -TaskName "Incident Staging - Backup PostgreSQL"\r
Get-ScheduledTaskInfo -TaskName "Incident Staging - Backup PostgreSQL"\r
Get-ScheduledTask -TaskName "Incident Staging - Backup PostgreSQL"\r
~~~\r
\r
## Résultats des tests du 27 novembre 2026\r
\r
A. Exécution manuelle PowerShell 5.1 : sortie 0, pg_restore --list et SHA256 OK.\r
B. Deuxième exécution depuis C:\Windows\Temp : sortie 0, autre nom, aucun écrasement.\r
C. Déclenchement réel Start-ScheduledTask : résultat final 0, troisième archive.\r
D. Destination de test occupée par un fichier : dump et validation réussis,\r
copie Docker refusée avec code 1, sortie script 1 et log FAILURE.\r
Le fichier distant a été nettoyé ; aucune archive finale ou .partial résiduelle.\r
Le fichier de simulation a été supprimé.\r
Un premier essai avait aussi échoué proprement au contrôle des labels à cause des\r
guillemets PowerShell 5.1 ; il utilise désormais JSON sans guillemets imbriqués.\r
E. Comptages staging avant/après : users=3, incidents=1, audit_logs=9, revoked_tokens=3.\r
Ces nombres sont des observations de cette mission, pas des constantes.\r
Les deux frontends localhost:3020 et localhost:3000 répondent 200.\r
Tous les identifiants de conteneurs dev/staging sont inchangés, services healthy.\r
Hashes des anciennes archives et de .env.docker/.env.staging inchangés.\r
Aucun conteneur ou volume supprimé. L'ancien /tmp/staging_backup.dump préexistant\r
est conservé. git diff --check et git check-ignore sur une archive : réussis.\r
\r
Trois nouvelles archives de 23 918 octets chacune dans :\r
C:\Users\Emile\Desktop\Bureau\elephant-project\incident-management-platform\backups\\r
\r
- staging_2026-11-27_20-15-45_8dace911cd32413dae9009b489fb69c8.dump\r
- staging_2026-11-27_20-16-17_015b580594e543ad9b45a4cec0c342f1.dump\r
- staging_2026-11-27_20-16-36_2d82753a92174387b283739957f8d612.dump\r
\r
Les journaux portent les mêmes horodatages/identifiants dans backups/logs/.\r
Le test d'échec commence à 20:16:40.\r
Aucune restauration complète n'a été exécutée pendant cette mission.\r
\r
## Restauration dans une base séparée\r
\r
La procédure manuelle déjà rapportée consiste à restaurer dans une base distincte\r
et comparer les tables. Aucun script de restauration existant n'a été trouvé.\r
Ne jamais faire un exercice de restauration par-dessus staging ou développement.\r
\r
Exemple à exécuter manuellement dans un NOUVEAU conteneur sans port exposé :\r
\r
~~~powershell\r
$archive = "C:\chemin\vers\une-sauvegarde.dump"\r
$restoreContainer = "incident-restore-check-" + [guid]::NewGuid().ToString("N")\r
$bytes = New-Object byte[] 32\r
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()\r
$rng.GetBytes($bytes)\r
$rng.Dispose()\r
$env:POSTGRES_PASSWORD = [Convert]::ToBase64String($bytes)\r
docker run -d --name $restoreContainer --network none -e POSTGRES_PASSWORD -e POSTGRES_USER=restore_user -e POSTGRES_DB=restore_check postgres:17-alpine\r
Remove-Item Env:POSTGRES_PASSWORD\r
# Attendre une réponse positive de pg_isready.\r
docker exec $restoreContainer pg_isready -U restore_user -d restore_check\r
docker cp $archive ($restoreContainer + ":/tmp/restore.dump")\r
docker exec $restoreContainer pg_restore --list /tmp/restore.dump\r
docker exec $restoreContainer pg_restore --exit-on-error --no-owner --no-acl -U restore_user -d restore_check /tmp/restore.dump\r
docker exec $restoreContainer psql -U restore_user -d restore_check -c "SELECT count(*) FROM users; SELECT count(*) FROM incidents; SELECT count(*) FROM audit_logs; SELECT count(*) FROM revoked_tokens;"\r
~~~\r
\r
Contrôler chaque code de retour et arrêter en cas d'échec. Comparer à des données\r
cohérentes avec la date de sauvegarde, pas à des valeurs historiques fixes.\r
Nettoyer explicitement le conteneur et son stockage de test après vérification\r
de leur identité. Cette procédure documentée n'a pas été exécutée ici.\r
\r
Une restauration ancienne peut perdre des révocations JWT récentes. Pour une\r
véritable reprise, appliquer la rotation de clé décrite dans jwt-revocation.md\r
avant réouverture. Aucune clé n'est modifiée automatiquement par ces scripts.\r
\r
## Limites et conservation future\r
\r
PC allumé, session Emile ouverte, Docker Desktop disponible et conditions\r
d'alimentation satisfaites. Une session verrouillée reste ouverte ; une session\r
déconnectée ne permet pas cette tâche Interactive.\r
Le rattrapage reste à activer avec les droits Windows nécessaires.\r
Stockage local uniquement, sans alerte externe ni protection contre la perte du PC.\r
Restreindre l'accès aux archives, qui contiennent des données sensibles.\r
\r
Recommandations NON activées, à valider avant toute suppression :\r
- Conservation quotidienne 7 jours.\r
- Sauvegarde hebdomadaire, durée à définir.\r
- Rotation des logs.\r
- Copie chiffrée vers un stockage distinct.\r
- Tests périodiques de restauration et alerte en cas d'échec.\r
\r
Aucune rétention destructive, sauvegarde cloud ou publication GitHub activée.\r
\r
\r
## Politique de rétention préparée — 27 novembre 2026\r
\r
La sauvegarde crée un nouveau point de restauration ; la rétention choisit lesquels\r
conserver. La suppression automatique reste désactivée et la tâche Windows est\r
inchangée. Le script scripts/retention_staging.ps1 fonctionne sous PowerShell 5.1.\r
\r
### Sélection exacte\r
\r
Seuls les fichiers directement dans backups/ sont examinés, sans récursion.\r
Le nom reconnu est staging_YYYY-MM-DD_HH-mm-ss_GUID.dump avec GUID de 32 caractères\r
hexadécimaux minuscules. Date impossible ou future, ancien nom sans GUID, export\r
manuel, archive inconnue, fichier .partial : conservation et signalement.\r
Les liens/jonctions ne sont pas suivis. Le dossier backups/ et ses parents,\r
le dossier logs et le verrou ne peuvent pas être des points de réanalyse.\r
\r
Une archive fiable doit être non vide, posséder son journal backup_DATE_GUID.log,\r
avec cible staging vérifiée, validation pg_restore --list, confirmation de copie,\r
une seule entrée SUCCESS correspondant au chemin et à la taille, et une fin de\r
journal exit_code=0 sans FAILURE. Son SHA256 est recalculé et comparé à ce journal.\r
Le journal lui-même ne doit pas être un lien. Une archive sans cette preuve reste\r
protégée et ne peut pas justifier une suppression.\r
\r
Sélection parmi les archives fiables :\r
- dernière sauvegarde de chacune des 7 dernières journées représentées ;\r
- dernière sauvegarde de chacune des 4 dernières semaines représentées ;\r
- union de ces sélections, sans doublon, avec protection explicite de la dernière archive fiable.\r
\r
Les semaines vont du lundi 00 h au dimanche 23 h 59 en heure locale, définies par\r
la date du lundi, y compris à cheval sur deux années. La semaine courante compte\r
si elle contient un point. Les journées/semaines absentes ne sont pas inventées :\r
il s'agit de points disponibles, pas d'une expiration au bout de 7 jours.\r
\r
Pour plusieurs archives le même jour, la plus récente gagne ; en cas d'égalité\r
à la seconde, le nom (GUID) le plus grand dans le tri descendant départage.\r
Les autres archives fiables de cette journée ne sont supprimables que si les\r
autres garde-fous sont satisfaits.\r
\r
Seuil conservateur : il faut au moins 7 journées ET 4 semaines fiables avant\r
toute suppression. Sinon, toutes les archives sont conservées.\r
Les fichiers ambigus ne sont jamais supprimés par ce mécanisme.\r
\r
### Simulation et application future\r
\r
Depuis la racine de l'application :\r
\r
~~~powershell\r
powershell.exe -NoProfile -NonInteractive -File .\scripts\retention_staging.ps1\r
~~~\r
\r
La simulation écrit un rapport texte et un plan JSON dans backups/logs/ :\r
retention_DATE_GUID.log et retention_DATE_GUID.json.\r
KEEP = point conservé ou historique insuffisant ;\r
PROTECT = fichier ambigu/inconnu/lien conservé ;\r
DELETE = suppression envisagée, jamais réalisée en simulation.\r
Le rapport inclut les comptes quotidiens/hebdomadaires, fichiers protégés,\r
tailles avant/après et opérations réellement effectuées.\r
\r
Après une validation distincte, l'application réelle pourra être lancée :\r
\r
~~~powershell\r
powershell.exe -NoProfile -NonInteractive -File .\scripts\retention_staging.ps1 -Apply\r
~~~\r
\r
Pour exiger également que le dossier soit identique à une simulation antérieure :\r
\r
~~~powershell\r
powershell.exe -NoProfile -NonInteractive -File .\scripts\retention_staging.ps1 -Apply -PlanPath "C:\chemin\du\projet\backups\logs\retention_DATE_GUID.json"\r
~~~\r
\r
-Apply sans PlanPath prépare et contrôle un nouveau plan dans la même exécution.\r
Avec PlanPath, le plan doit se trouver dans backups/logs/ et sa photographie\r
doit être identique au contenu actuel. Les décisions du JSON ne sont jamais\r
exécutées aveuglément : elles sont recalculées.\r
\r
### Protections et concurrence\r
\r
Le même verrou exclusif .backup-staging.lock que la sauvegarde empêche leur\r
exécution simultanée. Les chemins absolus sont contrôlés avant chaque suppression,\r
uniquement un fichier enfant direct, sans suppression récursive.\r
Les contenus SHA256, tailles, dates, attributs, noms et preuves sont contrôlés\r
avant l'application puis avant chaque suppression, avec adaptation aux seules\r
suppressions déjà effectuées. Tout changement détecté arrête l'application.\r
Si une erreur survient après plusieurs suppressions réussies, celles-ci ne peuvent\r
pas être annulées ; le journal les identifie et les fichiers restants sont préservés.\r
\r
Le verrou coordonne les scripts de sauvegarde/rétention. Ce n'est pas un mécanisme\r
de protection contre un administrateur ou un autre programme ignorant ce verrou.\r
Ne pas modifier le dossier pendant l'application ; les contrôles ne constituent\r
pas une transaction atomique du système de fichiers.\r
\r
Les journaux et SHA256 prouvent la cohérence avec la vérification enregistrée,\r
pas une restauration complète ni une authenticité cryptographique des journaux.\r
Un acteur pouvant altérer archives ET preuves peut falsifier cette confiance.\r
Conserver des permissions Windows restrictives et réaliser des restaurations périodiques.\r
Ne pas supprimer les journaux backup_*.log associés aux archives conservées :\r
leur absence rendrait celles-ci protégées et inutilisables pour la sélection.\r
\r
### Intégration non destructive préparée\r
\r
backup_staging.ps1 conserve exactement son comportement par défaut.\r
L'option facultative -PreviewRetention appelle seulement une simulation après\r
publication réussie de l'archive et libération du verrou. L'appel est effectué\r
dans un processus PowerShell 5.1 distinct ; aucun -Apply n'est transmis.\r
\r
~~~powershell\r
powershell.exe -NoProfile -NonInteractive -File .\scripts\backup_staging.ps1 -PreviewRetention\r
~~~\r
\r
Cette option n'a pas été ajoutée à la tâche quotidienne. Aucune suppression\r
automatique n'est active. Un échec de la simulation optionnelle renvoie un code\r
non nul mais préserve la sauvegarde déjà créée.\r
\r
### Validation effectuée\r
\r
Banc reproductible : scripts/test_retention_staging.py.\r
Il utilise Python du projet et invoque le vrai script sous Windows PowerShell 5.1.\r
Il copie celui-ci dans des projets temporaires disposant de leur propre backups/.\r
Les archives et preuves y sont fictives ; -Apply n'y cible jamais le vrai projet.\r
\r
~~~powershell\r
uv run --project backend python scripts/test_retention_staging.py\r
~~~\r
\r
20 scénarios réussis : vide, une archive, moins de 7 journées, plus de 7 journées,\r
sélection par jour et égalité, semaines successives/passage d'année, union,\r
idempotence, noms/dates invalides, exports inconnus/manuels/anciens, fichiers\r
incomplets, hash incorrect, preuve manquante/modifiée, plan périmé par modification\r
ou ajout de fichier, chemin externe, dossier indisponible, jonction racine/enfant,\r
instructions falsifiées dans le plan et verrou concurrent.\r
\r
Simulation sur les archives existantes :\r
- 6 archives, 143 508 octets ;\r
- 3 fiables, couvrant 1 journée et 1 semaine ;\r
- 3 anciennes/manuelles explicitement protégées ;\r
- 6 conservées, 0 potentiellement supprimable, 0 supprimée ;\r
- sortie 0.\r
Plan : backups/logs/retention_2026-11-27_20-55-08_5693cf968359419dae5aa5cf971385c0.json.\r
\r
Aucun -Apply exécuté sur les archives réelles. Empreintes réelles et définition\r
de la tâche Windows vérifiées inchangées. Aucun appel Docker destructif.\r
\r
La rétention ne protège pas contre la panne du disque, le vol ou un ransomware.\r
Elle ne remplace pas une copie chiffrée indépendante. Cette copie, la rotation\r
des logs et l'activation de la suppression automatique restent à valider séparément.\r
