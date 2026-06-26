from rest_framework.exceptions import NotFound

from .models import Address


def parse_address_ref(address_ref: str) -> int | None:
    suffix = address_ref[5:] if address_ref.startswith("addr_") else address_ref
    if not suffix.isdigit():
        return None
    return int(suffix)


def get_user_address(user, address_ref: str) -> Address:
    pk = parse_address_ref(address_ref)
    if pk is None:
        raise NotFound("Invalid address ID. Use format: addr_<id>.")
    try:
        return user.addresses.get(pk=pk)
    except Address.DoesNotExist as exc:
        raise NotFound("Address not found.") from exc


def promote_next_default_address(user, exclude_pk: int | None = None) -> None:
    queryset = user.addresses.order_by("id")
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    next_address = queryset.first()
    if next_address and not next_address.is_default:
        next_address.is_default = True
        next_address.save(update_fields=["is_default"])
