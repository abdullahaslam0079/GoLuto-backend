"""Shared Firebase Admin app initialization.

Used by FCM push delivery and Firebase Phone Auth token verification.
"""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

_firebase_app = None
_init_attempted = False


def get_firebase_app():
    """Return the initialized Firebase Admin app, or None if unavailable."""
    global _firebase_app, _init_attempted
    if _init_attempted:
        return _firebase_app
    _init_attempted = True

    credentials_json = (os.environ.get("FIREBASE_CREDENTIALS_JSON") or "").strip()
    credentials_path = (os.environ.get("FIREBASE_CREDENTIALS_PATH") or "").strip()
    if not credentials_json and not credentials_path:
        logger.info(
            "Firebase Admin disabled: set FIREBASE_CREDENTIALS_JSON or "
            "FIREBASE_CREDENTIALS_PATH."
        )
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        logger.warning("Firebase Admin disabled: firebase-admin is not installed.")
        return None

    try:
        if credentials_json:
            cred = credentials.Certificate(json.loads(credentials_json))
        else:
            cred = credentials.Certificate(credentials_path)
        _firebase_app = firebase_admin.initialize_app(cred)
    except Exception:
        logger.exception("Failed to initialize Firebase Admin.")
        _firebase_app = None
    return _firebase_app
