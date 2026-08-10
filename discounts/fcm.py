"""Firebase Cloud Messaging helpers.

Push is best-effort: if credentials are missing or firebase-admin is not
installed, calls no-op so the in-app inbox still works.
"""

from __future__ import annotations

import logging
from typing import Any

from .firebase_app import get_firebase_app

logger = logging.getLogger(__name__)


def send_fcm_to_tokens(
    *,
    tokens: list[str],
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> None:
    if not tokens:
        return

    app = get_firebase_app()
    if app is None:
        return

    try:
        from firebase_admin import messaging
    except ImportError:
        return

    # FCM data payload values must be strings.
    string_data = {
        str(key): "" if value is None else str(value)
        for key, value in (data or {}).items()
    }

    # Send individually so one bad token does not fail the batch.
    for token in tokens:
        message = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data=string_data,
            android=messaging.AndroidConfig(priority="high"),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default", badge=1),
                )
            ),
        )
        try:
            messaging.send(message, app=app)
        except Exception as exc:
            logger.warning("FCM send failed for token …%s: %s", token[-8:], exc)
