import os

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from discounts.models import Address, Business, Category, Offer, UserPreferences


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

        categories = {}
        for name in ["Food", "Fashion", "Electronics"]:
            category, _ = Category.objects.get_or_create(name=name)
            categories[name] = category

        businesses = {}
        business_payloads = [
            ("Burger Hub", "Food", Decimal("24.860734"), Decimal("67.001137")),
            ("Style Corner", "Fashion", Decimal("24.874100"), Decimal("67.032500")),
            (
                "Gadget Point",
                "Electronics",
                Decimal("24.905600"),
                Decimal("67.082200"),
            ),
        ]
        for name, category_name, latitude, longitude in business_payloads:
            business, _ = Business.objects.get_or_create(
                name=name,
                defaults={
                    "category": categories[category_name],
                    "latitude": latitude,
                    "longitude": longitude,
                },
            )
            if business.category_id != categories[category_name].id:
                business.category = categories[category_name]
                business.save(update_fields=["category"])
            businesses[name] = business

        # Always-active offer
        Offer.objects.update_or_create(
            business=businesses["Burger Hub"],
            title="Lunch Deal",
            defaults={
                "description": "Flat 30% off on all burgers.",
                "discount_percent": Decimal("30.00"),
                "is_enabled": True,
                "is_time_limited": False,
                "starts_at": None,
                "ends_at": None,
            },
        )

        # Active time-limited offer
        Offer.objects.update_or_create(
            business=businesses["Style Corner"],
            title="Weekend Fashion Sale",
            defaults={
                "description": "25% off this weekend only.",
                "discount_percent": Decimal("25.00"),
                "is_enabled": True,
                "is_time_limited": True,
                "starts_at": now - timedelta(days=1),
                "ends_at": now + timedelta(days=2),
            },
        )

        # Inactive (expired) offer for logic validation
        Offer.objects.update_or_create(
            business=businesses["Gadget Point"],
            title="Flash Electronics Offer",
            defaults={
                "description": "40% off, expired test offer.",
                "discount_percent": Decimal("40.00"),
                "is_enabled": True,
                "is_time_limited": True,
                "starts_at": now - timedelta(days=5),
                "ends_at": now - timedelta(days=1),
            },
        )

        user_model = get_user_model()
        test_user, _ = user_model.objects.get_or_create(
            email="testuser@example.com",
            defaults={"first_name": "John", "last_name": "Doe"},
        )
        test_user.set_password("testpass123")
        test_user.first_name = "John"
        test_user.last_name = "Doe"
        test_user.save(update_fields=["password", "first_name", "last_name"])

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
            "Categories: Food, Fashion, Electronics | "
            "Businesses: Burger Hub, Style Corner, Gadget Point | "
            "3 sample offers (2 active, 1 expired)"
        )

    def _log(self, message: str) -> None:
        self.stderr.write(message + "\n")
