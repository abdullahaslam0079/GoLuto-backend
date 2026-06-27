from datetime import timedelta

from django.db.models import F, Max, Q
from django.utils import timezone

from .models import Offer, OfferBranchStats, OfferRedemption


def active_offer_q(now=None, prefix=""):
    now = now or timezone.now()
    field = f"{prefix}__" if prefix else ""

    return Q(**{f"{field}is_enabled": True}) & (
        Q(**{f"{field}is_time_limited": False})
        | (
            Q(**{f"{field}is_time_limited": True})
            & (
                Q(**{f"{field}starts_at__isnull": True})
                | Q(**{f"{field}starts_at__lte": now})
            )
            & (
                Q(**{f"{field}ends_at__isnull": True})
                | Q(**{f"{field}ends_at__gte": now})
            )
        )
    )


def filter_active_offers(queryset, now=None):
    return queryset.filter(active_offer_q(now))


def period_start(limit_type: str, now=None):
    now = now or timezone.now()
    if limit_type.endswith("_week"):
        return now - timedelta(days=now.weekday())
    if limit_type.endswith("_month"):
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return None


def get_user_redemption_count(user, offer, branch, limit_type, now=None):
    queryset = OfferRedemption.objects.filter(user=user, offer=offer, branch=branch)
    period = period_start(limit_type, now)
    if period:
        queryset = queryset.filter(redeemed_at__gte=period)
    return queryset.count()


def can_user_redeem_offer(user, offer, branch):
    if not offer.is_active:
        return False, "This offer is not currently active."

    if not offer.branches.filter(pk=branch.pk).exists():
        return False, "This offer is not available at the selected branch."

    if branch.business_id != offer.business_id:
        return False, "This branch does not belong to the offer business."

    limit_type = offer.usage_limit_type
    count = offer.usage_limit_count
    now = timezone.now()
    used = get_user_redemption_count(user, offer, branch, limit_type, now)

    if limit_type == Offer.UsageLimitType.ONE_TIME:
        if used >= 1:
            return False, "You have already used this offer."
    elif limit_type == Offer.UsageLimitType.ONCE_PER_WEEK:
        if used >= 1:
            return False, "You can use this offer once per week. Try again next week."
    elif limit_type == Offer.UsageLimitType.ONCE_PER_MONTH:
        if used >= 1:
            return False, "You can use this offer once per month. Try again next month."
    elif limit_type == Offer.UsageLimitType.N_TIMES_PER_WEEK:
        if used >= count:
            return (
                False,
                f"You have reached the limit of {count} uses per week for this offer.",
            )
    elif limit_type == Offer.UsageLimitType.N_TIMES_PER_MONTH:
        if used >= count:
            return (
                False,
                f"You have reached the limit of {count} uses per month for this offer.",
            )
    elif limit_type == Offer.UsageLimitType.N_TIMES_TOTAL:
        total_used = OfferRedemption.objects.filter(
            user=user, offer=offer, branch=branch
        ).count()
        if total_used >= count:
            return (
                False,
                f"You have reached the maximum of {count} uses for this offer.",
            )

    return True, ""


def increment_branch_stat(offer, branch, *, scan=False, avail=False):
    stats, _ = OfferBranchStats.objects.get_or_create(offer=offer, branch=branch)
    if scan:
        OfferBranchStats.objects.filter(pk=stats.pk).update(
            scan_count=F("scan_count") + 1
        )
    if avail:
        OfferBranchStats.objects.filter(pk=stats.pk).update(
            avail_count=F("avail_count") + 1
        )
