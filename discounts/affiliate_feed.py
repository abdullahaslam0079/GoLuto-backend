"""Parse affiliate CSV/XML product feeds into discovered deal rows."""

from __future__ import annotations

import csv
import io
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from xml.etree.ElementTree import ParseError

from .listing_discover import canonicalize_url
from .product_import import ProductImportError, fetch_public_text, validate_public_http_url

ID_KEYS = ("id", "product_id", "merchant_product_id", "aw_product_id", "gtin", "sku", "ean")
TITLE_KEYS = ("title", "name", "product_name", "productname", "aw_product_name")
DESCRIPTION_KEYS = (
    "description",
    "product_short_description",
    "desc",
    "product_description",
)
PRICE_KEYS = ("price", "search_price", "retail_price", "list_price", "aw_search_price")
SALE_KEYS = (
    "sale_price",
    "discounted_price",
    "special_price",
    "display_price",
    "aw_price",
)
LINK_KEYS = (
    "link",
    "url",
    "aw_deep_link",
    "product_url",
    "destination_url",
    "merchant_deep_link",
)
IMAGE_KEYS = (
    "image",
    "image_url",
    "aw_image_url",
    "product_image",
    "large_image",
    "image_large",
)
AVAIL_KEYS = ("availability", "stock_status", "in_stock", "stock")
END_KEYS = ("end_date", "valid_to", "price_valid_until", "expires", "expiry_date")


@dataclass
class DiscoveredDeal:
    source_key: str
    source_url: str
    title: str = ""
    description: str = ""
    detailed_description: str = ""
    original_price: str | None = None
    discounted_price: str | None = None
    image_urls: list[str] = field(default_factory=list)
    availability: str | None = None
    price_valid_until: str | None = None
    draft: dict[str, Any] | None = None


def parse_affiliate_feed(url: str, *, limit: int = 80) -> list[DiscoveredDeal]:
    validated = validate_public_http_url(url)
    text, _status = fetch_public_text(validated)
    stripped = (text or "").lstrip()
    if stripped.startswith("<"):
        rows = _from_xml(text)
    else:
        rows = _from_csv(text)
    deals: list[DiscoveredDeal] = []
    seen: set[str] = set()
    for row in rows:
        deal = _row_to_deal(row)
        if deal is None or deal.source_key in seen:
            continue
        seen.add(deal.source_key)
        deals.append(deal)
        if len(deals) >= max(1, limit):
            break
    if not deals:
        raise ProductImportError(
            "unsupported_page",
            "Could not parse product rows from this affiliate feed.",
        )
    return deals


def _from_csv(text: str) -> list[dict[str, str]]:
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows: list[dict[str, str]] = []
    for raw in reader:
        if not isinstance(raw, dict):
            continue
        rows.append({str(key or "").strip(): str(value or "").strip() for key, value in raw.items()})
    return rows


def _from_xml(text: str) -> list[dict[str, str]]:
    try:
        root = ET.fromstring(text)
    except ParseError as exc:
        raise ProductImportError("unsupported_page", "Affiliate feed XML is invalid.") from exc
    rows: list[dict[str, str]] = []
    candidates = list(root.findall(".//product")) + list(root.findall(".//item"))
    if not candidates:
        candidates = [child for child in list(root) if len(list(child))]
    for node in candidates:
        row: dict[str, str] = {}
        for child in list(node):
            tag = _local_name(child.tag)
            value = (child.text or "").strip()
            if not value:
                value = (child.get("url") or child.get("href") or "").strip()
            if tag and value and tag not in row:
                row[tag] = value
        if row:
            rows.append(row)
    return rows


def _row_to_deal(row: dict[str, str]) -> DiscoveredDeal | None:
    lookup = {key.lower().replace(" ", "_"): value for key, value in row.items() if key}
    product_id = _first(lookup, ID_KEYS)
    link = _first(lookup, LINK_KEYS)
    title = _first(lookup, TITLE_KEYS)
    if not link and not product_id:
        return None
    source_url = (link or "").strip()
    source_key = product_id or canonicalize_url(source_url)
    if not source_key:
        return None
    if product_id:
        source_key = f"feed:{product_id}"

    sale = _parse_decimal(_first(lookup, SALE_KEYS))
    price = _parse_decimal(_first(lookup, PRICE_KEYS))
    original = None
    discounted = None
    if price is not None and sale is not None and sale < price:
        original = f"{price:.2f}"
        discounted = f"{sale:.2f}"
    elif sale is not None:
        original = f"{sale:.2f}"
    elif price is not None:
        original = f"{price:.2f}"

    image = _first(lookup, IMAGE_KEYS)
    description = _first(lookup, DESCRIPTION_KEYS)
    availability = _first(lookup, AVAIL_KEYS)
    end_date = _first(lookup, END_KEYS)
    draft = {
        "source_url": source_url,
        "title": title,
        "description": description,
        "detailed_description": description,
        "original_price": original,
        "list_price": original if discounted else None,
        "sale_price": discounted or original,
        "image_urls": [image] if image else [],
        "external_url": source_url,
        "availability": availability or None,
        "price_valid_until": end_date or None,
        "suggested_offer_type": "item" if original else "percentage_bill",
        "ai_enriched": False,
        "warnings": [],
    }
    return DiscoveredDeal(
        source_key=source_key[:500],
        source_url=source_url,
        title=title,
        description=description,
        detailed_description=description,
        original_price=original,
        discounted_price=discounted,
        image_urls=[image] if image else [],
        availability=availability or None,
        price_valid_until=end_date or None,
        draft=draft,
    )


def _first(lookup: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = lookup.get(key)
        if value:
            return value
    return ""


def _parse_decimal(value: str) -> Decimal | None:
    text = (value or "").strip().replace("€", "").replace("EUR", "").strip()
    if not text:
        return None
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        parts = text.split(",")
        text = text.replace(",", ".") if len(parts[-1]) <= 2 else text.replace(",", "")
    try:
        amount = Decimal(text)
    except Exception:
        return None
    return amount if amount > 0 else None


def _local_name(tag: str) -> str:
    if "}" in tag:
        tag = tag.rsplit("}", 1)[-1]
    return tag.lower().replace("-", "_")
