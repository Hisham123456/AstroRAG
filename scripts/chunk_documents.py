"""Découper les articles nettoyés en passages avec contexte et sources."""

import argparse
from bisect import bisect_left, bisect_right
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
CHUNKER_VERSION = 1
HEADING = re.compile(r"^(#{2,6})[ \t]+(.+?)[ \t]*$", re.MULTILINE)
SENTENCE_BREAK = re.compile(r"[.!?…][»\"”)]*\s+(?=[A-ZÀ-ÖØ-Þ0-9«\"“])")
ABBREVIATIONS = {"m.", "mme.", "dr.", "pr.", "env.", "etc.", "cf.", "av.", "j.", "c."}


def sections(text):
    """Repérer les titres et garder les positions dans le texte de départ."""
    path = []
    start = 0
    for heading in HEADING.finditer(text):
        if text[start:heading.start()].strip():
            yield start, heading.start(), [title for _, title in path] or ["Introduction"]
        level = len(heading.group(1))
        path = [(depth, title) for depth, title in path if depth < level]
        path.append((level, heading.group(2)))
        start = heading.end()
    if text[start:].strip():
        yield start, len(text), [title for _, title in path] or ["Introduction"]


def boundary_indices(text, words):
    """Exprimer les fins de paragraphes et de phrases en indices de mots."""
    starts = [word.start() for word in words]
    paragraphs = {bisect_left(starts, match.end()) for match in re.finditer(r"\n\s*\n", text)}
    sentences = set(paragraphs)
    for match in SENTENCE_BREAK.finditer(text):
        previous_word = text[:match.start() + 1].split()[-1].casefold()
        # Éviter quelques coupures fréquentes, par exemple « M. Hubble ».
        if previous_word in ABBREVIATIONS or re.fullmatch(r"[^\W\d_]\.", previous_word):
            continue
        sentences.add(bisect_left(starts, match.end()))
    sentences.update({0, len(words)})
    paragraphs.add(len(words))
    return sorted(paragraphs), sorted(sentences)


def split_section(text, chunk_size, overlap):
    """Produire des fenêtres de mots sans franchir une limite de section."""
    words = list(re.finditer(r"\S+", text))
    paragraphs, sentences = boundary_indices(text, words)
    start = 0
    while start < len(words):
        limit = min(start + chunk_size, len(words))
        minimum = start + max(1, chunk_size // 2)
        end = limit
        hard_split = False
        if limit < len(words):
            # Préférer un paragraphe complet si le passage est assez rempli.
            for boundaries in (paragraphs, sentences):
                index = bisect_right(boundaries, limit) - 1
                if index >= 0 and boundaries[index] >= minimum:
                    end = boundaries[index]
                    break
            else:
                hard_split = end not in sentences
        yield words[start].start(), words[end - 1].end(), end - start, hard_split
        if end == len(words):
            break
        next_start = end
        if overlap:
            # Reprendre des phrases entières, dans la limite du chevauchement.
            index = bisect_left(sentences, max(start + 1, end - overlap))
            if index < len(sentences) and sentences[index] < end:
                next_start = sentences[index]
            elif hard_split:
                next_start = max(start + 1, end - overlap)
        start = next_start


def chunk_article(article, chunk_size=300, overlap=40):
    """Associer à chaque passage les titres, la révision et l'attribution."""
    if chunk_size < 1 or not 0 <= overlap < chunk_size:
        raise ValueError("Il faut une taille positive et 0 <= overlap < chunk_size.")
    text = article["text"]
    metadata_fields = (
        "title", "url", "theme", "language", "page_id", "revision_id",
        "revision_url", "revision_timestamp", "retrieved_at", "license", "attribution",
    )
    metadata = {field: article[field] for field in metadata_fields}
    chunks = []
    for section_index, (section_start, section_end, path) in enumerate(sections(text)):
        body = text[section_start:section_end]
        previous_end = section_start
        for local_start, local_end, word_count, hard_split in split_section(body, chunk_size, overlap):
            char_start, char_end = section_start + local_start, section_start + local_end
            passage = text[char_start:char_end]
            fingerprint = json.dumps([
                CHUNKER_VERSION, article["id"], article["revision_id"],
                article.get("cleaner_version"), chunk_size, overlap,
                char_start, char_end, path, passage,
            ], ensure_ascii=False)
            digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]
            shared_text = text[char_start:min(previous_end, char_end)] if char_start < previous_end else ""
            chunks.append({
                "id": f"{article['id']}-{digest}",
                "article_id": article["id"],
                **metadata,
                "section_path": path,
                "section_index": section_index,
                "chunk_index": len(chunks),
                "text": passage,
                "contextualized_text": f"Article : {article['title']}\nSection : {' > '.join(path)}\n\n{passage}",
                "word_count": word_count,
                "overlap_word_count": len(shared_text.split()),
                "char_start": char_start,
                "char_end": char_end,
                "hard_split": hard_split,
                "cleaner_version": article.get("cleaner_version"),
                "chunker_version": CHUNKER_VERSION,
            })
            previous_end = char_end
    if not chunks:
        raise ValueError(f"Aucun passage produit pour {article['id']}.")
    return chunks


def load_articles():
    """Ne lire que les articles de la sélection actuelle et refuser les manquants."""
    sources = json.loads((ROOT / "data/sources.json").read_text(encoding="utf-8"))
    if not isinstance(sources, list) or not sources:
        raise ValueError("La liste des sources est vide ou invalide.")
    articles = []
    seen = set()
    for source in sources:
        article_id = source["id"]
        if not isinstance(article_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", article_id):
            raise ValueError("Identifiant de source invalide.")
        if article_id in seen:
            raise ValueError(f"Source en double : {article_id}")
        seen.add(article_id)
        path = ROOT / "data/processed" / f"{article_id}.json"
        if not path.exists():
            raise ValueError(f"Article manquant : {article_id}. Relancez collect_wikipedia.py.")
        article = json.loads(path.read_text(encoding="utf-8"))
        if article["id"] != article_id or article.get("source") != source:
            raise ValueError(f"Article différent de la sélection : {article_id}. Relancez la collecte.")
        if not isinstance(article.get("text"), str) or not article["text"].strip():
            raise ValueError(f"Texte vide ou invalide : {article_id}")
        articles.append(article)
    return articles


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def build_corpus(chunk_size=300, overlap=40):
    articles = load_articles()
    chunks = []
    counts = []
    for article in articles:
        passages = chunk_article(article, chunk_size, overlap)
        chunks.extend(passages)
        counts.append({"id": article["id"], "revision_id": article["revision_id"], "chunks": len(passages)})
        print(f"{article['title']} : {len(passages)} passages", flush=True)
    if len({chunk["id"] for chunk in chunks}) != len(chunks):
        raise ValueError("Identifiants de passages en double.")
    report = {
        "chunker_version": CHUNKER_VERSION,
        "chunk_size_words": chunk_size,
        "max_overlap_words": overlap,
        "article_count": len(articles),
        "chunk_count": len(chunks),
        "min_words": min(chunk["word_count"] for chunk in chunks),
        "max_words": max(chunk["word_count"] for chunk in chunks),
        "average_words": round(sum(chunk["word_count"] for chunk in chunks) / len(chunks), 1),
        "under_40_words_count": sum(chunk["word_count"] < 40 for chunk in chunks),
        "hard_split_count": sum(chunk["hard_split"] for chunk in chunks),
        "articles": counts,
    }
    # Tous les articles sont validés avant de remplacer les résultats précédents.
    output = ROOT / "data/chunks"
    write_file(output / "chunks.json", json.dumps(chunks, ensure_ascii=False, indent=2) + "\n")
    write_file(output / "report.json", json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    # Répartir dix exemples sur le corpus pour faciliter une relecture humaine.
    indices = sorted({round(i * (len(chunks) - 1) / 9) for i in range(10)})
    examples = ["# Aperçu du découpage\n\nDix exemples répartis sur le corpus.\n"]
    for index in indices:
        chunk = chunks[index]
        examples.append(
            f"## {chunk['title']} — {' > '.join(chunk['section_path'])}\n\n"
            f"Identifiant : `{chunk['id']}` — {chunk['word_count']} mots.\n\n"
            f"[Source, révision {chunk['revision_id']}]({chunk['revision_url']})\n\n"
            f"{chunk['text']}\n"
        )
    write_file(output / "preview.md", "\n".join(examples))
    print(f"\nBilan : {len(chunks)} passages pour {len(articles)} articles.")
    print(f"Taille : {report['min_words']} à {report['max_words']} mots ; moyenne {report['average_words']}.")
    print(f"Coupures forcées au milieu d'une phrase : {report['hard_split_count']}.")
    print("Résultats : data/chunks/ — relecture : preview.md")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunk-size", type=int, default=300, help="Nombre maximal de mots, hors titres (300).")
    parser.add_argument("--overlap", type=int, default=40, help="Chevauchement maximal en mots (40).")
    args = parser.parse_args()
    if args.chunk_size < 1 or not 0 <= args.overlap < args.chunk_size:
        parser.error("Il faut --chunk-size > 0 et 0 <= --overlap < --chunk-size.")
    try:
        build_corpus(args.chunk_size, args.overlap)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"ERREUR — {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
