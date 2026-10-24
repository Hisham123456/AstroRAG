"""Contrôler les citations, l'abstention et les erreurs sans appeler Gemini."""

import json
import unittest
from unittest.mock import Mock, patch

import requests

from scripts import answer_question as rag


def source(number=1):
    return {
        "source_id": number, "chunk_id": f"soleil-{number}", "article_id": "soleil",
        "title": "Soleil", "section_path": ["Noyau"],
        "text": "L'énergie du Soleil provient de la fusion de l'hydrogène en hélium.",
        "url": "https://fr.wikipedia.org/wiki/Soleil", "revision_id": 42,
        "revision_url": "https://fr.wikipedia.org/w/index.php?oldid=42",
        "license": {"text": "CC BY-SA"}, "attribution": {"authors": "Wikipédia"},
        "score": 0.88,
    }


def answer():
    return {"answerable": True, "statements": [{
        "text": "Le Soleil produit de l'énergie par fusion nucléaire.", "source_ids": [1],
    }]}


def response(payload=None, finish="STOP", status=200):
    result = Mock(status_code=status)
    result.json.return_value = {
        "candidates": [{"finishReason": finish, "content": {"parts": [
            {"text": json.dumps(payload if payload is not None else answer())},
        ]}}],
        "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 30},
    }
    return result


class AnswerTests(unittest.TestCase):
    def test_references_must_point_to_a_transmitted_passage(self):
        bad = answer()
        bad["statements"][0]["source_ids"] = [99]
        with self.assertRaisesRegex(ValueError, "passages transmis"):
            rag.validate_answer(bad, [source()])

    def test_each_statement_needs_an_integer_reference(self):
        for refs in ([], [True], [1.0], ["1"]):
            bad = answer()
            bad["statements"][0]["source_ids"] = refs
            with self.assertRaises(ValueError):
                rag.validate_answer(bad, [source()])

    def test_model_cannot_add_its_own_links_or_citations(self):
        for text in ("Une affirmation [99]", "Voir https://example.com", "Voir [source](url)"):
            bad = answer()
            bad["statements"][0]["text"] = text
            with self.assertRaises(ValueError):
                rag.validate_answer(bad, [source()])

    def test_abstention_is_consistent_and_has_no_invented_explanation(self):
        absent = {"answerable": False, "statements": []}
        self.assertEqual(rag.format_answer(absent, [source()]), rag.NO_ANSWER)
        with self.assertRaises(ValueError):
            rag.validate_answer({"answerable": False, "statements": answer()["statements"]}, [source()])

    def test_only_cited_sources_are_displayed(self):
        rendered = rag.format_answer(answer(), [source(), {**source(2), "title": "Autre source"}])
        self.assertIn("[1]", rendered)
        self.assertIn(source()["revision_url"], rendered)
        self.assertNotIn("Autre source", rendered)

    def test_api_key_is_in_header_not_url_or_prompt(self):
        post = Mock(return_value=response())
        result, usage = rag.generate_answer("D'où vient l'énergie solaire ?", [source()], "cle-privee-test", post)
        args, kwargs = post.call_args
        self.assertEqual(kwargs["headers"]["x-goog-api-key"], "cle-privee-test")
        self.assertNotIn("cle-privee-test", args[0])
        self.assertNotIn("cle-privee-test", json.dumps(kwargs["json"]))
        self.assertEqual(result, answer())
        self.assertEqual(usage["promptTokenCount"], 100)

    def test_quota_errors_do_not_trigger_automatic_retries(self):
        post = Mock(return_value=response(status=429))
        with self.assertRaisesRegex(ValueError, "Quota Gemini"):
            rag.generate_answer("Question", [source()], "cle-privee-test", post)
        post.assert_called_once()

    def test_temporary_unavailability_is_reported_without_retry(self):
        post = Mock(return_value=response(status=503))
        with self.assertRaisesRegex(ValueError, "temporairement indisponible"):
            rag.generate_answer("Question", [source()], "cle-privee-test", post)
        post.assert_called_once()

    def test_network_error_does_not_expose_request_details(self):
        post = Mock(side_effect=requests.ConnectionError("Détail privé : cle-privee-test"))
        with self.assertRaises(ValueError) as caught:
            rag.generate_answer("Question", [source()], "cle-privee-test", post)
        self.assertNotIn("cle-privee-test", str(caught.exception))

    def test_truncated_answers_are_not_displayed(self):
        post = Mock(return_value=response(finish="MAX_TOKENS"))
        with self.assertRaisesRegex(ValueError, "interrompu"):
            rag.generate_answer("Question", [source()], "cle-privee-test", post)

    def test_thought_parts_are_not_mixed_with_the_answer(self):
        result = response()
        result.json.return_value["candidates"][0]["content"]["parts"].insert(0, {
            "thought": True, "text": "Texte interne qui n'est pas du JSON.",
        })
        generated, _ = rag.generate_answer("Question", [source()], "cle-privee-test", Mock(return_value=result))
        self.assertEqual(generated, answer())

    def test_full_flow_uses_retrieved_sources_and_keeps_attribution(self):
        chunk = {**source(), "id": "soleil-1"}
        hits = [{"score": 0.88, "chunk": chunk}]
        with patch.object(rag, "search", return_value=hits):
            result = rag.answer_question("Question", Mock(), Mock(), "cle-privee-test", post=Mock(return_value=response()))
        self.assertEqual(result["model"], "gemini-3.5-flash-lite")
        self.assertEqual(result["retrieved_sources"][0]["attribution"], source()["attribution"])
        self.assertNotIn("cle-privee-test", json.dumps(result))

    def test_no_passages_produces_abstention_without_an_api_call(self):
        post = Mock()
        with patch.object(rag, "search", return_value=[]):
            result = rag.answer_question("Question", Mock(), Mock(), "cle-privee-test", post=post)
        self.assertFalse(result["answer"]["answerable"])
        post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
