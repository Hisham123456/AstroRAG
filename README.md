# AstroRAG

Projet personnel pour apprendre à construire un RAG sur l’astronomie.

L’objectif est de répondre à des questions en français à partir d’une petite collection d’articles Wikipédia, en affichant les sources et les passages utilisés.

## Première version visée

- Une collection de 20 à 30 articles sur l’astronomie.
- Une recherche des passages pertinents pour une question.
- Des réponses accompagnées de sources consultables.
- Un signalement lorsque les documents ne permettent pas de répondre.
- Une interface simple pour poser des questions.

La sélection des sources est prête. La récupération des textes et le développement du RAG restent à réaliser.

## Suivi du projet

Voir [ROADMAP.md](ROADMAP.md) pour les grandes étapes et les critères de validation.

- Une seule branche `main` pour commencer.
- Un commit par changement cohérent, réalisé avec GitHub Desktop.
- Une issue par grande étape, avec une liste de tâches dans sa description.
- Un tag pour marquer chaque version terminée.
- Les petits ajustements et corrections sont décrits directement dans les commits.

## Données et sources

La liste des 20 articles Wikipédia en français est enregistrée dans [data/sources.json](data/sources.json). Chaque entrée contient un identifiant stable, le titre de la page, son URL et son thème. Les pages ont été vérifiées lors de la sélection le 24 octobre 2026.

La collecte utilisera l’API MediaWiki pour récupérer les articles sélectionnés. Il ne s’agit pas d’explorer automatiquement les liens de Wikipédia. Le futur script résoudra les redirections et conservera la révision exacte de chaque article téléchargé.

Chaque article collecté devra conserver son titre, son URL, sa date de récupération et les informations de licence et d’attribution applicables.

Les données téléchargées, les index et les clés d’API ne sont pas suivis dans Git. Les scripts de collecte et la liste des sources permettront de reconstruire les données.
