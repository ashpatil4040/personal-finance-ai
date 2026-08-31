"""Phase 5: lightweight web search for the research agent.

Uses DuckDuckGo Instant Answer and Wikipedia search (no extra API keys).
Failures are swallowed so a flaky network never 500s the Ask endpoint.
"""

from __future__ import annotations

import html as html_lib
import json
import re
import urllib.error
import urllib.parse
import urllib.request

_UA = "personal-finance-ai/1.0 (research-agent; educational)"
_TIMEOUT = 8


def _get_json(url: str) -> object | None:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, OSError):
        return None


def _strip_html(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text or "")
    cleaned = html_lib.unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def parse_ddg(data: object) -> list[dict]:
    """Pure parser for a DuckDuckGo Instant Answer JSON payload."""
    if not isinstance(data, dict):
        return []
    out: list[dict] = []
    abstract = (data.get("AbstractText") or data.get("Abstract") or "").strip()
    abs_url = (data.get("AbstractURL") or "").strip()
    heading = (data.get("Heading") or "").strip()
    if abstract:
        out.append(
            {
                "title": heading or "DuckDuckGo",
                "snippet": abstract[:600],
                "url": abs_url,
                "source": "duckduckgo",
            }
        )
    answer = (data.get("Answer") or "").strip()
    if answer and answer != abstract:
        out.append(
            {
                "title": heading or "Instant answer",
                "snippet": answer[:600],
                "url": abs_url,
                "source": "duckduckgo",
            }
        )
    related = data.get("RelatedTopics") or []
    if isinstance(related, list):
        for item in related[:3]:
            if not isinstance(item, dict):
                continue
            text = (item.get("Text") or "").strip()
            url = (item.get("FirstURL") or "").strip()
            if text:
                out.append(
                    {
                        "title": text.split(" - ", 1)[0][:80],
                        "snippet": text[:600],
                        "url": url,
                        "source": "duckduckgo",
                    }
                )
    return out[:4]


def parse_wikipedia_search(data: object) -> list[dict]:
    """Pure parser for a MediaWiki ``list=search`` JSON payload."""
    if not isinstance(data, dict):
        return []
    query = data.get("query")
    hits = (query.get("search") or []) if isinstance(query, dict) else []
    out: list[dict] = []
    for item in hits:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        snippet = _strip_html(str(item.get("snippet") or "")) or title
        out.append(
            {
                "title": title,
                "snippet": snippet[:600],
                "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
                "source": "wikipedia",
            }
        )
    return out


def _ddg(query: str) -> list[dict]:
    qs = urllib.parse.urlencode(
        {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
    )
    return parse_ddg(_get_json(f"https://api.duckduckgo.com/?{qs}"))


def _wikipedia(query: str) -> list[dict]:
    qs = urllib.parse.urlencode(
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": 3,
            "format": "json",
            "utf8": 1,
            "origin": "*",
        }
    )
    hits = parse_wikipedia_search(_get_json(f"https://en.wikipedia.org/w/api.php?{qs}"))
    # Enrich the top hit with the REST summary paragraph when available.
    if hits:
        slug = urllib.parse.quote(hits[0]["title"].replace(" ", "_"))
        summary = _get_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}")
        if isinstance(summary, dict):
            extract = (summary.get("extract") or "").strip()
            if extract:
                hits[0]["snippet"] = extract[:600]
                desktop = ((summary.get("content_urls") or {}).get("desktop") or {})
                hits[0]["url"] = desktop.get("page") or hits[0]["url"]
    return hits


def search_web(query: str, k: int = 5) -> list[dict]:
    """Return up to ``k`` {title, snippet, url, source} hits. Empty on failure."""
    q = (query or "").strip()
    if not q:
        return []
    hits: list[dict] = []
    seen: set[str] = set()
    for item in _ddg(q) + _wikipedia(q):
        key = (item.get("url") or item.get("title") or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        hits.append(item)
        if len(hits) >= k:
            break
    return hits
