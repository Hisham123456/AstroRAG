---
name: AstroRAG
description: Une conversation scientifique en français, sources à l’appui.
colors:
  paper: "#edf2f6"
  white: "#fff"
  ink: "#20324e"
  muted: "#52647a"
  blue: "#213c68"
  cobalt: "#3157a4"
  amber: "#ffc55c"
  line: "#cdd7e2"
  tint: "#e3ebf7"
  error: "#9c3428"
  source-muted: "#d1ddee"
  source-rule: "#506a8f"
  field-line: "#a8b8ca"
  ready: "#347457"
  amber-hover: "#f6b53c"
  suggestion-hover: "#e4ebf4"
  error-paper: "#fff0ed"
  error-line: "#c8877e"
  source-number: "#3a5881"
  source-count: "#365780"
typography:
  display:
    fontFamily: "Atkinson, 'Segoe UI', sans-serif"
    fontSize: "clamp(30px, 3vw, 42px)"
    fontWeight: 650
    lineHeight: 1.14
    letterSpacing: "-.035em"
  headline:
    fontFamily: "Atkinson, 'Segoe UI', sans-serif"
    fontSize: "23px"
    fontWeight: 600
    letterSpacing: "-.025em"
  title:
    fontFamily: "Atkinson, 'Segoe UI', sans-serif"
    fontSize: "15px"
    fontWeight: 650
    lineHeight: 1.4
  body:
    fontFamily: "Atkinson, 'Segoe UI', sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.8
  intro:
    fontFamily: "Atkinson, 'Segoe UI', sans-serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.65
  question:
    fontFamily: "Atkinson, 'Segoe UI', sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.6
  field:
    fontFamily: "Atkinson, 'Segoe UI', sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Atkinson, 'Segoe UI', sans-serif"
    fontSize: "14px"
    fontWeight: 700
  excerpt:
    fontFamily: "Atkinson, 'Segoe UI', sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.8
rounded:
  citation: "6px"
  secondary: "8px"
  passage: "10px"
  composer: "14px"
  question: "16px 16px 4px 16px"
  dot: "50%"
spacing:
  xs: "4px"
  sm: "8px"
  control-gap: "10px"
  md: "12px"
  lg: "16px"
  passage: "17px"
  xl: "20px"
  panel-bottom: "22px"
  section: "24px"
  panel: "26px"
  turn: "34px"
  gutter: "40px"
  reading: "52px"
components:
  button-send:
    backgroundColor: "{colors.amber}"
    textColor: "{colors.blue}"
    rounded: "{rounded.passage}"
    size: "44px"
  button-send-hover:
    backgroundColor: "{colors.amber-hover}"
  button-secondary:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.secondary}"
    padding: "10px 14px"
  button-secondary-hover:
    backgroundColor: "{colors.paper}"
  button-text:
    textColor: "{colors.cobalt}"
    padding: "2px 0"
  button-retry:
    backgroundColor: "{colors.white}"
    textColor: "{colors.error}"
    rounded: "{rounded.citation}"
    padding: "7px 12px"
  composer:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.composer}"
    padding: "12px 12px 12px 20px"
  citation:
    backgroundColor: "{colors.tint}"
    textColor: "{colors.blue}"
    rounded: "{rounded.citation}"
    padding: "0 5px"
    height: "27px"
  citation-selected:
    backgroundColor: "{colors.amber}"
  question:
    backgroundColor: "{colors.blue}"
    textColor: "{colors.white}"
    typography: "{typography.question}"
    rounded: "{rounded.question}"
    padding: "16px 20px"
  passage:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    typography: "{typography.excerpt}"
    rounded: "{rounded.passage}"
    padding: "17px"
  suggestion:
    textColor: "{colors.ink}"
    padding: "17px 0"
  suggestion-hover:
    backgroundColor: "{colors.suggestion-hover}"
    textColor: "{colors.cobalt}"
---

# Design System: AstroRAG

## Overview

**Creative North Star: "L’édition scientifique des années 1970"**

Le système reprend le bleu d’une couverture scientifique, le papier froid et un repère ambre pour rendre une conversation documentée lisible. Le dessin orbital reste léger ; les titres humanistes, les filets et les surfaces franches portent l’identité. Cette direction correspond au monde retenu dans le brief : candidate 4, seed `279cb4bd`.

L’interface privilégie la lecture puis la vérification d’un passage. La densité reste mesurée, avec des réponses ouvertes sur le fond de page et des extraits blancs dans un panneau bleu. Les contrôles suivent les usages contemporains du Web. La documentation décrit les valeurs livrées dans `web/style.css` et les états de `web/app.js` ; les paramètres du modèle restent hors de l’interface de conversation.

**Key Characteristics:**

- Papier froid et couverture bleue, sans ombre.
- Une seule famille humaniste auto-hébergée.
- Ambre commun à la citation et au passage sélectionnés.
- Filets fins, réponses aérées et extraits directement consultables.

## Colors

La palette associe une couverture bleue à des surfaces de lecture claires ; les noms et valeurs du frontmatter font foi.

### Primary

- **Bleu de couverture — blue** : fond du panneau des sources, questions de l’utilisateur, marque et numéros de citation.
- **Bleu de lecture — cobalt** : liens, orbite, point d’attente et focus sur les surfaces claires.
- **Ambre de repérage — amber** : envoi, satellite orbital, livre de l’état vide, citation active et numéro du passage actif. Le survol de l’envoi emploie **amber-hover**.

### Neutral

- **Papier froid — paper** : fond général et zone de saisie.
- **Blanc de lecture — white** : en-tête, champ de saisie, extraits et texte sur bleu.
- **Encre — ink** : texte principal sur surfaces claires.
- **Encre secondaire — muted** : introduction, légendes, aide et réponse de clarification.
- **Filet — line** : séparateurs des suggestions, en-tête et limites de la grille.
- **Teinte de référence — tint** : citation au repos.
- **Texte sur couverture — source-muted** et **Filet sur couverture — source-rule** : explications, chemin de section et séparateurs des sources.
- **Contour de saisie — field-line** : champ au repos ; son contour devient cobalt au focus.
- **Numéro au repos — source-number** et **Compteur — source-count** : deux fonds bleus distincts, effectivement utilisés dans le panneau.
- **Survol de suggestion — suggestion-hover** : léger aplat sous la ligne survolée.

Les couleurs fonctionnelles complètent cette palette : **ready** pour le point de disponibilité ; **error**, **error-paper** et **error-line** pour les erreurs et la reprise. L’état est toujours exprimé aussi par du texte. Les nuances auxiliaires des pieds de panneau et des barres de défilement restent locales au CSS.

**The Shared Selection Rule.** Une citation sélectionnée et le numéro de son passage utilisent le même ambre ; cet état est lié à une réponse précise, jamais au seul numéro de source.

## Typography

**Display Font:** Atkinson, avec Segoe UI puis sans-serif en repli.  
**Body Font:** la même famille Atkinson.  
**Label/Mono Font:** aucune famille distincte.

Le fichier variable local `web/fonts/Atkinson.ttf` est déclaré pour les graisses (100–900), en style normal, avec `font-display: swap` et `font-synthesis: none`. Le projet n’utilise pas de police distante. Les différences de taille, de graisse et d’interligne établissent la hiérarchie ; les libellés conservent la casse naturelle du français.

### Hierarchy

- **Display** : titre d’accueil, rôle `display` ; sur mobile, taille fixe (34px), largeur maximale (16ch).
- **Headline** : titre du panneau des sources, rôle `headline`.
- **Title** : titre d’un passage, rôle `title`, suivi d’un chemin de section (12px, graisse 400).
- **Body** : réponse, rôle `body`, mesure maximale (68ch) ; sur mobile (16px), même interligne.
- **Introduction** : rôle `intro`, mesure maximale (52ch) ; sur mobile (16px).
- **Question** : rôle `question`, retours à la ligne conservés ; sur mobile (16px).
- **Field** : rôle `field`, saisie et placeholder.
- **Label** : signature de réponse, rôle `label`. Les aides utilisent (11–12px) ; les titres des suggestions (13px, puis 12px sur mobile).
- **Excerpt** : rôle `excerpt`, texte source avec retours à la ligne conservés ; attribution (11px, interligne 1.6).

**The Reading Measure Rule.** Les réponses restent limitées à 68ch et l’introduction à 52ch ; les longues chaînes se replient dans les questions, réponses et sources.

## Layout

La surface Web actuelle combine un en-tête blanc et une grille centrée, de largeur maximale (1600px). Au-dessus de (760px), l’en-tête mesure (88px) et la grille réserve (360px) aux sources. La conversation et le panneau occupent la hauteur restante de la fenêtre avec `100dvh`. La conversation et la liste des sources défilent indépendamment ; le compositeur reste sous la zone défilante, sans superposition.

L’accueil est limité à (790px), les échanges et le compositeur à (870px). L’accueil et les échanges ont des marges intérieures de lecture (52px) ; le compositeur dispose de marges latérales (40px). Les suggestions sont des lignes, de largeur maximale (560px), séparées par des filets. Le rythme utilise de petits écarts pour les contrôles et des espacements plus généreux entre les tours ; les valeurs réutilisées figurent dans `spacing`.

À (1050px) et moins, le panneau passe à (310px), les marges de lecture à (30px), celles du compositeur à (25px) et celles du panneau à (22px). Les catégories de suggestion passent au-dessus de la question.

À (760px) et moins, l’en-tête mesure (72px), la description de marque disparaît et le contenu suit un flux vertical : conversation, compositeur, puis sources. Le compositeur est statique, séparé par un filet ; il ne masque pas les messages. Les sources ne forment ni tiroir ni fenêtre flottante : leur hauteur est automatique avec un minimum (300px). Les marges sont (22px) pour les échanges, (18px) pour le compositeur et (24px) pour les sources. Les bulles peuvent atteindre (95%) de la largeur, contre (85%) sur grand écran. L’aide clavier est masquée sur mobile.

Activer une citation ouvre et sélectionne le passage, déplace le focus sur son bouton et, sur mobile, amène le panneau en vue. « Revenir à la réponse » est visible uniquement sur mobile ; il replace le focus et le défilement sur le tour associé. À partir de (1600px), des filets latéraux délimitent la grille.

## Elevation & Depth

Aucune ombre, aucun flou d’arrière-plan et aucun dégradé ne sont utilisés. La profondeur vient du contraste entre papier, couverture et extrait blanc, ainsi que des filets d’un pixel. Les réponses restent sur le papier ; seules les questions et les extraits occupent des aplats.

**The Flat Paper Rule.** Les surfaces se distinguent par la couleur, l’espace et les filets ; elles n’acquièrent pas d’ombre au survol ou au focus.

La seule transition est celle du contour de saisie (0.15s). Pendant la recherche, le point d’état respire (1.5s, ease-in-out, en boucle, opacité 0.3 à mi-parcours). La préférence de réduction des mouvements supprime animations, transitions et défilement animé. Les déplacements de lecture programmatiques utilisent un mouvement immédiat.

## Shapes

Les contrôles ont des angles doucement arrondis : citation et numéro de source, bouton secondaire, passage et bouton d’envoi, puis compositeur. Les rayons normatifs sont dans `rounded`. La question possède une silhouette asymétrique avec un angle inférieur droit plus court. Les points d’état sont circulaires. Les suggestions, séparateurs et liens d’action n’ont pas de contour de carte.

Les icônes sont des tracés SVG : orbite, livre, plus, flèche d’envoi et chevrons. Le trait général est arrondi (1.6), avec des variantes réellement livrées pour l’orbite (1.2), le livre (1.1) et l’envoi (2). Le satellite orbital est rempli d’ambre.

## Components

### Buttons

Les actions restent explicites et proches de leur contenu.

- **Envoi** : carré ambre (44 × 44px), rayon de passage, flèche SVG bleue. Son survol utilise le ton ambre de survol ; le bouton est désactivé si le modèle n’est pas prêt, pendant une réponse ou si le champ est vide.
- **Nouvelle discussion** : surface blanche, filet neutre, rayon secondaire, hauteur minimale (44px), graisse (600), corps (14px). Au survol, fond papier et bord cobalt. Sur mobile, corps (12px) et padding (8px 10px). Pendant une réponse, le bouton est désactivé.
- **Consulter les sources** : bouton textuel cobalt (13px), souligné par une bordure, sans aplat. Il sélectionne la première référence du tour.
- **Réessayer cette question** : bouton blanc, contour d’erreur, rayon de citation, hauteur minimale (40px). Il reprend le tour en échec sans dupliquer la question.
- **Retour mobile** : bouton blanc sur bleu, soulignement discret, hauteur minimale (40px) ; texte ambre au survol.

Les boutons désactivés ont une opacité (0.55) et un curseur d’attente. Le focus visible est un contour (3px) décalé de (4px), cobalt sur clair et ambre sur bleu. Le lien d’article, dans son extrait blanc, reprend le focus cobalt. Aucun état actif supplémentaire n’est défini.

### Citations and passages

La citation est un bouton numéroté compact, au fond teinté, de hauteur (27px) et largeur minimale (28px), corps (12px), graisse (700). Le survol et la sélection utilisent l’ambre. `aria-pressed` indique la sélection.

Le panneau affiche uniquement les passages cités dans la réponse choisie et un compteur. Chaque bouton de passage comporte un numéro, un titre et le chemin de section ; sa hauteur minimale est (48px). Son état `aria-expanded` correspond à la visibilité de l’extrait associé par `aria-controls`. Un seul passage est ouvert à la fois. Un clic sur le passage ouvert le referme ; un autre tour peut réactiver ses propres sources.

L’extrait est blanc, avec le rayon de passage et un padding (17px). Il montre le texte, un lien vers la révision Wikipédia et l’attribution. Le lien s’ouvre dans un nouvel onglet ; les adresses acceptées dans ce contrôle sont en HTTPS sur `fr.wikipedia.org`.

### Conversation and states

La question est un aplat bleu aligné à droite. La réponse commence par une petite orbite et la signature AstroRAG, puis des paragraphes lisibles sur papier ; les citations suivent les affirmations. Les métadonnées donnent l’action de consultation et la durée.

L’accueil présente une orbite, un titre, un court texte et trois vraies questions de départ, sans échange simulé. Les suggestions sont désactivées au chargement ou pendant la recherche ; leur survol colore la ligne et le texte.

Le chargement initial, l’état prêt et l’erreur serveur ont un libellé de statut. La recherche d’une réponse présente un point animé et un message adapté à la présence de contexte. Une réponse insuffisamment étayée apparaît en texte secondaire, avec un état « Aucun passage cité » dans les sources. Une erreur de réponse apparaît dans un bloc d’alerte teinté, avec reprise. Les sources de la réponse précédente restent consultables pendant une nouvelle recherche.

### Input and keyboard

Le compositeur blanc est bordé et arrondi, avec un champ sans bord propre et le bouton d’envoi. Le focus interne change son contour en cobalt. Le champ possède un libellé accessible, une limite (1000 caractères), une hauteur minimale (40px) et une croissance jusqu’à (140px). Il reste désactivé tant que le modèle est indisponible ou occupé.

Entrée envoie, Maj + Entrée ajoute une ligne ; une composition de texte en cours n’est pas soumise. Après la réponse, le focus revient à la saisie. Une nouvelle discussion efface les tours et rétablit accueil et sources vides. L’historique reste uniquement en mémoire dans la page ; les trois derniers tours réussis sont envoyés comme contexte de suivi.

### Header and accessibility

L’en-tête associe un lien de marque et « Nouvelle discussion », avec une description secondaire sur grand écran. Il n’existe pas de menu de navigation additionnel.

Un lien d’évitement apparaît au focus et mène à la question. La discussion est une zone de journal à annonce polie ; le formulaire expose son occupation, les recherches utilisent un statut et les erreurs une alerte. Les icônes décoratives sont masquées aux technologies d’assistance, le bouton d’envoi a un nom accessible et les sources gardent des contrôles clavier natifs. La couleur ne remplace ni le texte d’état ni les attributs de sélection.

## Do's and Don'ts

### Do:

- **Do** conserver la famille Atkinson auto-hébergée et la casse naturelle des libellés.
- **Do** lier visuellement et sémantiquement la citation au passage de la réponse sélectionnée.
- **Do** préserver les mesures de lecture, le repli des longues chaînes et les états de focus visibles.
- **Do** garder les sources dans le flux vertical sur mobile et un retour explicite à la réponse.
- **Do** afficher chargement, erreur et insuffisance des sources par des mots compréhensibles.

### Don't:

- **Don't** ajouter d’ombres ou de surfaces flottantes aux composants plats de ce système.
- **Don't** transformer l’astronomie en cockpit ou en fond de ciel étoilé décoratif.
- **Don't** présenter un faux échange pour remplir l’état vide.
- **Don't** suggérer une conservation des discussions après actualisation ou fermeture de la page.
