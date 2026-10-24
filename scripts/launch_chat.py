"""Ouvrir le chat par double clic, en réutilisant un serveur déjà démarré."""

import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener
import webbrowser


ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:8000"
LOCAL_HTTP = build_opener(ProxyHandler({}))


def chat_is_running():
    try:
        with LOCAL_HTTP.open(URL + "/api/status", timeout=1) as response:
            status = json.load(response)
        return isinstance(status, dict) and {"state", "model_loads", "passages", "articles"} <= status.keys()
    except (OSError, URLError, ValueError):
        return False


def open_chat():
    if not webbrowser.open(URL):
        print(f"Ouvre le chat dans ton navigateur : {URL}", flush=True)


def main():
    if chat_is_running():
        open_chat()
        return 0

    print("Démarrage d’AstroRAG… Le navigateur va s’ouvrir automatiquement.", flush=True)
    print("Garde cette fenêtre ouverte. Pour arrêter le chat : Ctrl+C.", flush=True)
    process = subprocess.Popen([sys.executable, str(ROOT / "app.py")], cwd=ROOT)
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if process.poll() is not None:
                print("Le démarrage a échoué. Consulte le message ci-dessus.", flush=True)
                return 1
            if chat_is_running():
                open_chat()
                return process.wait()
            time.sleep(0.3)
        print("Le démarrage prend du temps. Une fois prêt, ouvre " + URL, flush=True)
        return process.wait()
    except KeyboardInterrupt:
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()


if __name__ == "__main__":
    sys.exit(main())
