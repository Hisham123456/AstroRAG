"""Construire des embeddings locaux et rechercher des passages en français."""

import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import unicodedata

import numpy as np

if __package__:
    from .chunk_documents import boundary_indices, load_articles
else:
    from chunk_documents import boundary_indices, load_articles


ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "intfloat/multilingual-e5-small"
MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
INDEX_PATH = ROOT / "data/index/embeddings.npz"
STOP_WORDS = set("a au aux avec ce ces cette dans de des du elle en est et etre il la le les on ou par pour qu que quel quelle quelles quels qui quoi sa se ses son sont sur un une comment pourquoi combien".split())


def lexical_tokens(text):
    """Normaliser accents et pluriels simples, sans effacer les comparatifs."""
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    tokens = re.findall(r"[a-z0-9]+", text)
    return [word[:-1] if len(word) > 4 and word.endswith("s") and word != "moins" else word
            for word in tokens if len(word) > 1 and word not in STOP_WORDS]


class LexicalIndex:
    """BM25 : privilégier les mots utiles, rares et présents dans le passage."""

    def __init__(self, texts):
        self.lengths = np.zeros(len(texts), dtype=np.float32)
        self.postings = defaultdict(list)
        self.phrases = []
        for index, text in enumerate(texts):
            tokens = lexical_tokens(text)
            counts = Counter(tokens)
            self.phrases.append(" " + " ".join(tokens) + " ")
            self.lengths[index] = sum(counts.values())
            for word, frequency in counts.items():
                self.postings[word].append((index, frequency))
        self.average_length = max(float(self.lengths.mean()), 1.0)

    def scores(self, question):
        scores = np.zeros(len(self.lengths), dtype=np.float32)
        k1, b = 1.5, 0.75
        query_tokens = lexical_tokens(question)
        phrase_weight = 0.0
        for word in set(query_tokens):
            postings = self.postings.get(word, [])
            if not postings:
                continue
            inverse_frequency = np.log(1 + (len(scores) - len(postings) + 0.5) / (len(postings) + 0.5))
            phrase_weight += inverse_frequency
            for index, frequency in postings:
                length_factor = 1 - b + b * self.lengths[index] / self.average_length
                scores[index] += inverse_frequency * frequency * (k1 + 1) / (frequency + k1 * length_factor)
        # Préserver une relation courte comme « planète la plus proche du Soleil ».
        # Les mots fréquents seuls ne suffisent pas : leur ordre porte aussi du sens.
        if 3 <= len(query_tokens) <= 8:
            phrase = " " + " ".join(query_tokens) + " "
            for index, text in enumerate(self.phrases):
                if phrase in text:
                    scores[index] += 2 * phrase_weight
        return scores


@lru_cache(maxsize=1)
def cached_lexical_index(texts):
    # Construit une fois par corpus ; aucun poids ni embedding n'est recalculé.
    return LexicalIndex(texts)


def hybrid_ranking(semantic_scores, lexical_scores, top_k):
    """Fusionner les classements, plutôt que des scores d'échelles différentes."""
    semantic_order = np.argsort(-semantic_scores, kind="stable")
    lexical_order = np.argsort(-lexical_scores, kind="stable")
    fused = np.zeros(len(semantic_scores), dtype=np.float32)
    # Reciprocal Rank Fusion : un passage retrouvé par les deux méthodes gagne en poids.
    for rank, index in enumerate(semantic_order[:50], 1):
        fused[index] += 1 / (60 + rank)
    for rank, index in enumerate(lexical_order[:50], 1):
        if lexical_scores[index] > 0:
            fused[index] += 1 / (60 + rank)
    order = np.lexsort((-semantic_scores, -fused))[:top_k]
    return order, fused


def contextualize(chunk, text):
    return f"Article : {chunk['title']}\nSection : {' > '.join(chunk['section_path'])}\n\n{text}"


def fit_chunks(chunks, token_count, max_tokens):
    """Redécouper les passages trop longs sans tronquer le texte encodé."""
    fitted = []
    for parent in chunks:
        original = parent["text"]
        if token_count("passage: " + contextualize(parent, "x")) >= max_tokens:
            raise ValueError(f"Titres trop longs pour le modèle : {parent['id']}")

        def split(start, end):
            fragment = original[start:end]
            start += len(fragment) - len(fragment.lstrip())
            end -= len(fragment) - len(fragment.rstrip())
            text = original[start:end]
            contextualized = contextualize(parent, text)
            count = token_count("passage: " + contextualized)
            if count <= max_tokens:
                part = {key: value for key, value in parent.items() if key != "overlap_word_count"}
                part.update({
                    "id": parent["id"] if start == 0 and end == len(original) else f"{parent['id']}-{start}-{end}",
                    "parent_chunk_id": parent["id"], "text": text,
                    "contextualized_text": contextualized,
                    "char_start": parent["char_start"] + start,
                    "char_end": parent["char_start"] + end,
                    "word_count": len(text.split()), "input_token_count": count,
                })
                fitted.append(part)
                return
            words = list(re.finditer(r"\S+", text))
            cut = len(text) // 2
            if len(words) > 1:
                paragraphs, sentences = boundary_indices(text, words)
                word_cut = len(words) // 2
                for boundaries in (paragraphs, sentences):
                    candidates = [i for i in boundaries if 0 < i < len(words)
                                  and len(words) / 4 <= i <= 3 * len(words) / 4]
                    if candidates:
                        word_cut = min(candidates, key=lambda i: abs(i - len(words) / 2))
                        break
                cut = words[word_cut].start()
            if not 0 < cut < len(text):
                raise ValueError(f"Passage impossible à adapter au modèle : {parent['id']}")
            split(start, start + cut)
            split(start + cut, end)

        split(0, len(original))
    return fitted


def corpus_signature():
    """Détecter un changement des sources, textes ou passages après indexation."""
    sources_path = ROOT / "data/sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    paths = [sources_path, ROOT / "data/chunks/chunks.json"]
    for source in sources:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", source["id"]):
            raise ValueError("Identifiant de source invalide.")
        paths.append(ROOT / "data/processed" / f"{source['id']}.json")
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.relative_to(ROOT)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def load_chunks():
    chunks = json.loads((ROOT / "data/chunks/chunks.json").read_text(encoding="utf-8"))
    if not chunks or not isinstance(chunks, list):
        raise ValueError("Aucun passage. Lancez chunk_documents.py.")
    articles = {article["id"]: article for article in load_articles()}
    seen = set()
    covered_articles = set()
    for chunk in chunks:
        article = articles[chunk["article_id"]]
        current_text = article["text"][chunk["char_start"]:chunk["char_end"]]
        if chunk["revision_id"] != article["revision_id"] or chunk["text"] != current_text:
            raise ValueError("Les passages sont anciens : relancez chunk_documents.py.")
        if chunk["id"] in seen or not chunk["text"].strip():
            raise ValueError("Passage vide ou identifiant dupliqué.")
        seen.add(chunk["id"])
        covered_articles.add(chunk["article_id"])
    if covered_articles != set(articles):
        raise ValueError("Des articles manquent dans les passages. Relancez chunk_documents.py.")
    return chunks


class Encoder:
    """Le même modèle et la même révision pour les passages et les questions."""

    def __init__(self, model_id=MODEL_ID, revision=MODEL_REVISION, offline=False):
        if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError("La révision du modèle doit être un identifiant de commit précis.")
        # Garder les téléchargements dans le projet, hors du suivi Git.
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        from sentence_transformers import SentenceTransformer
        import torch

        torch.set_num_threads(min(4, os.cpu_count() or 1))
        self.model = SentenceTransformer(
            model_id, revision=revision, device="cpu",
            cache_folder=str(ROOT / ".cache/models"),
            local_files_only=offline, trust_remote_code=False,
        )
        self.model_id = model_id
        self.revision = revision
        self.max_tokens = min(512, self.model.max_seq_length)
        get_dimension = getattr(self.model, "get_embedding_dimension", self.model.get_sentence_embedding_dimension)
        self.dimension = get_dimension()

    def token_count(self, text):
        return len(self.model.tokenizer.encode(text, truncation=False, verbose=False))

    def encode(self, texts, prefix, progress=False):
        inputs = [prefix + text for text in texts]
        if any(self.token_count(text) > self.max_tokens for text in inputs):
            raise ValueError(f"Texte trop long : la limite est de {self.max_tokens} tokens.")
        return self.model.encode(
            inputs, prompt="", batch_size=16, show_progress_bar=progress,
            convert_to_numpy=True, normalize_embeddings=True,
        ).astype(np.float32)


def validate_vectors(vectors, count, dimension):
    if vectors.shape != (count, dimension) or count < 1 or dimension < 1:
        raise ValueError("Dimensions de l'index incohérentes.")
    if not np.isfinite(vectors).all():
        raise ValueError("L'index contient des nombres invalides.")
    if not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4):
        raise ValueError("Les vecteurs de l'index ne sont pas normalisés.")


def build_index():
    original = load_chunks()
    signature = corpus_signature()
    print(f"Chargement du modèle {MODEL_ID} (premier téléchargement si nécessaire)...", flush=True)
    encoder = Encoder()
    chunks = fit_chunks(original, encoder.token_count, encoder.max_tokens)
    if len({chunk["id"] for chunk in chunks}) != len(chunks):
        raise ValueError("Identifiants dupliqués après adaptation des passages.")
    print(f"{len(original)} passages adaptés en {len(chunks)} entrées, sans troncature.", flush=True)
    vectors = encoder.encode([chunk["contextualized_text"] for chunk in chunks], "passage: ", progress=True)
    validate_vectors(vectors, len(chunks), encoder.dimension)
    if signature != corpus_signature():
        raise ValueError("Le corpus a changé pendant le calcul. Relancez l'indexation.")
    manifest = {
        "format_version": 1, "model_id": encoder.model_id, "model_revision": encoder.revision,
        "dimension": vectors.shape[1], "count": len(chunks),
        "original_chunk_count": len(original), "max_tokens": encoder.max_tokens,
        "max_input_tokens": max(chunk["input_token_count"] for chunk in chunks),
        "normalized": True, "corpus_sha256": signature,
        "passage_prefix": "passage: ", "query_prefix": "query: ",
    }
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = INDEX_PATH.with_suffix(".tmp")
    # Un seul fichier lie les lignes de la matrice à leurs passages et au modèle.
    with temporary.open("wb") as stream:
        np.savez_compressed(
            stream, embeddings=vectors,
            chunks=json.dumps(chunks, ensure_ascii=False),
            manifest=json.dumps(manifest, ensure_ascii=False),
        )
    temporary.replace(INDEX_PATH)
    print(f"Index enregistré : {len(chunks)} vecteurs de dimension {vectors.shape[1]}.")
    return manifest


def load_index():
    with np.load(INDEX_PATH, allow_pickle=False) as data:
        vectors = data["embeddings"]
        chunks = json.loads(data["chunks"].item())
        manifest = json.loads(data["manifest"].item())
    if manifest["format_version"] != 1 or manifest["count"] != len(chunks):
        raise ValueError("Format de l'index invalide. Reconstruisez-le.")
    validate_vectors(vectors, len(chunks), manifest["dimension"])
    if manifest["corpus_sha256"] != corpus_signature():
        raise ValueError("Le corpus a changé : relancez semantic_search.py build.")
    return vectors, chunks, manifest


def rank_passages(vectors, query_vector, chunks, top_k=5):
    if top_k < 1:
        raise ValueError("Le nombre de résultats doit être positif.")
    query = np.asarray(query_vector, dtype=np.float32).reshape(-1)
    if query.shape != (vectors.shape[1],) or not np.isfinite(query).all():
        raise ValueError("Vecteur de question invalide.")
    norm = np.linalg.norm(query)
    if norm == 0:
        raise ValueError("Le vecteur de la question est nul.")
    # Avec des vecteurs de norme 1 : cosinus = produit scalaire.
    scores = vectors @ (query / norm)
    order = np.argsort(-scores, kind="stable")[:top_k]
    return [{"score": float(scores[i]), "chunk": chunks[i]} for i in order]


def search(question, encoder, index, top_k=5):
    if not question.strip():
        raise ValueError("La question est vide.")
    vectors, chunks, manifest = index
    if encoder.model_id != manifest["model_id"] or encoder.revision != manifest["model_revision"]:
        raise ValueError("La question et les passages doivent utiliser le même modèle et la même révision.")
    query = encoder.encode([question.strip()], manifest["query_prefix"])[0]
    if top_k < 1:
        raise ValueError("Le nombre de résultats doit être positif.")
    semantic_hits = rank_passages(vectors, query, chunks, top_k)
    # Conserver le cosinus dans 'score' pour les diagnostics et la compatibilité.
    semantic_scores = vectors @ (query / np.linalg.norm(query))
    texts = tuple(chunk["contextualized_text"] for chunk in chunks)
    lexical_scores = cached_lexical_index(texts).scores(question)
    if not np.any(lexical_scores):
        return semantic_hits[:top_k]
    order, fusion_scores = hybrid_ranking(semantic_scores, lexical_scores, top_k)
    return [{
        "score": float(semantic_scores[i]), "retrieval_score": float(fusion_scores[i]),
        "lexical_score": float(lexical_scores[i]), "chunk": chunks[i],
    } for i in order]


def evaluate(encoder, index, top_k=5):
    questions = json.loads((ROOT / "data/evaluation_questions.json").read_text(encoding="utf-8"))
    results = []
    for item in questions:
        hits = search(item["question"], encoder, index, top_k)
        matched = any(
            hit["chunk"]["article_id"] in item["expected_articles"]
            and any(term.casefold() in hit["chunk"]["text"].casefold() for term in item["relevant_terms"])
            for hit in hits
        )
        results.append({**item, "matched": matched, "hits": hits})
        print(f"{'OK' if matched else 'À REVOIR'} — {item['question']}", flush=True)
    report = {
        "retrieval_method": "hybrid_bm25_phrase_rrf",
        "description": "Contrôle indicatif : article attendu et mot-clé pertinent dans un passage du top-k. Une relecture reste nécessaire.",
        "top_k": top_k, "matched": sum(item["matched"] for item in results),
        "total": len(results), "results": results,
    }
    (ROOT / "data/index/evaluation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(f"\nContrôle indicatif : {report['matched']}/{report['total']}. Détails : data/index/evaluation.json")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("build", help="Calculer les embeddings et enregistrer l'index.")
    query_parser = subparsers.add_parser("search", help="Afficher les passages proches d'une question.")
    query_parser.add_argument("question")
    query_parser.add_argument("--top-k", type=int, default=5)
    eval_parser = subparsers.add_parser("evaluate", help="Vérifier la recherche sur dix questions.")
    eval_parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    if getattr(args, "top_k", 1) < 1:
        parser.error("--top-k doit être positif.")
    try:
        if args.command == "build":
            build_index()
        else:
            index = load_index()
            manifest = index[2]
            encoder = Encoder(manifest["model_id"], manifest["model_revision"], offline=True)
            if args.command == "evaluate":
                evaluate(encoder, index, args.top_k)
            else:
                hits = search(args.question, encoder, index, args.top_k)
                for position, hit in enumerate(hits, 1):
                    chunk = hit["chunk"]
                    print(f"\n{position}. {chunk['title']}")
                    if "retrieval_score" in hit:
                        print(f"Classement hybride : {hit['retrieval_score']:.4f} ; cosinus : {hit['score']:.4f}")
                    else:
                        print(f"Cosinus : {hit['score']:.4f}")
                    print("Section : " + " > ".join(chunk["section_path"]))
                    print("Source : " + chunk["revision_url"])
                    print(chunk["text"])
                print("\nLes scores comparent la proximité des textes ; ce ne sont pas des probabilités de réponse correcte.")
    except (OSError, ValueError, KeyError, TypeError, ImportError, RuntimeError) as error:
        print(f"ERREUR — {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
