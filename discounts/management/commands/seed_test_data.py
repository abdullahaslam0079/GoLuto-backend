import os
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from discounts.models import Address, Branch, Business, Category, Offer, UserPreferences
from discounts.seed_utils import (
    DEMO_BUSINESS_PASSWORD,
    LIVE_BUSINESSES,
    LIVE_CATEGORIES,
    generate_seed_image,
)


class Command(BaseCommand):
    help = "Seed categories, demo businesses, branches, offers, and test user data"

    def handle(self, *args, **options):
        if os.environ.get("RENDER") and not os.environ.get("SEED_TEST_DATA", "").lower() in (
            "true",
            "1",
            "yes",
        ):
            return

        user_model = get_user_model()
        categories = self._seed_categories()
        business_count = self._seed_businesses(user_model, categories)
        self._seed_consumer_user(user_model, categories)

        self._log(self.style.SUCCESS("Seed data created/updated successfully."))
        self._log(f"Categories: {len(categories)} | Demo businesses: {business_count}")
        self._log("Consumer -> testuser@example.com / testpass123")
        self._log(f"Demo businesses -> demo-<slug>@goluto.app / {DEMO_BUSINESS_PASSWORD}")

    def _seed_categories(self) -> dict[str, Category]:
        categories = {}
        for name in LIVE_CATEGORIES:
            category, _ = Category.objects.get_or_create(name=name)
            categories[name] = category
        return categories

    def _seed_businesses(self, user_model, categories: dict[str, Category]) -> int:
        count = 0
        for payload in LIVE_BUSINESSES:
            email = f"demo-{payload['slug']}@goluto.app"
            owner, _ = user_model.objects.get_or_create(
                email=email,
                defaults={"account_type": user_model.AccountType.BUSINESS},
            )
            owner.account_type = user_model.AccountType.BUSINESS
            owner.set_password(DEMO_BUSINESS_PASSWORD)
            owner.save(update_fields=["password", "account_type"])

            business, _ = Business.objects.get_or_create(
                owner=owner,
                defaults={
                    "name": payload["name"],
                    "category": categories[payload["category"]],
                },
            )
            business.name = payload["name"]
            business.category = categories[payload["category"]]
            business.logo.save(
                f"{payload['slug']}-logo.png",
                generate_seed_image(
                    payload["name"],
                    payload["category"],
                    f"{payload['slug']}-logo.png",
                ),
                save=False,
            )
            business.save(update_fields=["name", "category", "logo"])

            branch_objects = []
            for branch_name, street, house_number, postal_code, city, lat, lng in payload[
                "branches"
            ]:
                branch, _ = Branch.objects.update_or_create(
                    business=business,
                    name=branch_name,
                    defaults={
                        "street": street,
                        "house_number": house_number,
                        "postal_code": postal_code,
                        "city": city,
                        "latitude": Decimal(lat),
                        "longitude": Decimal(lng),
                    },
                )
                branch_objects.append(branch)

            for index, offer_data in enumerate(payload["offers"], start=1):
                (
                    offer_type,
                    title,
                    description,
                    discount_percent,
                    item_name,
                    original_price,
                    discounted_price,
                ) = offer_data

                defaults = {
                    "offer_type": offer_type,
                    "description": description,
                    "usage_limit_type": Offer.UsageLimitType.ONE_TIME,
                    "usage_limit_count": 1,
                    "is_enabled": True,
                    "is_time_limited": False,
                    "starts_at": None,
                    "ends_at": None,
                    "item_name": "",
                    "original_price": None,
                    "discounted_price": None,
                }

                if offer_type == Offer.OfferType.PERCENTAGE_BILL:
                    defaults["discount_percent"] = Decimal(discount_percent)
                else:
                    original = Decimal(original_price)
                    discounted = Decimal(discounted_price)
                    defaults.update(
                        {
                            "item_name": item_name,
                            "original_price": original,
                            "discounted_price": discounted,
                            "discount_percent": Offer.compute_discount_percent(
                                original, discounted
                            ),
                        }
                    )

                offer, _ = Offer.objects.update_or_create(
                    business=business,
                    title=title,
                    defaults=defaults,
                )
                offer.image.save(
                    f"{payload['slug']}-offer-{index}.png",
                    generate_seed_image(
                        title,
                        payload["name"],
                        f"{payload['slug']}-offer-{index}.png",
                    ),
                    save=True,
                )
                offer.branches.set(branch_objects)

            count += 1
        return count

    def _seed_consumer_user(self, user_model, categories: dict[str, Category]) -> None:
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
            [categories["Food"], categories["Fashion"], categories["Electronics"]]
        )

    def _log(self, message: str) -> None:
        self.stderr.write(message + "\n")
