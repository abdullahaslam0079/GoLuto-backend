"""Firebase Cloud Messaging helpers.

Push is best-effort: if credentials are missing or firebase-admin is not
installed, calls no-op so the in-app inbox still works.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_firebase_app = None
_init_attempted = False


def _get_firebase_app():
    global _firebase_app, _init_attempted
    if _init_attempted:
        return _firebase_app
    _init_attempted = True

    credentials_json = (os.environ.get("FIREBASE_CREDENTIALS_JSON") or "").strip()
    credentials_path = (os.environ.get("FIREBASE_CREDENTIALS_PATH") or "").strip()
    if not credentials_json and not credentials_path:
        logger.info("FCM disabled: set FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS_PATH.")
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        logger.warning("FCM disabled: firebase-admin is not installed.")
        return None

    try:
        if credentials_json:
            cred = credentials.Certificate(json.loads(credentials_json))
        else:
            cred = credentials.Certificate(credentials_path)
        _firebase_app = firebase_admin.initialize_app(cred)
    except Exception:
        logger.exception("Failed to initialize Firebase Admin for FCM.")
        _firebase_app = None
    return _firebase_app


def send_fcm_to_tokens(
    *,
    tokens: list[str],
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> None:
    if not tokens:
        return

    app = _get_firebase_app()
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
