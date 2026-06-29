from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .models import Offer


@dataclass
class OfferPaymentPreview:
    offer_type: str
    discount_percent: Decimal
    item_name: str
    original_amount: Decimal | None
    discount_amount: Decimal | None
    amount_to_pay: Decimal | None
    bill_amount: Decimal | None
    requires_bill_amount: bool

    @property
    def summary(self) -> str | None:
        if self.amount_to_pay is None:
            return None
        amount = f"€{self.amount_to_pay:.2f}"
        if self.offer_type == Offer.OfferType.ITEM and self.item_name:
            return f"Pay {amount} at the counter for {self.item_name}"
        if self.offer_type == Offer.OfferType.PERCENTAGE_BILL and self.original_amount is not None:
            return (
                f"Pay {amount} at the counter "
                f"({self.discount_percent:.0f}% off €{self.original_amount:.2f} bill)"
            )
        return f"Pay {amount} at the counter"

    def as_dict(self) -> dict[str, Any]:
        return {
            "offer_type": self.offer_type,
            "item_name": self.item_name or None,
            "discount_percent": self.discount_percent,
            "original_amount": self.original_amount,
            "discount_amount": self.discount_amount,
            "amount_to_pay": self.amount_to_pay,
            "bill_amount": self.bill_amount,
            "requires_bill_amount": self.requires_bill_amount,
            "summary": self.summary,
        }


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def compute_offer_payment(
    offer: Offer, *, bill_amount: Decimal | None = None
) -> OfferPaymentPreview:
    if offer.offer_type == Offer.OfferType.ITEM:
        original = Decimal(str(offer.original_price))
        discounted = Decimal(str(offer.discounted_price))
        return OfferPaymentPreview(
            offer_type=offer.offer_type,
            discount_percent=offer.discount_percent,
            item_name=offer.item_name,
            original_amount=original,
            discount_amount=_quantize_money(original - discounted),
            amount_to_pay=discounted,
            bill_amount=None,
            requires_bill_amount=False,
        )

    if bill_amount is None:
        return OfferPaymentPreview(
            offer_type=offer.offer_type,
            discount_percent=offer.discount_percent,
            item_name="",
            original_amount=None,
            discount_amount=None,
            amount_to_pay=None,
            bill_amount=None,
            requires_bill_amount=True,
        )

    bill = Decimal(str(bill_amount))
    discount = _quantize_money(bill * offer.discount_percent / Decimal("100"))
    amount_to_pay = _quantize_money(bill - discount)
    return OfferPaymentPreview(
        offer_type=offer.offer_type,
        discount_percent=offer.discount_percent,
        item_name="",
        original_amount=bill,
        discount_amount=discount,
        amount_to_pay=amount_to_pay,
        bill_amount=bill,
        requires_bill_amount=True,
    )
