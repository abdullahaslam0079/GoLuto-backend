import base64
import binascii
import uuid

from django.core.files.base import ContentFile
from rest_framework import serializers


class OptionalImageField(serializers.ImageField):
    """Accepts file uploads, omits empty values, and supports base64 JSON payloads."""

    def to_internal_value(self, data):
        if data is None:
            return None

        if isinstance(data, str):
            stripped = data.strip()
            if not stripped or stripped.lower() in {"null", "none", "undefined"}:
                return None
            if stripped.startswith("data:") or self._looks_like_base64(stripped):
                return super().to_internal_value(self._decode_base64_image(stripped))
            raise serializers.ValidationError(
                "Logo must be a file upload or a base64-encoded image. "
                "Omit the logo field if you are not uploading one."
            )

        if data == "" or data == b"":
            return None

        return super().to_internal_value(data)

    @staticmethod
    def _looks_like_base64(value: str) -> bool:
        if len(value) < 16:
            return False
        try:
            base64.b64decode(value, validate=True)
            return True
        except (binascii.Error, ValueError):
            return False

    @staticmethod
    def _decode_base64_image(value: str) -> ContentFile:
        filename = f"logo-{uuid.uuid4().hex}.png"
        payload = value

        if value.startswith("data:"):
            header, _, payload = value.partition(",")
            if ";base64" not in header.lower():
                raise serializers.ValidationError(
                    "Logo data URI must be base64-encoded."
                )
            mime = header.split(":")[1].split(";")[0]
            extension = mime.split("/")[-1] if "/" in mime else "png"
            filename = f"logo-{uuid.uuid4().hex}.{extension}"

        try:
            decoded = base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise serializers.ValidationError("Invalid base64 logo data.") from exc

        return ContentFile(decoded, name=filename)
