import os

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from discounts.models import Address, Branch, Business, Category, Offer, UserPreferences


class Command(BaseCommand):
    help = "Seed development test data for Discount Discovery API"

    def handle(self, *args, **options):
        if os.environ.get("RENDER") and not os.environ.get("SEED_TEST_DATA", "").lower() in (
            "true",
            "1",
            "yes",
        ):
            return

        now = timezone.now()
        user_model = get_user_model()

        categories = {}
        for name in ["Food", "Fashion", "Electronics"]:
            category, _ = Category.objects.get_or_create(name=name)
            categories[name] = category

        businesses = {}
        business_payloads = [
            (
                "Burger Hub",
                "Food",
                "burgerhub@example.com",
                Decimal("24.860734"),
                Decimal("67.001137"),
            ),
            (
                "Style Corner",
                "Fashion",
                "stylecorner@example.com",
                Decimal("24.874100"),
                Decimal("67.032500"),
            ),
            (
                "Gadget Point",
                "Electronics",
                "gadgetpoint@example.com",
                Decimal("24.905600"),
                Decimal("67.082200"),
            ),
        ]
        for name, category_name, email, latitude, longitude in business_payloads:
            owner, _ = user_model.objects.get_or_create(
                email=email,
                defaults={"account_type": user_model.AccountType.BUSINESS},
            )
            owner.account_type = user_model.AccountType.BUSINESS
            owner.set_password("businesspass123")
            owner.save(update_fields=["password", "account_type"])

            business, _ = Business.objects.get_or_create(
                owner=owner,
                defaults={
                    "name": name,
                    "category": categories[category_name],
                },
            )
            business.name = name
            business.category = categories[category_name]
            business.save(update_fields=["name", "category"])

            branch, _ = Branch.objects.get_or_create(
                business=business,
                name=f"{name} Main Branch",
                defaults={
                    "street": "Main Street",
                    "house_number": "1",
                    "postal_code": "75500",
                    "city": "Karachi",
                    "latitude": latitude,
                    "longitude": longitude,
                },
            )
            businesses[name] = {"business": business, "branch": branch}

        burger = businesses["Burger Hub"]
        offer, _ = Offer.objects.update_or_create(
            business=burger["business"],
            title="Lunch Deal",
            defaults={
                "offer_type": Offer.OfferType.PERCENTAGE_BILL,
                "description": "Flat 30% off on the entire bill.",
                "discount_percent": Decimal("30.00"),
                "usage_limit_type": Offer.UsageLimitType.ONE_TIME,
                "usage_limit_count": 1,
                "is_enabled": True,
                "is_time_limited": False,
                "starts_at": None,
                "ends_at": None,
            },
        )
        offer.branches.set([burger["branch"]])

        style = businesses["Style Corner"]
        offer, _ = Offer.objects.update_or_create(
            business=style["business"],
            title="Weekend Fashion Sale",
            defaults={
                "offer_type": Offer.OfferType.PERCENTAGE_BILL,
                "description": "25% off this weekend only.",
                "discount_percent": Decimal("25.00"),
                "usage_limit_type": Offer.UsageLimitType.ONCE_PER_WEEK,
                "usage_limit_count": 1,
                "is_enabled": True,
                "is_time_limited": True,
                "starts_at": now - timedelta(days=1),
                "ends_at": now + timedelta(days=2),
            },
        )
        offer.branches.set([style["branch"]])

        gadget = businesses["Gadget Point"]
        offer, _ = Offer.objects.update_or_create(
            business=gadget["business"],
            title="Doner Kebab Special",
            defaults={
                "offer_type": Offer.OfferType.ITEM,
                "description": "Doner kebab at a special price.",
                "item_name": "Doner Kebab",
                "original_price": Decimal("7.00"),
                "discounted_price": Decimal("4.00"),
                "discount_percent": Offer.compute_discount_percent(
                    Decimal("7.00"), Decimal("4.00")
                ),
                "usage_limit_type": Offer.UsageLimitType.N_TIMES_TOTAL,
                "usage_limit_count": 2,
                "is_enabled": True,
                "is_time_limited": True,
                "starts_at": now - timedelta(days=5),
                "ends_at": now - timedelta(days=1),
            },
        )
        offer.branches.set([gadget["branch"]])

        test_user, _ = user_model.objects.get_or_create(
            email="testuser@example.com",
            defaults={"first_name": "John", "last_name": "Doe"},
        )
        test_user.set_password("testpass123")
        test_user.first_name = "John"
        test_user.last_name = "Doe"
        test_user.account_type = user_model.AccountType.CONSUMER
        test_user.save(update_fields=["password", "first_name", "last_name", "account_type"])

        Address.objects.update_or_create(
            user=test_user,
            street="Musterstraße",
            house_number="12",
            defaults={
                "postal_code": "10115",
                "city": "Berlin",
                "county": "Germany",
                "latitude": Decimal("52.520008"),
                "longitude": Decimal("13.404954"),
                "is_default": True,
            },
        )

        preferences, _ = UserPreferences.objects.get_or_create(user=test_user)
        preferences.notifications_enabled = True
        preferences.save(update_fields=["notifications_enabled"])
        preferences.preferred_categories.set(
            [categories["Food"], categories["Fashion"]]
        )

        self._log(self.style.SUCCESS("Seed data created/updated successfully."))
        self._log("Test user -> email: testuser@example.com, password: testpass123")
        self._log(
            "Business logins -> burgerhub@example.com / stylecorner@example.com / "
            "gadgetpoint@example.com, password: businesspass123"
        )

    def _log(self, message: str) -> None:
        self.stderr.write(message + "\n")
