from __future__ import annotations

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken


def blacklist_user_tokens(user, refresh: str | None = None) -> None:
    if refresh:
        RefreshToken(refresh).blacklist()
        return

    outstanding_tokens = OutstandingToken.objects.filter(user_id=user.id)
    for outstanding_token in outstanding_tokens:
        BlacklistedToken.objects.get_or_create(token=outstanding_token)


def logout_response_message(refresh: str | None = None) -> str:
    if refresh:
        return "Logged out successfully."
    return "Logged out successfully. Discard the access token on the client."
