"""Récupérer les articles de sources.json via l'API Wikipédia, puis les nettoyer."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
API_URL = "https://fr.wikipedia.org/w/api.php"
USER_AGENT = "AstroRAG/0.1 (https://github.com/Hisham123456/AstroRAG)"
CLEANER_VERSION = 1


def api_get(session, **params):
    """Effectuer une requête avec délai maximal et trois essais au plus."""
    for attempt in range(3):
        # Les appels restent séquentiels, espacés d'au moins une seconde.
        time.sleep(1)
        try:
            response = session.get(
                API_URL,
                params={"format": "json", "formatversion": 2, "maxlag": 5, **params},
                timeout=(10, 60),
            )
            if response.status_code in (429, 502, 503, 504) and attempt < 2:
                retry_after = response.headers.get("Retry-After", "")
                delay = float(retry_after) if retry_after.isdigit() else 5 * (attempt + 1)
                time.sleep(delay)
                continue
            response.raise_for_status()
            data = response.json()
            error = data.get("error")
            if error:
                if error.get("code") in ("maxlag", "ratelimited") and attempt < 2:
                    time.sleep(5 * (attempt + 1))
                    continue
                raise ValueError(f"API : {error.get('code')} — {error.get('info')}")
            return data
        except (requests.ConnectionError, requests.Timeout):
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))
    raise ValueError("L'API n'a pas répondu après trois essais.")


def load_sources():
    """Vérifier la liste avant de contacter Wikipédia ou d'écrire des fichiers."""
    sources = json.loads((ROOT / "data/sources.json").read_text(encoding="utf-8"))
    if not isinstance(sources, list) or not sources:
        raise ValueError("sources.json doit contenir une liste non vide.")
    seen_ids, seen_titles = set(), set()
    for source in sources:
        for field in ("id", "title", "url", "theme"):
            if not isinstance(source.get(field), str) or not source[field].strip():
                raise ValueError(f"Champ absent ou vide : {field}")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", source["id"]):
            raise ValueError(f"Identifiant invalide : {source['id']}")
        if not source["url"].startswith("https://fr.wikipedia.org/wiki/"):
            raise ValueError(f"URL invalide : {source['url']}")
        if source["id"] in seen_ids or source["title"] in seen_titles:
            raise ValueError(f"Source en double : {source['title']}")
        seen_ids.add(source["id"])
        seen_titles.add(source["title"])
    return sources


def fetch_article(session, source, license_info):
    """Résoudre les redirections, puis télécharger une révision déterminée."""
    query = api_get(
        session, action="query", titles=source["title"], redirects=1,
        prop="info|pageprops|revisions", inprop="url", rvprop="ids|timestamp",
        rvlimit=1,
    )["query"]
    page = query["pages"][0]
    if "missing" in page or "invalid" in page:
        raise ValueError(f"Page introuvable : {source['title']}")
    if page.get("ns") != 0 or "disambiguation" in page.get("pageprops", {}):
        raise ValueError(f"Cette page n'est pas un article précis : {source['title']}")
    revision = page["revisions"][0]
    parsed = api_get(
        session, action="parse", oldid=revision["revid"],
        prop="text|revid", disableeditsection=1,
    )["parse"]
    if parsed["revid"] != revision["revid"]:
        raise ValueError("La révision reçue ne correspond pas à la révision demandée.")
    return {
        "id": source["id"],
        "source": source,
        "title": page["title"],
        "url": page["fullurl"],
        "theme": source["theme"],
        "language": "fr",
        "page_id": page["pageid"],
        "revision_id": revision["revid"],
        "revision_timestamp": revision["timestamp"],
        "revision_url": f"https://fr.wikipedia.org/w/index.php?oldid={revision['revid']}",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "license": license_info,
        "attribution": {
            "authors": "Contributeurs et contributrices de Wikipédia",
            "history_url": f"https://fr.wikipedia.org/w/index.php?curid={page['pageid']}&action=history",
            "changes": "Texte extrait du HTML et nettoyé ; tableaux et illustrations exclus.",
        },
        "html": parsed["text"],
    }


def clean_html(html):
    """Garder les titres, paragraphes et listes du corps de l'article."""
    soup = BeautifulSoup(html, "html.parser")
    for element in soup.select(
        "script, style, table, figure, .thumb, .infobox, .navbox, .navigation, "
        ".bandeau-container, .bandeau, .hatnote, .homonymie, .metadata, "
        ".mw-editsection, .reference, .references, .reflist, .mw-references-wrap, "
        ".toc, #toc, .noprint, .printfooter, .catlinks, .mw-empty-elt"
    ):
        element.decompose()
    # Les formules affichées sous forme d'images conservent leur texte alternatif.
    for image in soup.find_all("img"):
        image.replace_with(image.get("alt", "") if "mwe-math-fallback-image-inline" in image.get("class", []) else "")
    for element in soup.select(".mwe-math-mathml"):
        element.decompose()

    end_sections = {
        "notes", "références", "notes et références", "voir aussi", "annexes",
        "bibliographie", "liens externes", "articles connexes",
    }
    blocks = []
    skipped_level = None
    for element in soup.find_all(["h2", "h3", "h4", "h5", "h6", "p", "li"]):
        # Une liste imbriquée sera lue dans son bloc parent, sans duplication.
        if element.find_parent(["li", "p"]):
            continue
        text = re.sub(r"\s+", " ", element.get_text()).strip()
        if not text:
            continue
        is_heading = element.name.startswith("h")
        if is_heading:
            level = int(element.name[1])
            if skipped_level is not None and level <= skipped_level:
                skipped_level = None
            if text.casefold() in end_sections:
                skipped_level = level
        if skipped_level is not None:
            continue
        if is_heading:
            text = "#" * int(element.name[1]) + " " + text
        elif element.name == "li":
            text = "- " + text
        blocks.append(text)
    return "\n\n".join(blocks)


def write_json(path, data):
    """Remplacer le fichier seulement lorsque son écriture est terminée."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def collect(sources, refresh=False):
    results = []
    license_info = None
    seen_pages = set()
    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})
        for number, source in enumerate(sources, 1):
            print(f"[{number}/{len(sources)}] {source['title']}", flush=True)
            raw_path = ROOT / "data/raw" / f"{source['id']}.json"
            try:
                cached = False
                if raw_path.exists() and not refresh:
                    article = json.loads(raw_path.read_text(encoding="utf-8"))
                    cached = article.get("source") == source and bool(article.get("html"))
                if not cached:
                    if license_info is None:
                        license_info = api_get(
                            session, action="query", meta="siteinfo", siprop="rightsinfo",
                        )["query"]["rightsinfo"]
                        if not license_info.get("url") or not license_info.get("text"):
                            raise ValueError("Informations de licence manquantes.")
                    article = fetch_article(session, source, license_info)
                    write_json(raw_path, article)
                if article["page_id"] in seen_pages:
                    raise ValueError("Deux sources pointent vers le même article.")
                text = clean_html(article["html"])
                if len(text) < 500:
                    raise ValueError("Texte vide ou trop court : vérifier l'article et le nettoyage.")
                processed = {key: value for key, value in article.items() if key != "html"}
                processed.update({"text": text, "character_count": len(text), "cleaner_version": CLEANER_VERSION})
                write_json(ROOT / "data/processed" / f"{source['id']}.json", processed)
                seen_pages.add(article["page_id"])
                status = "cache" if cached else "downloaded"
                results.append({"id": source["id"], "status": status, "characters": len(text)})
                print(f"  OK — {len(text):,} caractères ({status})", flush=True)
            except (requests.RequestException, ValueError, KeyError, IndexError, TypeError, OSError) as error:
                results.append({"id": source["id"], "status": "error", "error": str(error)})
                print(f"  ERREUR — {error}", file=sys.stderr, flush=True)
    write_json(ROOT / "data/collection_report.json", {
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "selected_count": len(sources), "results": results,
    })
    failures = sum(result["status"] == "error" for result in results)
    print(f"\nBilan : {len(results) - failures}/{len(sources)} articles prêts, {failures} erreur(s).")
    print("Détails : data/collection_report.json")
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, help="Traiter seulement les N premières sources.")
    parser.add_argument("--refresh", action="store_true", help="Retélécharger les articles au lieu d'utiliser le cache.")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit doit être supérieur ou égal à 1.")
    try:
        sources = load_sources()
        return collect(sources[:args.limit], args.refresh)
    except (ValueError, OSError) as error:
        print(f"ERREUR — {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCollecte interrompue. Relancez la commande pour reprendre.")
        sys.exit(130)
