"""Web search for Online mode.

Uses DuckDuckGo's HTML endpoint (no API key). Only callable when the app is
in ONLINE mode — in offline mode the Network Guard blocks the socket anyway,
so this fails closed by construction.

NOT VERIFIED against the live site in the build environment (no egress to
duckduckgo.com there); parsing is covered by a unit test on a saved HTML
shape, and the failure path returns [] rather than raising.
"""
from __future__ import annotations

import html as html_mod
import re
from dataclasses import dataclass


@dataclass
class WebResult:
    title: str
    snippet: str
    url: str


_RESULT_RE = re.compile(
    r'<a[^>]+class="result__a"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>'
    r'.*?class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
    re.S,
)
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(fragment: str) -> str:
    return html_mod.unescape(_TAG_RE.sub("", fragment)).strip()


def parse_duckduckgo_html(page: str, limit: int = 5) -> list[WebResult]:
    out: list[WebResult] = []
    for m in _RESULT_RE.finditer(page):
        url = html_mod.unescape(m.group("url"))
        # DDG wraps urls as /l/?uddg=<encoded>; extract when present
        uddg = re.search(r"uddg=([^&]+)", url)
        if uddg:
            from urllib.parse import unquote
            url = unquote(uddg.group(1))
        out.append(WebResult(_clean(m.group("title")), _clean(m.group("snippet")), url))
        if len(out) >= limit:
            break
    return out


def web_search(query: str, limit: int = 5, timeout: float = 8.0) -> list[WebResult]:
    """Fetch DDG results. Returns [] on any failure (offline, blocked, parse)."""
    try:
        import httpx
        r = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (NEXUS Local)"},
            timeout=timeout,
            follow_redirects=True,
        )
        if r.status_code != 200:
            return []
        return parse_duckduckgo_html(r.text, limit=limit)
    except Exception:
        return []
