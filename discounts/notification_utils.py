from __future__ import annotations

import logging

from .models import BusinessLike, DeviceToken, Notification, Offer, UserPreferences

logger = logging.getLogger(__name__)


def _notifications_enabled_for(user_id: int) -> bool:
    prefs = UserPreferences.objects.filter(user_id=user_id).only("notifications_enabled").first()
    if prefs is None:
        return True
    return prefs.notifications_enabled


def create_and_push_notification(
    *,
    user_id: int,
    type: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> Notification:
    notification = Notification.objects.create(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        data=data or {},
    )

    if not _notifications_enabled_for(user_id):
        return notification

    tokens = list(
        DeviceToken.objects.filter(user_id=user_id).values_list("token", flat=True)
    )
    if tokens:
        send_fcm_to_tokens(
            tokens=tokens,
            title=title,
            body=body,
            data={
                **(data or {}),
                "notification_id": notification.id,
                "type": type,
            },
        )
    return notification


def notify_favorited_business_new_offer(offer: Offer) -> int:
    """Create inbox (+ optional push) for users who favorited the offer's business.

    Returns the number of notifications created.
    """
    if not offer.is_enabled:
        return 0

    business = offer.business
    branch = offer.branches.order_by("id").first()
    if branch is None:
        branch = business.branches.order_by("id").first()

    likes = (
        BusinessLike.objects.filter(business=business)
        .select_related("user")
        .only("user_id")
    )
    user_ids = sorted({like.user_id for like in likes})
    if not user_ids:
        return 0

    title = f"New offer from {business.name}"
    body = offer.title
    data = {
        "type": Notification.NotificationType.FAVORITED_BUSINESS_NEW_OFFER,
        "offer_id": offer.id,
        "business_id": business.id,
        "branch_id": branch.id if branch else None,
        "route": "/business-store",
    }

    created = 0
    for user_id in user_ids:
        try:
            create_and_push_notification(
                user_id=user_id,
                type=Notification.NotificationType.FAVORITED_BUSINESS_NEW_OFFER,
                title=title,
                body=body,
                data=data,
            )
            created += 1
        except Exception:
            logger.exception(
                "Failed to notify user %s about offer %s", user_id, offer.id
            )
    return created
