# Feuille de route AstroRAG

Chaque section peut devenir une issue GitHub. Il n’est pas nécessaire de créer une issue pour chaque tâche.

## v0.1.0 — Constituer le corpus

- [x] Sélectionner 20 à 30 articles d’astronomie en français.
- [x] Enregistrer la liste des sources dans le dépôt.
- [ ] Créer un script de récupération et de nettoyage des textes.
- [ ] Conserver les métadonnées des sources et leur attribution.

Validation : le corpus peut être reconstruit à partir des scripts et de la liste des sources.

## v0.2.0 — Rechercher les passages pertinents

- [ ] Découper les textes en passages en conservant leur source.
- [ ] Calculer les embeddings avec un modèle adapté au français.
- [ ] Enregistrer un index local.
- [ ] Afficher les passages retrouvés pour une question.

Validation : sur une dizaine de questions préparées à l’avance, vérifier si les passages contenant les réponses sont retrouvés et noter les échecs.

## v0.3.0 — Générer des réponses avec sources

- [ ] Relier les passages retrouvés à un modèle de langage.
- [ ] Afficher des références liées aux sources effectivement fournies au modèle.
- [ ] Demander au modèle de signaler quand les informations sont insuffisantes.
- [ ] Vérifier les réponses sur des questions couvertes et non couvertes par le corpus.

Validation : contrôler manuellement que les affirmations des réponses sont soutenues par les passages cités et documenter les limites observées.

## v1.0.0 — Livrer une démonstration utilisable

- [ ] Ajouter une interface de discussion avec affichage des passages sources.
- [ ] Documenter l’installation, la configuration et le lancement.
- [ ] Évaluer le système sur une quinzaine de questions, dont des questions sans réponse dans le corpus.
- [ ] Ajouter une capture de démonstration et les limites connues au README.

Validation : une autre personne peut installer et lancer le projet en suivant le README.

## Routine avec GitHub Desktop

1. Réaliser un changement cohérent.
2. Relire les fichiers modifiés dans `Changes`.
3. Écrire un message de commit explicite, par exemple `Ajouter la liste des articles d’astronomie`.
4. Cliquer sur `Commit to main`, puis sur `Push origin`.
5. À la fin d’une grande étape, mettre à jour cette feuille de route, fermer l’issue correspondante et créer le tag de version sur le commit final.

Un commit conserve une étape de travail. Un tag donne un nom stable à une version terminée. Une issue sert à suivre un objectif.
