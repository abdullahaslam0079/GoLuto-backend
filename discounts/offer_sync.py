"""Sync offers from brand listing pages and affiliate feeds."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .affiliate_feed import DiscoveredDeal, parse_affiliate_feed
from .listing_discover import canonicalize_url, discover_product_urls_from_listing
from .models import DealSource, Offer, OfferGalleryImage
from .product_import import ProductImportError, import_product_from_url

logger = logging.getLogger(__name__)

FETCH_PAUSE_SECONDS = 0.15
OUT_OF_STOCK = {"outofstock", "soldout", "discontinued", "offline"}
IN_STOCK = {"instock", "limitedavailability", "onlineonly", "instoreonly", "preorder"}


@dataclass
class SyncResult:
    discovered: int = 0
    created: int = 0
    updated: int = 0
    skipped_rejected: int = 0
    skipped_manual: int = 0
    disabled_missing: int = 0
    disabled_unavailable: int = 0
    reenabled: int = 0
    errors: int = 0
    error_samples: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "discovered": self.discovered,
            "created": self.created,
            "updated": self.updated,
            "skipped_rejected": self.skipped_rejected,
            "skipped_manual": self.skipped_manual,
            "disabled_missing": self.disabled_missing,
            "disabled_unavailable": self.disabled_unavailable,
            "reenabled": self.reenabled,
            "errors": self.errors,
            "error_samples": self.error_samples[:8],
        }


def sync_all_deal_sources(*, only_enabled: bool = True) -> list[tuple[DealSource, SyncResult]]:
    qs = DealSource.objects.select_related("business").order_by("id")
    if only_enabled:
        qs = qs.filter(is_enabled=True)
    results: list[tuple[DealSource, SyncResult]] = []
    for source in qs:
        results.append((source, sync_deal_source(source)))
    return results


def sync_deal_source(source: DealSource) -> SyncResult:
    result = SyncResult()
    try:
        deals = _discover(source)
        result.discovered = len(deals)
        seen_keys = _upsert_deals(source, deals, result)
        _disable_missing(source, seen_keys, result)
        source.last_error = ""
        if result.discovered == 0:
            source.last_error = "No products found."
    except ProductImportError as exc:
        result.errors += 1
        result.error_samples.append(exc.message)
        source.last_error = exc.message
        logger.warning("Deal source %s failed: %s", source.pk, exc.message)
    except Exception as exc:
        result.errors += 1
        message = str(exc) or exc.__class__.__name__
        result.error_samples.append(message)
        source.last_error = message
        logger.exception("Deal source %s failed unexpectedly", source.pk)
    source.last_synced_at = timezone.now()
    source.save(update_fields=["last_synced_at", "last_error"])
    return result


def _discover(source: DealSource) -> list[DiscoveredDeal]:
    limit = max(1, int(source.max_items or 80))
    if source.kind == DealSource.Kind.AFFILIATE_FEED:
        url = (source.feed_url or "").strip()
        if not url:
            raise ProductImportError("invalid_url", "Feed URL is required.")
        return parse_affiliate_feed(url, limit=limit)

    url = (source.listing_url or "").strip()
    if not url:
        raise ProductImportError("invalid_url", "Listing URL is required.")
    product_urls = discover_product_urls_from_listing(url, limit=limit)
    return [
        DiscoveredDeal(
            source_key=canonicalize_url(href)[:500],
            source_url=href,
        )
        for href in product_urls
        if canonicalize_url(href)
    ]


def _upsert_deals(
    source: DealSource,
    deals: list[DiscoveredDeal],
    result: SyncResult,
) -> set[str]:
    seen: set[str] = set()
    now = timezone.now()
    for index, deal in enumerate(deals):
        if not deal.source_key:
            continue
        seen.add(deal.source_key)
        try:
            draft = deal.draft
            if source.kind == DealSource.Kind.BRAND_LISTING:
                if index:
                    time.sleep(FETCH_PAUSE_SECONDS)
                draft = import_product_from_url(deal.source_url, enrich=False)
            if not draft:
                continue
            _apply_draft(source, deal, draft, now, result)
        except ProductImportError as exc:
            if exc.code == "http_404":
                _mark_unavailable(
                    source,
                    deal.source_key,
                    Offer.UnavailableReason.HTTP_404,
                    result,
                )
            else:
                result.errors += 1
                result.error_samples.append(f"{deal.source_url}: {exc.message}")
        except Exception as exc:
            result.errors += 1
            result.error_samples.append(f"{deal.source_url}: {exc}")
            logger.exception("Failed upserting %s", deal.source_url)
    return seen


def _apply_draft(
    source: DealSource,
    deal: DiscoveredDeal,
    draft: dict[str, Any],
    now,
    result: SyncResult,
) -> None:
    availability = (draft.get("availability") or deal.availability or "").replace(" ", "")
    fields = _offer_fields_from_draft(source, deal, draft)
    existing = (
        Offer.objects.filter(business=source.business, source_key=deal.source_key)
        .first()
    )
    if existing is None and deal.source_url:
        existing = (
            Offer.objects.filter(business=source.business, source_url=deal.source_url)
            .first()
        )

    if existing is None:
        with transaction.atomic():
            offer = Offer.objects.create(
                business=source.business,
                **fields,
                origin=_origin_for(source),
                source=source,
                source_url=(deal.source_url or fields.get("external_url") or "")[:1000],
                source_key=deal.source_key[:500],
                review_status=Offer.ReviewStatus.PENDING,
                is_enabled=False,
                last_seen_at=now,
                last_synced_at=now,
            )
            _replace_gallery(offer, draft.get("image_urls") or deal.image_urls)
        result.created += 1
        _apply_availability(offer, availability, result)
        return

    if existing.origin == Offer.Origin.MANUAL:
        result.skipped_manual += 1
        return
    if existing.review_status == Offer.ReviewStatus.REJECTED:
        result.skipped_rejected += 1
        return

    update_fields = [
        "title",
        "description",
        "detailed_description",
        "external_url",
        "external_url_label",
        "offer_type",
        "item_name",
        "discount_percent",
        "original_price",
        "discounted_price",
        "is_time_limited",
        "ends_at",
        "last_seen_at",
        "last_synced_at",
        "source",
        "source_url",
        "source_key",
        "unavailable_reason",
    ]
    existing.title = fields["title"]
    existing.description = fields["description"]
    existing.detailed_description = fields["detailed_description"]
    existing.external_url = fields["external_url"]
    existing.external_url_label = fields["external_url_label"]
    existing.offer_type = fields["offer_type"]
    existing.item_name = fields["item_name"]
    existing.discount_percent = fields["discount_percent"]
    existing.original_price = fields["original_price"]
    existing.discounted_price = fields["discounted_price"]
    existing.is_time_limited = fields["is_time_limited"]
    existing.ends_at = fields["ends_at"]
    existing.last_seen_at = now
    existing.last_synced_at = now
    existing.source = source
    existing.source_url = (deal.source_url or existing.source_url)[:1000]
    existing.source_key = deal.source_key[:500]
    existing.unavailable_reason = ""
    existing.save(update_fields=update_fields)
    _replace_gallery(existing, draft.get("image_urls") or deal.image_urls)
    result.updated += 1
    _apply_availability(existing, availability, result)


def _apply_availability(offer: Offer, availability: str, result: SyncResult) -> None:
    token = (availability or "").split("/")[-1].split(":")[-1].lower()
    if offer.review_status != Offer.ReviewStatus.APPROVED:
        return
    if token in OUT_OF_STOCK:
        if offer.is_enabled or offer.disabled_by != Offer.DisabledBy.ADMIN:
            offer.is_enabled = False
            offer.disabled_by = Offer.DisabledBy.SYNC
            offer.unavailable_reason = Offer.UnavailableReason.OUT_OF_STOCK
            offer.save(
                update_fields=["is_enabled", "disabled_by", "unavailable_reason"]
            )
            result.disabled_unavailable += 1
        return
    if token in IN_STOCK or not token:
        if (
            not offer.is_enabled
            and offer.disabled_by == Offer.DisabledBy.SYNC
            and offer.unavailable_reason
            in {
                Offer.UnavailableReason.OUT_OF_STOCK,
                Offer.UnavailableReason.HTTP_404,
                Offer.UnavailableReason.MISSING_FROM_SOURCE,
                "",
            }
        ):
            offer.is_enabled = True
            offer.disabled_by = ""
            offer.unavailable_reason = ""
            offer.save(
                update_fields=["is_enabled", "disabled_by", "unavailable_reason"]
            )
            result.reenabled += 1


def _mark_unavailable(
    source: DealSource,
    source_key: str,
    reason: str,
    result: SyncResult,
) -> None:
    offer = Offer.objects.filter(
        business=source.business,
        source_key=source_key,
        origin= _origin_for(source),
    ).first()
    if offer is None or offer.origin == Offer.Origin.MANUAL:
        return
    if offer.review_status == Offer.ReviewStatus.REJECTED:
        return
    if offer.disabled_by == Offer.DisabledBy.ADMIN:
        offer.unavailable_reason = reason
        offer.save(update_fields=["unavailable_reason"])
        return
    offer.is_enabled = False
    offer.disabled_by = Offer.DisabledBy.SYNC
    offer.unavailable_reason = reason
    offer.last_synced_at = timezone.now()
    offer.save(
        update_fields=[
            "is_enabled",
            "disabled_by",
            "unavailable_reason",
            "last_synced_at",
        ]
    )
    if reason == Offer.UnavailableReason.HTTP_404:
        result.disabled_unavailable += 1


def _disable_missing(source: DealSource, seen_keys: set[str], result: SyncResult) -> None:
    qs = Offer.objects.filter(
        source=source,
        origin=_origin_for(source),
    ).exclude(origin=Offer.Origin.MANUAL)
    if seen_keys:
        qs = qs.exclude(source_key__in=seen_keys)
    else:
        # Discovery returned nothing usable; do not mass-disable.
        return
    now = timezone.now()
    for offer in qs:
        if offer.review_status == Offer.ReviewStatus.REJECTED:
            continue
        offer.unavailable_reason = Offer.UnavailableReason.MISSING_FROM_SOURCE
        offer.last_synced_at = now
        update = ["unavailable_reason", "last_synced_at"]
        if offer.disabled_by != Offer.DisabledBy.ADMIN:
            offer.is_enabled = False
            offer.disabled_by = Offer.DisabledBy.SYNC
            update.extend(["is_enabled", "disabled_by"])
            if offer.review_status == Offer.ReviewStatus.APPROVED:
                result.disabled_missing += 1
        offer.save(update_fields=update)


def _offer_fields_from_draft(
    source: DealSource,
    deal: DiscoveredDeal,
    draft: dict[str, Any],
) -> dict[str, Any]:
    title = _clip(draft.get("title") or deal.title or "Imported offer", 120)
    description = draft.get("description") or deal.description or ""
    detailed = draft.get("detailed_description") or deal.detailed_description or description
    source_url = (draft.get("external_url") or deal.source_url or "")[:500]
    list_price = _as_decimal(draft.get("list_price") or deal.original_price)
    sale_price = _as_decimal(
        draft.get("sale_price") or deal.discounted_price or draft.get("original_price")
    )
    original = list_price
    discounted = sale_price
    if original is None and sale_price is not None:
        original = sale_price
        discounted = None
    if (
        original is not None
        and discounted is not None
        and discounted > 0
        and original > discounted
    ):
        offer_type = Offer.OfferType.ITEM
        item_name = title
        discount_percent = Offer.compute_discount_percent(original, discounted)
        original_price = original
        discounted_price = discounted
    else:
        offer_type = Offer.OfferType.PERCENTAGE_BILL
        item_name = ""
        suggested = _as_decimal(draft.get("suggested_discount_percent"))
        discount_percent = suggested if suggested and 0 < suggested <= 100 else Decimal("10.00")
        original_price = None
        discounted_price = None

    ends_at = _parse_end(draft.get("price_valid_until") or deal.price_valid_until)
    return {
        "title": title,
        "description": description,
        "detailed_description": detailed,
        "offer_type": offer_type,
        "redemption_mode": Offer.RedemptionMode.VIEW_ONLY,
        "is_online": bool(source.is_online),
        "item_name": item_name,
        "included_items": [],
        "discount_percent": discount_percent,
        "original_price": original_price,
        "discounted_price": discounted_price,
        "usage_limit_type": Offer.UsageLimitType.ONE_TIME,
        "usage_limit_count": 1,
        "external_url": source_url,
        "external_url_label": Offer.default_external_url_label(offer_type),
        "is_time_limited": bool(ends_at),
        "starts_at": None,
        "ends_at": ends_at,
    }


def _replace_gallery(offer: Offer, image_urls: list[str] | None) -> None:
    urls = [str(url).strip() for url in (image_urls or []) if str(url).strip()]
    if not urls:
        return
    offer.gallery_images.all().delete()
    for index, url in enumerate(urls[:12]):
        OfferGalleryImage.objects.create(offer=offer, source_url=url, sort_order=index)
    offer.image = None
    offer.save(update_fields=["image"])


def _origin_for(source: DealSource) -> str:
    if source.kind == DealSource.Kind.AFFILIATE_FEED:
        return Offer.Origin.AFFILIATE_FEED
    return Offer.Origin.BRAND_LISTING


def _clip(value: str, limit: int) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _as_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return amount if amount > 0 else None


def _parse_end(value: str | None):
    text = (value or "").strip()
    if not text:
        return None
    parsed = parse_datetime(text)
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def default_source_name(url: str) -> str:
    host = urlparse(url).hostname or ""
    if host.startswith("www."):
        host = host[4:]
    return host[:120]
