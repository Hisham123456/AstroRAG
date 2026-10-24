"""Lancer l'interface locale : python app.py, puis http://127.0.0.1:8000."""

import argparse
from pathlib import Path
import threading
import time

from flask import Flask, jsonify, request, send_from_directory

from scripts.answer_question import answer_question, get_api_key
from scripts.conversation import resolve_question, validate_history
from scripts.semantic_search import Encoder, corpus_signature, load_index


ROOT = Path(__file__).resolve().parent


class RAGService:
    """Un index et un modèle partagés, chargés une fois pour ce serveur."""

    def __init__(self, index_loader=load_index, encoder_factory=Encoder):
        self.index_loader = index_loader
        self.encoder_factory = encoder_factory
        self.load_lock = threading.Lock()
        self.query_lock = threading.Lock()
        self.index = None
        self.encoder = None
        self.state = "loading"
        self.error = ""
        self.load_count = 0

    def warm_up(self):
        try:
            self.get_resources()
        except (OSError, ValueError, KeyError, TypeError, ImportError, RuntimeError):
            self.state = "error"
            self.error = "La préparation a échoué. Vérifie que l’index a été construit, puis redémarre l’application."

    def get_resources(self):
        with self.load_lock:
            if self.encoder is None:
                index = self.index_loader()
                manifest = index[2]
                encoder = self.encoder_factory(manifest["model_id"], manifest["model_revision"], offline=True)
                self.index, self.encoder = index, encoder
                self.load_count += 1
                self.state = "ready"
            return self.encoder, self.index

    def status(self):
        state, message = self.state, self.error
        try:
            get_api_key()
        except ValueError:
            state = "error"
            message = "Renseigne la clé Gemini dans le fichier .env, puis redémarre l’application."
        chunks = self.index[1] if self.index is not None else []
        return {
            "state": state, "message": message,
            "articles": len({chunk["article_id"] for chunk in chunks}),
            "passages": len(chunks),
            "model_loads": self.load_count,
        }

    def ask(self, question, history):
        # Une requête à la fois : pas de double appel Gemini ni d'inférence concurrente.
        if not self.query_lock.acquire(blocking=False):
            raise BlockingIOError("Une réponse est déjà en cours. Attendez qu’elle soit terminée.")
        try:
            encoder, index = self.get_resources()
            if corpus_signature() != index[2]["corpus_sha256"]:
                raise ValueError("Le corpus a changé. Redémarrez l’application pour charger le nouvel index.")
            key = get_api_key()
            started = time.monotonic()
            resolved, rewrite_usage = resolve_question(question, history, key)
            result = answer_question(resolved, encoder, index, key)
            # L'historique sert à trouver le sujet, seuls les passages étayent les faits.
            result["question"] = question
            result["retrieval_question"] = resolved
            result["rewrite_usage"] = rewrite_usage
            result["elapsed_seconds"] = round(time.monotonic() - started, 1)
            return result
        finally:
            self.query_lock.release()


def create_app(service=None):
    app = Flask(__name__, static_folder=str(ROOT / "web"), static_url_path="/static")
    app.config.update(MAX_CONTENT_LENGTH=24000, TRUSTED_HOSTS=["127.0.0.1", "localhost"])
    service = service if service is not None else RAGService()
    app.extensions["rag_service"] = service

    @app.after_request
    def response_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        return response

    @app.get("/")
    def home():
        return send_from_directory(ROOT / "web", "index.html")

    @app.get("/api/status")
    def status():
        return jsonify(service.status())

    @app.post("/api/chat")
    def chat():
        # Seule l'interface locale envoie du JSON ; aucune clé n'entre dans le navigateur.
        origin = request.headers.get("Origin")
        if origin and origin != request.host_url.rstrip("/"):
            return jsonify(error="Cette requête ne vient pas de l’interface locale."), 403
        if not request.is_json:
            return jsonify(error="Une requête JSON est attendue."), 415
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error="La question est invalide."), 400
        question = data.get("question")
        if not isinstance(question, str) or not 0 < len(question.strip()) <= 1000:
            return jsonify(error="Écris une question de 1 à 1 000 caractères."), 400
        try:
            history = validate_history(data.get("history", []))
            result = service.ask(question.strip(), history)
            return jsonify(result)
        except BlockingIOError as error:
            return jsonify(error=str(error)), 409
        except (ValueError, FileNotFoundError) as error:
            return jsonify(error=str(error)), 400
        except (OSError, KeyError, TypeError, ImportError, RuntimeError):
            return jsonify(error="La réponse n’a pas pu être préparée. Vérifie l’index et réessaie."), 500

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error="La question ou l’historique est trop long. Commence une nouvelle discussion."), 413

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Le port doit être compris entre 1 et 65535.")
    app = create_app()
    threading.Thread(target=app.extensions["rag_service"].warm_up, daemon=True).start()
    print(f"AstroRAG : http://127.0.0.1:{args.port} — Ctrl+C pour arrêter.", flush=True)
    app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()
