from __future__ import annotations

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import (
    Business,
    BusinessEngagementStats,
    BusinessLike,
    Offer,
    OfferEngagementStats,
    OfferLike,
    OfferViewEvent,
)


def ensure_offer_engagement_stats(offer: Offer) -> OfferEngagementStats:
    stats, _ = OfferEngagementStats.objects.get_or_create(offer=offer)
    return stats


def ensure_business_engagement_stats(business: Business) -> BusinessEngagementStats:
    stats, _ = BusinessEngagementStats.objects.get_or_create(business=business)
    return stats


def _increment_offer_views(stats: OfferEngagementStats) -> OfferEngagementStats:
    OfferEngagementStats.objects.filter(pk=stats.pk).update(
        view_count=F("view_count") + 1
    )
    stats.refresh_from_db()
    return stats


def record_offer_view(offer: Offer, user=None) -> OfferEngagementStats:
    stats = ensure_offer_engagement_stats(offer)

    if user is not None and getattr(user, "is_authenticated", False):
        _, created = OfferViewEvent.objects.get_or_create(
            user=user,
            offer=offer,
            viewed_on=timezone.localdate(),
        )
        if not created:
            return stats
        return _increment_offer_views(stats)

    return _increment_offer_views(stats)


def record_business_view(business: Business, user=None) -> BusinessEngagementStats:
    stats = ensure_business_engagement_stats(business)
    BusinessEngagementStats.objects.filter(pk=stats.pk).update(
        view_count=F("view_count") + 1
    )
    stats.refresh_from_db()
    return stats


@transaction.atomic
def toggle_offer_like(user, offer: Offer) -> tuple[bool, OfferEngagementStats]:
    stats = ensure_offer_engagement_stats(offer)
    like = OfferLike.objects.filter(user=user, offer=offer).first()
    if like:
        like.delete()
        OfferEngagementStats.objects.filter(pk=stats.pk).update(
            like_count=F("like_count") - 1
        )
        stats.refresh_from_db()
        return False, stats

    OfferLike.objects.create(user=user, offer=offer)
    OfferEngagementStats.objects.filter(pk=stats.pk).update(
        like_count=F("like_count") + 1
    )
    stats.refresh_from_db()
    return True, stats


@transaction.atomic
def toggle_business_like(user, business: Business) -> tuple[bool, BusinessEngagementStats]:
    stats = ensure_business_engagement_stats(business)
    like = BusinessLike.objects.filter(user=user, business=business).first()
    if like:
        like.delete()
        BusinessEngagementStats.objects.filter(pk=stats.pk).update(
            like_count=F("like_count") - 1
        )
        stats.refresh_from_db()
        return False, stats

    BusinessLike.objects.create(user=user, business=business)
    BusinessEngagementStats.objects.filter(pk=stats.pk).update(
        like_count=F("like_count") + 1
    )
    stats.refresh_from_db()
    return True, stats


@transaction.atomic
def set_business_like(
    user, business: Business, *, liked: bool
) -> tuple[bool, BusinessEngagementStats]:
    stats = ensure_business_engagement_stats(business)
    like = BusinessLike.objects.filter(user=user, business=business).first()

    if liked and like is None:
        BusinessLike.objects.create(user=user, business=business)
        BusinessEngagementStats.objects.filter(pk=stats.pk).update(
            like_count=F("like_count") + 1
        )
        stats.refresh_from_db()
        return True, stats

    if not liked and like is not None:
        like.delete()
        BusinessEngagementStats.objects.filter(pk=stats.pk).update(
            like_count=F("like_count") - 1
        )
        stats.refresh_from_db()
        return False, stats

    stats.refresh_from_db()
    return liked, stats


def user_liked_offer_ids(user, offer_ids: list[int]) -> set[int]:
    if not user or not user.is_authenticated or not offer_ids:
        return set()
    return set(
        OfferLike.objects.filter(user=user, offer_id__in=offer_ids).values_list(
            "offer_id", flat=True
        )
    )


def user_liked_business_ids(user, business_ids: list[int]) -> set[int]:
    if not user or not user.is_authenticated or not business_ids:
        return set()
    return set(
        BusinessLike.objects.filter(
            user=user, business_id__in=business_ids
        ).values_list("business_id", flat=True)
    )


def favorited_branches_for_user(user, *, location=None):
    """Return one representative branch per business the user has favorited.

    Prefers the nearest branch when [location] is provided; otherwise the
    branch with the highest active discount. Order follows most-recent like.
    """
    from .location_utils import branch_distance_km
    from .models import Branch
    from .offer_utils import branch_highlight_queryset

    liked_business_ids = list(
        BusinessLike.objects.filter(user=user)
        .order_by("-created_at")
        .values_list("business_id", flat=True)
    )
    if not liked_business_ids:
        return []

    branches = list(
        branch_highlight_queryset(
            Branch.objects.filter(business_id__in=liked_business_ids)
        )
    )
    if not branches:
        return []

    best_by_business: dict[int, object] = {}
    for branch in branches:
        business_id = branch.business_id
        current = best_by_business.get(business_id)
        if current is None:
            best_by_business[business_id] = branch
            continue

        if location is not None:
            if branch_distance_km(branch, location) < branch_distance_km(
                current, location
            ):
                best_by_business[business_id] = branch
            continue

        current_discount = getattr(current, "highest_discount_percent", None) or 0
        branch_discount = getattr(branch, "highest_discount_percent", None) or 0
        if branch_discount > current_discount:
            best_by_business[business_id] = branch

    return [
        best_by_business[business_id]
        for business_id in liked_business_ids
        if business_id in best_by_business
    ]


def pick_featured_offers_one_per_business(offers: list[Offer]) -> list[Offer]:
    """Pick a single spotlight offer per business (views, likes, then discount)."""
    featured: dict[int, Offer] = {}

    def sort_key(offer: Offer) -> tuple:
        stats = getattr(offer, "engagement_stats", None)
        views = stats.view_count if stats else 0
        likes = stats.like_count if stats else 0
        return (views, likes, float(offer.discount_percent), offer.id)

    for offer in sorted(offers, key=sort_key, reverse=True):
        if offer.business_id not in featured:
            featured[offer.business_id] = offer

    result = list(featured.values())
    result.sort(key=sort_key, reverse=True)
    return result
