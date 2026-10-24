"""Vérifier le serveur et le contexte conversationnel sans appel à Gemini."""

import json
import unittest
from unittest.mock import Mock, patch

import app as web
from scripts import conversation


class ServiceTests(unittest.TestCase):
    def test_model_and_index_are_loaded_once_across_questions(self):
        index = (None, [{"article_id": "soleil"}], {"model_id": "test", "model_revision": "abc", "corpus_sha256": "signature"})
        loader = Mock(return_value=index)
        factory = Mock(return_value=Mock())
        service = web.RAGService(loader, factory)
        result = {"answer": {"answerable": True}}
        with patch.object(web, "corpus_signature", return_value="signature"), \
             patch.object(web, "get_api_key", return_value="test-secret"), \
             patch.object(web, "resolve_question", side_effect=lambda question, history, key: (question, {})), \
             patch.object(web, "answer_question", side_effect=lambda *args: dict(result)):
            service.ask("Question 1", [])
            service.ask("Question 2", [])
        loader.assert_called_once()
        factory.assert_called_once()
        self.assertEqual(service.load_count, 1)

    def test_concurrent_question_does_not_start_another_generation(self):
        service = web.RAGService()
        service.query_lock.acquire()
        try:
            with self.assertRaises(BlockingIOError):
                service.ask("Question", [])
        finally:
            service.query_lock.release()


class ConversationTests(unittest.TestCase):
    def test_first_question_needs_no_reformulation_call(self):
        post = Mock()
        question, usage = conversation.resolve_question("Le Soleil ?", [], "secret", post)
        self.assertEqual(question, "Le Soleil ?")
        self.assertEqual(usage, {})
        post.assert_not_called()

    def test_followup_is_resolved_from_bounded_history(self):
        history = [{"question": "Comment le Soleil produit-il son énergie ?", "answer": "Par fusion nucléaire."}]
        with patch.object(conversation, "request_json", return_value=({"standalone_question": "Quelle est la température du Soleil ?"}, {"promptTokenCount": 100})) as request:
            resolved, usage = conversation.resolve_question("Et sa température ?", history, "secret")
        self.assertIn("Soleil", resolved)
        payload = json.loads(request.call_args.args[0]["contents"][0]["parts"][0]["text"])
        self.assertEqual(payload["history"], history)
        self.assertEqual(payload["question"], "Et sa température ?")

    def test_long_or_malformed_history_is_rejected(self):
        for history in ([{}], [{"question": "a", "answer": "b"}] * 4, "texte"):
            with self.assertRaises(ValueError):
                conversation.validate_history(history)


class EndpointTests(unittest.TestCase):
    def setUp(self):
        self.service = Mock()
        self.service.status.return_value = {"state": "ready", "articles": 20, "passages": 1174}
        self.service.ask.return_value = {"question": "Question", "answer": {"answerable": False, "statements": []}}
        self.client = web.create_app(self.service).test_client()

    def test_page_assets_and_status_are_served_without_key(self):
        with self.client.get("/") as page:
            self.assertEqual(page.status_code, 200)
        with self.client.get("/static/app.js") as script:
            self.assertEqual(script.status_code, 200)
        status = self.client.get("/api/status")
        self.assertEqual(status.json["articles"], 20)
        self.assertNotIn("GEMINI_API_KEY", status.get_data(as_text=True))
        self.assertEqual(self.client.get("/.env").status_code, 404)

    def test_question_and_history_reach_the_service(self):
        history = [{"question": "Le Soleil ?", "answer": "Une étoile."}]
        result = self.client.post("/api/chat", json={"question": " Et sa température ? ", "history": history})
        self.assertEqual(result.status_code, 200)
        self.service.ask.assert_called_once_with("Et sa température ?", history)

    def test_invalid_questions_and_foreign_origins_are_rejected(self):
        self.assertEqual(self.client.post("/api/chat", json={"question": " "}).status_code, 400)
        self.assertEqual(self.client.post("/api/chat", json={"question": "x" * 1001}).status_code, 400)
        self.assertEqual(self.client.post("/api/chat", data="question=x").status_code, 415)
        self.assertEqual(self.client.post("/api/chat", json={"question": "Question"}, headers={"Origin": "https://example.com"}).status_code, 403)
        self.service.ask.assert_not_called()

    def test_expected_error_is_shown_without_traceback(self):
        self.service.ask.side_effect = ValueError("Quota Gemini atteint.")
        result = self.client.post("/api/chat", json={"question": "Question"})
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.json["error"], "Quota Gemini atteint.")


if __name__ == "__main__":
    unittest.main()
