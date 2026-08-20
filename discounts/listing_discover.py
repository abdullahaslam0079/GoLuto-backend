"""Discover product URLs from a public brand sale/listing page."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from .product_import import (
    ProductImportError,
    _flatten_json_ld,
    _is_type,
    fetch_public_text,
    validate_public_http_url,
)

TRACKING_PARAMS = {
    "gclid",
    "fbclid",
    "msclkid",
    "mc_cid",
    "mc_eid",
    "ref",
    "referrer",
}
NAV_PATH_PARTS = {
    "login",
    "logout",
    "cart",
    "checkout",
    "account",
    "konto",
    "wishlist",
    "search",
    "suche",
    "help",
    "faq",
    "impressum",
    "datenschutz",
    "privacy",
    "agb",
    "kontakt",
    "contact",
    "about",
    "blog",
    "news",
    "jobs",
    "career",
    "newsletter",
}
PRODUCT_PATH_HINTS = (
    "/p/",
    "/product",
    "/products/",
    "/pd/",
    "/dp/",
    "/item/",
    "/i/",
    "/sku/",
    "/artikel/",
    "/angebot",
    "/angebote/",
    "/sale/",
)
SKIP_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".css",
    ".js",
    ".pdf",
    ".mp4",
)


def canonicalize_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return (url or "").strip()
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS and not key.lower().startswith("utm_")
    ]
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return urlunparse((parsed.scheme.lower(), host, path, "", urlencode(query), ""))


def discover_product_urls_from_listing(url: str, *, limit: int = 80) -> list[str]:
    validated = validate_public_http_url(url)
    html, _status = fetch_public_text(validated)
    soup = BeautifulSoup(html, "lxml")
    found = _urls_from_json_ld(soup, validated)
    if len(found) < max(3, min(limit, 8)):
        for href in _urls_from_anchors(soup, validated):
            if href not in found:
                found.append(href)
    listing_key = canonicalize_url(validated)
    unique: list[str] = []
    seen: set[str] = set()
    for href in found:
        key = canonicalize_url(href)
        if not key or key == listing_key or key in seen:
            continue
        seen.add(key)
        unique.append(href)
        if len(unique) >= max(1, limit):
            break
    if not unique:
        raise ProductImportError(
            "unsupported_page",
            "Could not find product URLs on this listing page.",
        )
    return unique


def _urls_from_json_ld(soup: BeautifulSoup, page_url: str) -> list[str]:
    urls: list[str] = []
    scripts = soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)})
    nodes: list[dict[str, Any]] = []
    for script in scripts:
        text = script.string or script.get_text() or ""
        text = text.strip()
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        nodes.extend(_flatten_json_ld(data))

    for node in nodes:
        if _is_type(node, "ItemList"):
            urls.extend(_urls_from_item_list(node, page_url))
        if _is_type(node, "Product"):
            href = _url_from_node(node, page_url)
            if href:
                urls.append(href)
    return urls


def _urls_from_item_list(node: dict[str, Any], page_url: str) -> list[str]:
    urls: list[str] = []
    elements = node.get("itemListElement") or node.get("item")
    if not isinstance(elements, list):
        elements = [elements] if elements else []
    for element in elements:
        if isinstance(element, str):
            absolute = urljoin(page_url, element)
            if _is_http_url(absolute):
                urls.append(absolute)
            continue
        if not isinstance(element, dict):
            continue
        item = element.get("item") or element.get("url") or element
        href = _url_from_node(item, page_url) if isinstance(item, dict) else None
        if not href and isinstance(item, str):
            href = urljoin(page_url, item)
        if href and _is_http_url(href):
            urls.append(href)
    return urls


def _url_from_node(node: dict[str, Any], page_url: str) -> str | None:
    raw = node.get("url") or node.get("@id") or node.get("sameAs")
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    text = str(raw or "").strip()
    if not text:
        return None
    absolute = urljoin(page_url, text)
    return absolute if _is_http_url(absolute) else None


def _urls_from_anchors(soup: BeautifulSoup, page_url: str) -> list[str]:
    listing = urlparse(page_url)
    listing_host = _host_key(listing.netloc)
    urls: list[str] = []
    for tag in soup.find_all("a", href=True):
        href = str(tag.get("href") or "").strip()
        if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        absolute = urljoin(page_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if _host_key(parsed.netloc) != listing_host:
            continue
        path = (parsed.path or "").lower()
        if any(path.endswith(ext) for ext in SKIP_EXTENSIONS):
            continue
        parts = [part for part in path.split("/") if part]
        if any(part in NAV_PATH_PARTS for part in parts):
            continue
        if not _looks_like_product_path(path, parts):
            continue
        urls.append(absolute)
    return urls


def _looks_like_product_path(path: str, parts: list[str]) -> bool:
    if any(hint in path for hint in PRODUCT_PATH_HINTS):
        return True
    if len(parts) >= 2 and "-" in parts[-1] and any(ch.isdigit() for ch in parts[-1]):
        return True
    if len(parts) >= 3 and "-" in parts[-1]:
        return True
    return False


def _host_key(netloc: str) -> str:
    host = (netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _is_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
