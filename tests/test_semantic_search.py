"""Vérifications mathématiques et de conservation du texte, sans modèle téléchargé."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

from scripts import semantic_search as semantic


def passage(text):
    return {
        "id": "soleil-test", "article_id": "soleil", "title": "Soleil",
        "section_path": ["Noyau"], "text": text, "char_start": 100,
        "char_end": 100 + len(text), "revision_id": 42,
        "revision_url": "https://fr.wikipedia.org/w/index.php?oldid=42",
    }


class SemanticTests(unittest.TestCase):
    def test_model_revision_must_be_pinned_before_loading(self):
        with self.assertRaisesRegex(ValueError, "commit précis"):
            semantic.Encoder(revision="main")

    def test_cosine_ranking_and_query_normalization(self):
        vectors = np.array([[0, 1], [-1, 0], [1, 0]], dtype=np.float32)
        chunks = [{"id": "perpendiculaire"}, {"id": "opposé"}, {"id": "proche"}]
        hits = semantic.rank_passages(vectors, [5, 0], chunks, 3)
        self.assertEqual([hit["chunk"]["id"] for hit in hits], ["proche", "perpendiculaire", "opposé"])
        np.testing.assert_allclose([hit["score"] for hit in hits], [1, 0, -1])

    def test_invalid_or_null_query_vectors_are_rejected(self):
        for query in ([0, 0], [float("nan"), 1], [1, 2, 3]):
            with self.assertRaises(ValueError):
                semantic.rank_passages(np.array([[1, 0]]), query, [{}])

    def test_invalid_index_vectors_are_rejected(self):
        for matrix in (np.array([[2, 0]]), np.array([[float("nan"), 0]]), np.zeros((2, 2))):
            with self.assertRaises(ValueError):
                semantic.validate_vectors(matrix, 1, 2)

    def test_oversized_passage_is_split_without_losing_text_or_sources(self):
        text = " ".join(f"Phrase {i} avec du contenu." for i in range(25))
        parent = passage(text)
        chunks = semantic.fit_chunks([parent], lambda value: len(value.split()), 30)
        self.assertGreater(len(chunks), 1)
        covered = set()
        for chunk in chunks:
            self.assertLessEqual(chunk["input_token_count"], 30)
            start, end = chunk["char_start"] - 100, chunk["char_end"] - 100
            self.assertEqual(chunk["text"], text[start:end])
            self.assertEqual(chunk["revision_url"], parent["revision_url"])
            self.assertEqual(chunk["parent_chunk_id"], parent["id"])
            covered.update(range(start, end))
        self.assertTrue(all(i in covered for i, char in enumerate(text) if not char.isspace()))

    def test_fitting_passage_keeps_its_id_and_text(self):
        parent = passage("Le Soleil produit de l'énergie.")
        chunks = semantic.fit_chunks([parent], lambda value: len(value.split()), 30)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["id"], parent["id"])
        self.assertEqual(chunks[0]["text"], parent["text"])

    def test_extremely_long_single_word_is_not_silently_truncated(self):
        parent = passage("x" * 300)
        chunks = semantic.fit_chunks([parent], len, 80)
        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunk["text"] for chunk in chunks), parent["text"])
        self.assertTrue(all(chunk["input_token_count"] <= 80 for chunk in chunks))

    def test_oversized_titles_are_rejected(self):
        parent = {**passage("Texte."), "title": "titre " * 50}
        with self.assertRaisesRegex(ValueError, "Titres trop longs"):
            semantic.fit_chunks([parent], lambda value: len(value.split()), 20)

    def test_query_cannot_use_another_model_revision(self):
        encoder = Mock(model_id=semantic.MODEL_ID, revision="autre-version")
        manifest = {"model_id": semantic.MODEL_ID, "model_revision": "version-indexée"}
        with self.assertRaisesRegex(ValueError, "même modèle"):
            semantic.search("Une question ?", encoder, (None, None, manifest))
        encoder.encode.assert_not_called()

    def test_changed_corpus_invalidates_the_index(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "index.npz"
            manifest = {
                "format_version": 1, "count": 1, "dimension": 2, "corpus_sha256": "ancien",
            }
            np.savez_compressed(
                path, embeddings=np.array([[1, 0]], dtype=np.float32),
                chunks=json.dumps([{"id": "soleil"}]), manifest=json.dumps(manifest),
            )
            with patch.object(semantic, "INDEX_PATH", path), patch.object(semantic, "corpus_signature", return_value="nouveau"):
                with self.assertRaisesRegex(ValueError, "corpus a changé"):
                    semantic.load_index()


if __name__ == "__main__":
    unittest.main()
