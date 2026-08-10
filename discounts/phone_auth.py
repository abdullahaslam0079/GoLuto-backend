"""Firebase Phone Auth → Django user helpers."""

from __future__ import annotations

import logging
import re

from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed, ValidationError

from .firebase_app import get_firebase_app

logger = logging.getLogger(__name__)
User = get_user_model()

_PHONE_LOCAL_DOMAIN = "phone.goluto.local"


def _synthetic_email_for_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if not digits:
        raise ValidationError({"id_token": ["Phone number claim is invalid."]})
    return f"{digits}@{_PHONE_LOCAL_DOMAIN}"


def verify_firebase_phone_id_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return decoded claims.

    Raises AuthenticationFailed on invalid/expired tokens or missing Firebase config.
    """
    app = get_firebase_app()
    if app is None:
        raise AuthenticationFailed(
            "Phone authentication is unavailable. Firebase credentials are not configured."
        )

    try:
        from firebase_admin import auth as firebase_auth
    except ImportError as exc:
        raise AuthenticationFailed(
            "Phone authentication is unavailable. firebase-admin is not installed."
        ) from exc

    try:
        return firebase_auth.verify_id_token(id_token, app=app)
    except Exception as exc:
        logger.info("Firebase ID token verification failed: %s", exc)
        raise AuthenticationFailed("Invalid or expired Firebase ID token.") from exc


def get_or_create_consumer_from_firebase_claims(claims: dict) -> User:
    """Resolve or create a consumer user from verified Firebase phone claims."""
    firebase_uid = (claims.get("uid") or "").strip()
    phone = (claims.get("phone_number") or "").strip()

    if not firebase_uid:
        raise ValidationError({"id_token": ["Firebase UID is missing from the token."]})
    if not phone:
        raise ValidationError(
            {"id_token": ["Phone number is missing from the Firebase token."]}
        )

    user = User.objects.filter(firebase_uid=firebase_uid).first()
    if user is None:
        user = User.objects.filter(phone=phone).first()

    if user is not None:
        if user.account_type != User.AccountType.CONSUMER:
            raise ValidationError(
                {
                    "id_token": [
                        "This phone number is linked to a non-consumer account."
                    ]
                }
            )
        changed = False
        if user.firebase_uid != firebase_uid:
            user.firebase_uid = firebase_uid
            changed = True
        if user.phone != phone:
            user.phone = phone
            changed = True
        if changed:
            user.save(update_fields=["firebase_uid", "phone"])
        return user

    email = _synthetic_email_for_phone(phone)
    # Extremely unlikely collision; fall back to uid-based email.
    if User.objects.filter(email__iexact=email).exists():
        email = f"{firebase_uid}@{_PHONE_LOCAL_DOMAIN}"

    user = User(
        email=email,
        phone=phone,
        firebase_uid=firebase_uid,
        account_type=User.AccountType.CONSUMER,
    )
    user.set_unusable_password()
    user.save()
    return user
