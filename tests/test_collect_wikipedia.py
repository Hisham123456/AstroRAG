"""Vérifications hors ligne du nettoyage et de la collecte."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import collect_wikipedia as collector


SOURCE = {
    "id": "soleil", "title": "Soleil",
    "url": "https://fr.wikipedia.org/wiki/Soleil", "theme": "Système solaire",
}


class CleaningTests(unittest.TestCase):
    def test_preserves_inline_words_headings_and_removes_noise(self):
        html = """
        <div class="hatnote"><p>Page d'homonymie</p></div>
        <p>Le <b>Soleil</b> est une étoile<sup class="reference">[1]</sup>.</p>
        <h2>Structure<span class="mw-editsection">modifier</span></h2>
        <p>Son cœur produit de l'énergie.</p>
        <table><tr><td><p>Information tabulaire</p></td></tr></table>
        <figure><p>Légende de photo</p></figure>
        <h2>Notes et références</h2><p>Référence bibliographique</p>
        <h3>Détails des références</h3><p>Autre référence</p>
        <h2>Observation</h2><p>Observer avec précaution.</p>
        """
        text = collector.clean_html(html)
        self.assertIn("Le Soleil est une étoile.", text)
        self.assertIn("## Structure", text)
        self.assertIn("## Observation", text)
        for noise in ("homonymie", "[1]", "modifier", "tabulaire", "Légende", "référence"):
            self.assertNotIn(noise, text)

    def test_preserves_formula_once_and_does_not_duplicate_nested_lists(self):
        html = """
        <p>Énergie : <span class="mwe-math-mathml">DOUBLON</span>
        <img class="mwe-math-fallback-image-inline" alt="E=mc²"></p>
        <ul><li>Planètes<ul><li>Mars</li></ul></li></ul>
        """
        text = collector.clean_html(html)
        self.assertIn("E=mc²", text)
        self.assertNotIn("DOUBLON", text)
        self.assertEqual(text.count("Mars"), 1)


class CollectionTests(unittest.TestCase):
    @patch.object(collector, "api_get")
    def test_fetch_uses_the_exact_revision_and_canonical_title(self, api):
        api.side_effect = [
            {"query": {"pages": [{
                "ns": 0, "title": "Soleil", "pageid": 12,
                "fullurl": SOURCE["url"],
                "revisions": [{"revid": 42, "timestamp": "2026-10-01T00:00:00Z"}],
            }]}},
            {"parse": {"revid": 42, "text": "<p>Une étoile.</p>"}},
        ]
        article = collector.fetch_article(Mock(), {**SOURCE, "title": "Le Soleil"}, {"text": "CC BY-SA"})
        self.assertEqual(api.call_args.kwargs["oldid"], 42)
        self.assertEqual(article["revision_id"], 42)
        self.assertEqual(article["title"], "Soleil")
        self.assertIn("oldid=42", article["revision_url"])

    @patch.object(collector, "api_get")
    def test_disambiguation_is_rejected(self, api):
        api.return_value = {"query": {"pages": [{
            "ns": 0, "title": "Mars", "pageprops": {"disambiguation": ""},
        }]}}
        with self.assertRaisesRegex(ValueError, "article précis"):
            collector.fetch_article(Mock(), SOURCE, {})

    @patch.object(collector.time, "sleep")
    def test_rate_limit_retries_then_returns_data(self, sleep):
        session = Mock()
        limited, success = Mock(), Mock()
        limited.status_code = 429
        limited.headers = {"Retry-After": "2"}
        success.status_code = 200
        success.json.return_value = {"query": {}}
        session.get.side_effect = [limited, success]
        self.assertEqual(collector.api_get(session, action="query"), {"query": {}})
        self.assertEqual(session.get.call_count, 2)
        sleep.assert_any_call(2.0)

    @patch.object(collector, "api_get")
    def test_cached_html_can_be_reprocessed_without_network(self, api):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            article = {
                "source": SOURCE, "page_id": 12, "revision_id": 42,
                "html": "<p>Le Soleil est une étoile. </p>" * 30,
            }
            collector.write_json(root / "data/raw/soleil.json", article)
            with patch.object(collector, "ROOT", root):
                self.assertEqual(collector.collect([SOURCE]), 0)
            api.assert_not_called()
            processed = json.loads((root / "data/processed/soleil.json").read_text(encoding="utf-8"))
            self.assertEqual(processed["revision_id"], 42)
            self.assertNotIn("html", processed)
            self.assertGreater(processed["character_count"], 500)

    @patch.object(collector, "api_get", side_effect=ValueError("Page inaccessible"))
    def test_failed_download_returns_failure_and_writes_report(self, api):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            with patch.object(collector, "ROOT", root):
                self.assertEqual(collector.collect([SOURCE]), 1)
            report = json.loads((root / "data/collection_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["results"][0]["status"], "error")
            self.assertFalse((root / "data/processed/soleil.json").exists())


if __name__ == "__main__":
    unittest.main()
