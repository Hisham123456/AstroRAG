"""Éviter de manquer une réponse explicite à cause du seul classement vectoriel."""

import unittest
from unittest.mock import Mock

import numpy as np

from scripts.semantic_search import LexicalIndex, lexical_tokens, search


class HybridSearchTests(unittest.TestCase):
    def test_accents_and_simple_plurals_match_without_losing_comparisons(self):
        self.assertEqual(lexical_tokens("Quelle planète est la plus proche du Soleil ?"),
                         lexical_tokens("Quelles planètes sont les plus proches du soleil ?"))
        self.assertIn("plus", lexical_tokens("la plus proche"))
        self.assertIn("moins", lexical_tokens("la moins proche"))

    def test_ordered_relation_beats_scattered_mentions(self):
        index = LexicalIndex([
            "Mercure est la planète la plus proche du Soleil.",
            "Une planète peut être proche d'une étoile. Le Soleil est une étoile et possède plusieurs planètes.",
            "Neptune est la planète la plus éloignée du Soleil.",
        ])
        closest = index.scores("Quelle est la planète la plus proche du Soleil ?")
        farthest = index.scores("Quelle est la planète la plus éloignée du Soleil ?")
        self.assertEqual(int(np.argmax(closest)), 0)
        self.assertEqual(int(np.argmax(farthest)), 2)

    def test_explicit_answer_outside_semantic_top_five_is_recovered(self):
        angles = np.linspace(0, 0.8, 30)
        vectors = np.column_stack([np.cos(angles), np.sin(angles)]).astype(np.float32)
        chunks = [{"id": str(i), "text": "Exploration et missions spatiales.",
                   "contextualized_text": "Exploration et missions spatiales."} for i in range(30)]
        chunks[17] = {"id": "explicit", "text": "Mercure est la planète la plus proche du Soleil.",
                      "contextualized_text": "Mercure est la planète la plus proche du Soleil."}
        encoder = Mock(model_id="test", revision="version")
        encoder.encode.return_value = np.array([[1, 0]], dtype=np.float32)
        index = (vectors, chunks, {"model_id": "test", "model_revision": "version", "query_prefix": "query: "})
        hits = search("Quelle est la planète la plus proche du Soleil ?", encoder, index, 5)
        self.assertIn("explicit", [hit["chunk"]["id"] for hit in hits])
        self.assertTrue(all("retrieval_score" in hit for hit in hits))

    def test_no_keyword_match_preserves_semantic_ranking(self):
        vectors = np.array([[0, 1], [1, 0]], dtype=np.float32)
        chunks = [{"id": "other", "contextualized_text": "Texte premier"},
                  {"id": "nearest", "contextualized_text": "Texte second"}]
        encoder = Mock(model_id="test", revision="version")
        encoder.encode.return_value = np.array([[1, 0]], dtype=np.float32)
        index = (vectors, chunks, {"model_id": "test", "model_revision": "version", "query_prefix": "query: "})
        self.assertEqual(search("zzzinconnu", encoder, index, 1)[0]["chunk"]["id"], "nearest")


if __name__ == "__main__":
    unittest.main()
