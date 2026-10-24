"""Vérifier l'interface sur un serveur lancé ; --live ajoute deux questions réelles."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


ROOT = Path(__file__).resolve().parents[1]


def mock_result():
    return {
        "question": "Question de test", "elapsed_seconds": 1.2,
        "answer": {"answerable": True, "statements": [{"text": "Exemple de test : le Soleil produit son énergie par fusion nucléaire.", "source_ids": [1]}]},
        "formatted_answer": "Exemple de test.",
        "retrieved_sources": [{
            "source_id": 1, "title": "Soleil", "section_path": ["Noyau"],
            "text": "Extrait de test : la fusion transforme l'hydrogène en hélium.",
            "revision_id": 240375314,
            "revision_url": "https://fr.wikipedia.org/w/index.php?oldid=240375314",
            "license": {"text": "CC BY-SA 4.0"},
        }],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--live", action="store_true", help="Tester une question puis une relance, soit trois appels Gemini.")
    args = parser.parse_args()
    output = ROOT / ".impeccable/review"
    output.mkdir(parents=True, exist_ok=True)
    results = {"live": args.live, "checks": []}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        console_errors = []
        page.on("pageerror", lambda error: console_errors.append(str(error)))
        page.goto(args.url, wait_until="networkidle")
        expect(page.get_by_role("textbox", name="Votre question sur l’astronomie")).to_be_enabled(timeout=120000)
        expect(page.get_by_role("heading", name="Une question sur l’Univers ?")).to_be_visible()
        results["checks"].append("Page chargée et saisie disponible")
        page.screenshot(path=str(output / "desktop-empty.png"), full_page=True)
        initial_status = page.request.get(args.url + "/api/status").json()

        page.route("**/api/chat", lambda route: route.fulfill(status=400, json={"error": "Quota Gemini atteint. Réessayez plus tard."}))
        textbox = page.get_by_role("textbox", name="Votre question sur l’astronomie")
        textbox.fill("Question de test")
        page.get_by_role("button", name="Envoyer la question", exact=True).click()
        expect(page.get_by_role("alert")).to_contain_text("Quota Gemini atteint")
        page.unroute("**/api/chat")
        page.route("**/api/chat", lambda route: route.fulfill(json=mock_result()))
        page.get_by_role("button", name="Réessayer cette question").click()
        expect(page.locator(".assistant-message")).to_contain_text("Exemple de test")
        expect(page.locator(".user-message")).to_have_count(1)
        page.get_by_role("button", name="Lire la source 1", exact=True).click()
        expect(page.locator(".source-body:not([hidden])")).to_contain_text("Extrait de test")
        expect(page.get_by_role("link", name="Ouvrir l’article sur Wikipédia")).to_have_attribute("href", "https://fr.wikipedia.org/w/index.php?oldid=240375314")
        results["checks"].append("Erreur, nouvel essai sans doublon et ouverture d’une source")

        page.get_by_role("button", name="Nouvelle discussion").click()
        expect(page.locator(".turn")).to_have_count(0)
        textbox.fill('<img src=x onerror="window.xssTriggered=true">')
        page.get_by_role("button", name="Envoyer la question", exact=True).click()
        expect(page.locator(".assistant-message")).to_be_visible()
        expect(page.locator(".user-message img")).to_have_count(0)
        assert page.evaluate("window.xssTriggered === undefined")
        page.reload(wait_until="networkidle")
        expect(textbox).to_be_enabled(timeout=30000)
        expect(page.locator(".turn")).to_have_count(0)
        assert page.evaluate("localStorage.length === 0 && sessionStorage.length === 0")
        results["checks"].append("Texte affiché sans exécution HTML et historique effacé à l’actualisation")
        page.unroute("**/api/chat")

        if args.live:
            textbox.fill("Comment le Soleil produit-il son énergie ?")
            with page.expect_response(lambda response: response.url.endswith("/api/chat"), timeout=180000) as first:
                page.get_by_role("button", name="Envoyer la question", exact=True).click()
            assert first.value.ok, first.value.text()
            expect(textbox).to_be_enabled(timeout=30000)
            expect(page.locator(".assistant-message").last).to_contain_text("fusion")
            textbox.fill("Et sa température ?")
            with page.expect_response(lambda response: response.url.endswith("/api/chat"), timeout=180000) as followup:
                page.get_by_role("button", name="Envoyer la question", exact=True).click()
            assert followup.value.ok, followup.value.text()
            result = followup.value.json()
            assert "soleil" in result["retrieval_question"].lower(), result["retrieval_question"]
            assert result["answer"]["answerable"]
            expect(textbox).to_be_enabled(timeout=30000)
            page.locator(".turn").last.locator(".citation").first.click()
            results["followup_question"] = result["retrieval_question"]
            results["followup_answer"] = result["answer"]
            results["checks"].append("Discussion réelle et résolution de « sa température » vers le Soleil")

        final_status = page.request.get(args.url + "/api/status").json()
        assert initial_status["model_loads"] == final_status["model_loads"] == 1
        results["model_loads"] = final_status["model_loads"]
        results["checks"].append("Un seul chargement du modèle pour toutes les questions")
        page.evaluate("window.scrollTo(0, 0)")
        page.screenshot(path=str(output / "desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.evaluate("window.scrollTo(0, 0)")
        expect(page.get_by_role("button", name="Nouvelle discussion")).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(output / "mobile.png"), full_page=True)
        results["checks"].append("Vue mobile sans débordement horizontal")
        assert not console_errors, console_errors
        results["console_errors"] = console_errors
        for name in ("desktop-empty.png", "desktop.png", "mobile.png"):
            (output / (name + ".json")).write_text(json.dumps({
                "origin": "Capture Playwright de l’interface locale AstroRAG, Microsoft Edge sans interface graphique.",
                "url": args.url, "live_answers": args.live and name != "desktop-empty.png",
            }, ensure_ascii=False, indent=2), encoding="utf-8")
        browser.close()
    (output / "browser-checks.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
