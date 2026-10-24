# AstroRAG

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Projet Python existant : recherche NumPy, embeddings multilingual-e5-small et génération Gemini 3.5 Flash-Lite. L’interface locale ajoute Flask et du HTML, CSS et JavaScript sans compilation.

## Users

Projet personnel francophone pour apprendre le fonctionnement d’un RAG et interroger des documents d’astronomie.

## Product Purpose

Poser une question, obtenir une réponse en français et vérifier ses affirmations dans les passages Wikipédia utilisés.

## Operating Context

Application sur l’ordinateur de l’utilisateur, dépôt suivi avec GitHub Desktop. Un serveur garde le modèle local en mémoire ; Gemini reçoit la question et les passages utiles via API.

## Capabilities and Constraints

Historique limité à la session, choix confirmé par l’utilisateur. Aucune conservation des discussions après fermeture ou actualisation de la page. Comprendre les questions de suite, afficher les sources, signaler les informations insuffisantes et les erreurs. La clé Gemini reste dans .env côté serveur. Aucun déploiement public demandé.

## Evidence on Hand

Vingt articles français, 1 174 entrées indexées, des questions de contrôle, des tests hors ligne et des essais réels de génération. Les fichiers générés restent locaux.

## Product Principles

- Donner accès aux passages qui étayent les réponses.
- Ne pas ajouter des faits absents des sources.
- Garder les réglages techniques hors de la conversation.
- Faire un commit par changement cohérent, sans multiplier les issues.
