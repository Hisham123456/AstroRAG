# AstroRAG

Projet personnel pour apprendre à construire un RAG sur l’astronomie.

L’objectif est de répondre à des questions en français à partir d’une petite collection d’articles Wikipédia, en affichant les sources et les passages utilisés.

## Première version visée

- Une collection de 20 à 30 articles sur l’astronomie.
- Une recherche des passages pertinents pour une question.
- Des réponses accompagnées de sources consultables.
- Un signalement lorsque les documents ne permettent pas de répondre.
- Une interface simple pour poser des questions.

La sélection des sources et le script de collecte sont prêts. La recherche et la génération des réponses restent à réaliser.

## Suivi du projet

Voir [ROADMAP.md](ROADMAP.md) pour les grandes étapes et les critères de validation.

- Une seule branche `main` pour commencer.
- Un commit par changement cohérent, réalisé avec GitHub Desktop.
- Une issue par grande étape, avec une liste de tâches dans sa description.
- Un tag pour marquer chaque version terminée.
- Les petits ajustements et corrections sont décrits directement dans les commits.

## Données et sources

La liste des 20 articles Wikipédia en français est enregistrée dans [data/sources.json](data/sources.json). Chaque entrée contient un identifiant stable, le titre de la page, son URL et son thème. Les pages ont été vérifiées lors de la sélection le 24 octobre 2026.

La collecte utilise l’API MediaWiki pour récupérer les articles sélectionnés. Il ne s’agit pas d’explorer automatiquement les liens de Wikipédia. Le script résout les redirections et conserve la révision exacte de chaque article téléchargé.

Chaque article collecté devra conserver son titre, son URL, sa date de récupération et les informations de licence et d’attribution applicables.

Les données téléchargées, les index et les clés d’API ne sont pas suivis dans Git. Les scripts de collecte et la liste des sources permettront de reconstruire les données.

## Installer et lancer la collecte

Prérequis : Python 3.10 ou plus récent et une connexion Internet. Aucune clé d’API n’est nécessaire pour cette collecte.

Ouvrir PowerShell dans le dossier du projet, puis créer un environnement Python et installer les deux bibliothèques :

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Faire un premier essai sur un article, puis récupérer tout le corpus :

```powershell
.\.venv\Scripts\python.exe scripts/collect_wikipedia.py --limit 1
.\.venv\Scripts\python.exe scripts/collect_wikipedia.py
```

Le script suit la liste de `data/sources.json` et crée :

- `data/raw/<id>.json` : le HTML reçu de l’API et les métadonnées de l’article.
- `data/processed/<id>.json` : le texte nettoyé et les mêmes métadonnées, dont la révision, la licence et le lien vers l’historique des contributeurs.
- `data/collection_report.json` : le bilan du dernier lancement, avec les succès et les erreurs.

Les textes nettoyés conservent les paragraphes, les titres et les listes. Les tableaux, les illustrations, les renvois de notes et les sections de références sont exclus de cette première version. Le HTML d’origine reste disponible localement pour améliorer le nettoyage plus tard. Les informations de licence proviennent des paramètres du site Wikipédia ; les mentions particulières d’un article restent à consulter sur sa page.

Les articles déjà téléchargés sont réutilisés depuis `data/raw/`, puis nettoyés à nouveau. On peut donc interrompre et relancer le script. Si un article échoue, la collecte continue sur les suivants et se termine avec un code d’erreur. Consulter le rapport avant d’utiliser les résultats : d’anciens fichiers peuvent encore exister après un lancement en échec ou une modification de la sélection.

Pour télécharger les versions actuelles au lieu de réutiliser le cache :

```powershell
.\.venv\Scripts\python.exe scripts/collect_wikipedia.py --refresh
```

Une collecte fraîche peut récupérer des révisions différentes. Les identifiants enregistrés dans les fichiers locaux permettent de retrouver les versions utilisées ; le dépôt ne contient pas encore de liste verrouillée de ces révisions.

Les requêtes sont séquentielles, identifiées par le nom du projet, espacées d’au moins une seconde et réessayées en cas de problème temporaire, avec trois essais au maximum.

## Vérifications hors ligne

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Ces vérifications couvrent notamment le nettoyage, les révisions, les pages d’homonymie, la reprise depuis le cache et les erreurs réseau.
