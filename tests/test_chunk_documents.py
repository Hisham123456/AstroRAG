"""Vérifier que le découpage conserve le texte, le contexte et les sources."""

import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from scripts import chunk_documents as chunker


def article(text):
    return {
        "id": "soleil", "title": "Soleil", "text": text,
        "url": "https://fr.wikipedia.org/wiki/Soleil", "theme": "Système solaire",
        "language": "fr", "page_id": 12, "revision_id": 42,
        "revision_url": "https://fr.wikipedia.org/w/index.php?oldid=42",
        "revision_timestamp": "2026-10-01T00:00:00Z",
        "retrieved_at": "2026-10-24T00:00:00Z", "cleaner_version": 1,
        "license": {"text": "CC BY-SA", "url": "https://creativecommons.org/licenses/by-sa/4.0/"},
        "attribution": {"authors": "Contributeurs de Wikipédia"},
    }


class ChunkTests(unittest.TestCase):
    def test_section_hierarchy_and_introduction(self):
        text = "Un astre.\n\n## Structure\n\nUn noyau.\n\n### Composition\n\nDu gaz.\n\n## Observation\n\nDes instruments."
        paths = [path for _, _, path in chunker.sections(text)]
        self.assertEqual(paths, [
            ["Introduction"], ["Structure"], ["Structure", "Composition"], ["Observation"],
        ])

    def test_exact_text_coverage_and_traceability(self):
        text = "\n\n".join(f"Phrase {i} au sujet de notre étoile." for i in range(30))
        doc = article(text)
        chunks = chunker.chunk_article(doc, chunk_size=25, overlap=8)
        covered = set()
        for chunk in chunks:
            start, end = chunk["char_start"], chunk["char_end"]
            self.assertEqual(chunk["text"], text[start:end])
            self.assertLessEqual(chunk["word_count"], 25)
            self.assertLessEqual(chunk["overlap_word_count"], 8)
            self.assertIn("Article : Soleil", chunk["contextualized_text"])
            self.assertEqual(chunk["revision_id"], 42)
            self.assertEqual(chunk["license"], doc["license"])
            covered.update(range(start, end))
        self.assertTrue(all(i in covered for i, char in enumerate(text) if not char.isspace()))

    def test_overlap_repeats_whole_sentences(self):
        text = "Alpha brille très fort. Bêta brille très fort. Gamma brille très fort. Delta brille très fort."
        chunks = chunker.chunk_article(article(text), chunk_size=12, overlap=4)
        self.assertEqual(chunks[1]["overlap_word_count"], 4)
        self.assertTrue(chunks[1]["text"].startswith("Gamma brille très fort."))
        self.assertFalse(any(chunk["hard_split"] for chunk in chunks))

    def test_never_mixes_sections_or_drops_a_short_section(self):
        chunks = chunker.chunk_article(article("## Noyau\n\nFusion nucléaire.\n\n## Surface\n\nLumière visible."))
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["section_path"], ["Noyau"])
        self.assertEqual(chunks[1]["section_path"], ["Surface"])
        self.assertEqual(chunks[1]["overlap_word_count"], 0)
        self.assertNotIn("Fusion", chunks[1]["text"])

    def test_very_long_sentence_has_bounded_size_and_makes_progress(self):
        text = " ".join(f"mot{i}" for i in range(47))
        chunks = chunker.chunk_article(article(text), chunk_size=10, overlap=3)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(chunks[0]["hard_split"])
        self.assertEqual(chunks[-1]["char_end"], len(text))
        self.assertTrue(all(chunk["word_count"] <= 10 for chunk in chunks))
        self.assertEqual(len({chunk["id"] for chunk in chunks}), len(chunks))

    def test_ids_are_repeatable_and_change_with_revision(self):
        doc = article("Le Soleil est une étoile.")
        first = chunker.chunk_article(doc)
        self.assertEqual(first, chunker.chunk_article(doc))
        changed = chunker.chunk_article({**doc, "revision_id": 43})
        self.assertNotEqual(first[0]["id"], changed[0]["id"])

    def test_abbreviation_does_not_create_a_sentence_boundary(self):
        text = "M. Hubble observe des galaxies. Une autre phrase suit."
        words = list(re.finditer(r"\S+", text))
        _, boundaries = chunker.boundary_indices(text, words)
        self.assertNotIn(1, boundaries)
        self.assertIn(5, boundaries)

    def test_invalid_parameters_are_rejected(self):
        for size, overlap in [(0, 0), (10, 10), (10, -1)]:
            with self.assertRaises(ValueError):
                chunker.chunk_article(article("Texte."), size, overlap)

    def test_missing_article_does_not_replace_previous_output(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            (root / "data/chunks").mkdir(parents=True)
            source = {"id": "soleil", "title": "Soleil"}
            (root / "data/sources.json").write_text(json.dumps([source]), encoding="utf-8")
            output = root / "data/chunks/chunks.json"
            output.write_text("ANCIEN RÉSULTAT", encoding="utf-8")
            with patch.object(chunker, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "Article manquant"):
                    chunker.build_corpus()
            self.assertEqual(output.read_text(encoding="utf-8"), "ANCIEN RÉSULTAT")


if __name__ == "__main__":
    unittest.main()
