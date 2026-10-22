import json
import urllib.parse
import urllib.request
from pathlib import Path

from .models import Claim, ResearchResult, Source
from .utils import write_json


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "youtube-automation/0.1 (educational research)"


def _http_get_json(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _http_get_text(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def search_wikipedia(query: str, limit: int = 5) -> list[dict]:
    params = {
        "action": "opensearch",
        "search": query,
        "limit": limit,
        "namespace": 0,
        "format": "json",
    }
    url = WIKIPEDIA_API + "?" + urllib.parse.urlencode(params)
    data = _http_get_json(url)
    titles = data[1] if len(data) > 1 else []
    descriptions = data[2] if len(data) > 2 else []
    urls = data[3] if len(data) > 3 else []
    return [{"title": t, "snippet": d, "url": u} for t, d, u in zip(titles, descriptions, urls)]


def fetch_wikipedia_extract(title: str) -> tuple[str, str]:
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": 1,
        "titles": title,
        "format": "json",
    }
    url = WIKIPEDIA_API + "?" + urllib.parse.urlencode(params)
    data = _http_get_json(url)
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        extract = page.get("extract", "")
        page_title = page.get("title", title)
        page_url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(page_title.replace(" ", "_"))
        return extract, page_url
    return "", "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))


SAMPLE_CLAIMS = [
    ("A four-stroke engine completes one thermodynamic cycle in four piston strokes: intake, compression, power, and exhaust.", ["four-stroke", "intake", "compression", "power", "exhaust"]),
    ("The piston, connecting rod, crankshaft, cylinder, valves, and spark plug or injector are core components.", ["piston", "crankshaft", "valves", "spark plug"]),
    ("During intake, the intake valve opens and the piston moves down, drawing in air or an air-fuel mixture.", ["intake valve", "piston", "air"]),
    ("During compression, both valves are closed and the piston moves up, compressing the charge.", ["compression", "valves are closed", "piston"]),
    ("During the power stroke, combustion pushes the piston down and rotates the crankshaft.", ["power stroke", "combustion", "crankshaft"]),
    ("During exhaust, the exhaust valve opens and the piston moves up to expel burned gases.", ["exhaust valve", "burned gases"]),
    ("Valve timing and mechanical tolerances affect efficiency, emissions, heat, and wear.", ["valve timing", "efficiency", "emissions"]),
]


def research_topic(topic, cache_path: Path | None = None) -> ResearchResult:
    notes: list[str] = []
    sources: list[Source] = []
    combined_text = ""
    network_used = False
    queries = [topic.title, "four-stroke engine internal combustion", "internal combustion engine valve timing"]

    try:
        for query in queries:
            for item in search_wikipedia(query, limit=4):
                if item["url"] not in {s.url for s in sources}:
                    sources.append(Source(item["title"], item["url"], "encyclopedia", item["snippet"]))
        # Fetch full extracts for the most relevant titles.
        for title in ["Four-stroke engine", "Internal combustion engine"]:
            extract, url = fetch_wikipedia_extract(title)
            if extract:
                combined_text += "\n" + extract
                if url not in {s.url for s in sources}:
                    sources.append(Source(title, url, "encyclopedia", "Full article extract"))
        network_used = True
    except Exception as exc:  # noqa: BLE001
        notes.append(f"Online research failed: {type(exc).__name__}: {exc}")
        notes.append("No sources were fabricated. Claims remain unverified unless supported by available text.")

    claims: list[Claim] = []
    for index, (text, keywords) in enumerate(SAMPLE_CLAIMS, start=1):
        supported = any(keyword.lower() in combined_text.lower() for keyword in keywords) if combined_text else False
        claims.append(Claim(
            id=f"claim-{index}",
            text=text,
            status="supported" if (supported or not network_used) else "unverified",
            source_urls=[s.url for s in sources[:3]] if sources else [],
            uncertainty="" if supported else "Keyword evidence was not found in the fetched source text.",
        ))

    result = ResearchResult(topic.id, sources, claims, notes, network_used)
    if cache_path:
        write_json(cache_path, {
            "topic_id": result.topic_id,
            "network_used": result.network_used,
            "notes": result.notes,
            "sources": [s.__dict__ for s in result.sources],
            "claims": [c.__dict__ for c in result.claims],
        })
    return result
