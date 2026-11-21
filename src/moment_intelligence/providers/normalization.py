"""Shared helpers: URL safety, canonicalization, deduplication and text sanitizing.

Provider content is untrusted data. It is cleaned and truncated, and it is never
treated as instructions.
"""

from __future__ import annotations

import hashlib
import ipaddress
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from moment_intelligence.domain.contracts import Offer

_TRACKING_PARAMS = re.compile(r"^(utm_.+|gclid|fbclid|mc_cid|mc_eid|ref|ref_src|igshid)$", re.I)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WS = re.compile(r"\s+")
_BLOCKED_HOSTS = {"localhost", "localhost.localdomain"}


def is_safe_public_url(url: str | None) -> bool:
    """Only plain public http(s) URLs may be shown or redirected to (SSRF / open-redirect guard)."""
    if not url or len(url) > 2048:
        return False
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return False
    if parts.username or parts.password:
        return False
    host = parts.hostname.lower()
    if host in _BLOCKED_HOSTS or host.endswith(".local") or host.endswith(".internal"):
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return "." in host
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)


def canonical_url(url: str) -> str:
    """Normalize a URL for deduplication: https, no www, no tracking params, no fragment."""
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    query = [(k, v) for k, v in parse_qsl(parts.query) if not _TRACKING_PARAMS.match(k)]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(("https", host, path, urlencode(sorted(query)), ""))


def stable_offer_id(prefix: str, url: str) -> str:
    digest = hashlib.sha256(canonical_url(url).encode()).hexdigest()[:16]
    return f"{prefix}_{digest}"


def clean_text(text: str | None, max_length: int) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = _CONTROL.sub(" ", text)
    text = _WS.sub(" ", text).strip()
    if len(text) > max_length:
        text = text[: max_length - 1].rstrip() + "…"
    return text


def _title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def deduplicate(offers: list[Offer]) -> tuple[list[Offer], int]:
    """Drop offers with the same canonical URL or the same normalized title. Keeps first seen."""
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    kept: list[Offer] = []
    for offer in offers:
        url_key = canonical_url(str(offer.source_url)) if offer.source_url else offer.offer_id
        title_key = _title_key(offer.title)
        if url_key in seen_urls or (title_key and title_key in seen_titles):
            continue
        seen_urls.add(url_key)
        if title_key:
            seen_titles.add(title_key)
        kept.append(offer)
    return kept, len(offers) - len(kept)
