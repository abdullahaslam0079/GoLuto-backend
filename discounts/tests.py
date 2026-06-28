from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Branch, Business, Category, Offer, OfferRedemption
from .offer_utils import can_user_redeem_offer, get_user_offer_usage_status

User = get_user_model()


class OfferUsageLimitTests(TestCase):
    def setUp(self):
        self.consumer = User.objects.create_user(
            email="consumer@example.com",
            password="testpass123",
            account_type=User.AccountType.CONSUMER,
        )
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="testpass123",
            account_type=User.AccountType.BUSINESS,
        )
        self.category = Category.objects.create(name="Food")
        self.business = Business.objects.create(
            owner=self.owner,
            name="Test Cafe",
            category=self.category,
        )
        self.branch_a = Branch.objects.create(
            business=self.business,
            name="Branch A",
            street="Main",
            house_number="1",
            postal_code="10001",
            city="Berlin",
            latitude=Decimal("52.520008"),
            longitude=Decimal("13.404954"),
        )
        self.branch_b = Branch.objects.create(
            business=self.business,
            name="Branch B",
            street="Side",
            house_number="2",
            postal_code="10002",
            city="Berlin",
            latitude=Decimal("52.530008"),
            longitude=Decimal("13.414954"),
        )
        self.offer = Offer.objects.create(
            business=self.business,
            offer_type=Offer.OfferType.PERCENTAGE_BILL,
            title="One Time Deal",
            description="10% off",
            discount_percent=Decimal("10.00"),
            usage_limit_type=Offer.UsageLimitType.ONE_TIME,
            usage_limit_count=1,
        )
        self.offer.branches.set([self.branch_a, self.branch_b])

    def test_one_time_limit_applies_across_branches(self):
        OfferRedemption.objects.create(
            offer=self.offer,
            branch=self.branch_a,
            user=self.consumer,
        )

        can_redeem, message = can_user_redeem_offer(
            self.consumer, self.offer, self.branch_b
        )
        self.assertFalse(can_redeem)
        self.assertIn("already used", message.lower())

    def test_once_per_month_blocks_second_redemption(self):
        self.offer.usage_limit_type = Offer.UsageLimitType.ONCE_PER_MONTH
        self.offer.save(update_fields=["usage_limit_type"])

        OfferRedemption.objects.create(
            offer=self.offer,
            branch=self.branch_a,
            user=self.consumer,
        )

        usage = get_user_offer_usage_status(self.consumer, self.offer)
        self.assertEqual(usage.redemption_count, 1)
        self.assertEqual(usage.remaining_uses, 0)
        self.assertFalse(usage.is_available_for_user)
        self.assertIsNotNone(usage.period_resets_at)

    def test_weekly_limit_resets_after_period(self):
        self.offer.usage_limit_type = Offer.UsageLimitType.ONCE_PER_WEEK
        self.offer.save(update_fields=["usage_limit_type"])

        old_redemption = OfferRedemption.objects.create(
            offer=self.offer,
            branch=self.branch_a,
            user=self.consumer,
        )
        OfferRedemption.objects.filter(pk=old_redemption.pk).update(
            redeemed_at=timezone.now() - timedelta(days=8)
        )

        usage = get_user_offer_usage_status(self.consumer, self.offer)
        self.assertEqual(usage.redemption_count, 0)
        self.assertTrue(usage.is_available_for_user)


class OfferRedeemAPITests(APITestCase):
    def setUp(self):
        self.consumer = User.objects.create_user(
            email="consumer@example.com",
            password="testpass123",
            account_type=User.AccountType.CONSUMER,
        )
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="testpass123",
            account_type=User.AccountType.BUSINESS,
        )
        self.category = Category.objects.create(name="Food")
        self.business = Business.objects.create(
            owner=self.owner,
            name="Test Cafe",
            category=self.category,
        )
        self.branch = Branch.objects.create(
            business=self.business,
            name="Main Branch",
            street="Main",
            house_number="1",
            postal_code="10001",
            city="Berlin",
            latitude=Decimal("52.520008"),
            longitude=Decimal("13.404954"),
        )
        self.offer = Offer.objects.create(
            business=self.business,
            offer_type=Offer.OfferType.PERCENTAGE_BILL,
            title="One Time Deal",
            description="10% off",
            discount_percent=Decimal("10.00"),
            usage_limit_type=Offer.UsageLimitType.ONE_TIME,
            usage_limit_count=1,
        )
        self.offer.branches.add(self.branch)
        self.client.force_authenticate(user=self.consumer)

    def test_redeem_returns_usage_status(self):
        response = self.client.post(
            f"/api/offers/{self.offer.id}/redeem",
            {
                "branch_id": self.branch.id,
                "qr_code": str(self.offer.qr_code),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_redemption_count"], 1)
        self.assertEqual(response.data["user_remaining_uses"], 0)
        self.assertFalse(response.data["is_available_for_user"])

    def test_second_redeem_is_rejected(self):
        self.client.post(
            f"/api/offers/{self.offer.id}/redeem",
            {
                "branch_id": self.branch.id,
                "qr_code": str(self.offer.qr_code),
            },
            format="json",
        )
        response = self.client.post(
            f"/api/offers/{self.offer.id}/redeem",
            {
                "branch_id": self.branch.id,
                "qr_code": str(self.offer.qr_code),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(OfferRedemption.objects.count(), 1)

    def test_usage_endpoint_reports_remaining_uses(self):
        OfferRedemption.objects.create(
            offer=self.offer,
            branch=self.branch,
            user=self.consumer,
        )

        response = self.client.get(f"/api/offers/{self.offer.id}/usage")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_redemption_count"], 1)
        self.assertEqual(response.data["user_remaining_uses"], 0)
        self.assertFalse(response.data["is_available_for_user"])


class LogoutAndAvailedOffersAPITests(APITestCase):
    def setUp(self):
        self.consumer = User.objects.create_user(
            email="consumer@example.com",
            password="testpass123",
            account_type=User.AccountType.CONSUMER,
        )
        self.business_user = User.objects.create_user(
            email="owner@example.com",
            password="testpass123",
            account_type=User.AccountType.BUSINESS,
        )
        self.category = Category.objects.create(name="Food")
        self.business = Business.objects.create(
            owner=self.business_user,
            name="Test Cafe",
            category=self.category,
        )
        self.branch_a = Branch.objects.create(
            business=self.business,
            name="Branch A",
            street="Main",
            house_number="1",
            postal_code="10001",
            city="Berlin",
            latitude=Decimal("52.520008"),
            longitude=Decimal("13.404954"),
        )
        self.branch_b = Branch.objects.create(
            business=self.business,
            name="Branch B",
            street="Side",
            house_number="2",
            postal_code="10002",
            city="Berlin",
            latitude=Decimal("52.530008"),
            longitude=Decimal("13.414954"),
        )
        self.offer = Offer.objects.create(
            business=self.business,
            offer_type=Offer.OfferType.PERCENTAGE_BILL,
            title="Lunch Deal",
            description="10% off",
            discount_percent=Decimal("10.00"),
            usage_limit_type=Offer.UsageLimitType.N_TIMES_TOTAL,
            usage_limit_count=5,
        )
        self.offer.branches.set([self.branch_a, self.branch_b])

    def test_consumer_logout_blacklists_tokens(self):
        login = self.client.post(
            "/api/auth/token",
            {"email": "consumer@example.com", "password": "testpass123"},
            format="json",
        )
        access = login.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = self.client.post("/api/auth/logout", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Logged out successfully", response.data["message"])

    def test_availed_offers_returns_newest_first_with_branch(self):
        older = OfferRedemption.objects.create(
            offer=self.offer,
            branch=self.branch_a,
            user=self.consumer,
        )
        newer = OfferRedemption.objects.create(
            offer=self.offer,
            branch=self.branch_b,
            user=self.consumer,
        )
        OfferRedemption.objects.filter(pk=older.pk).update(
            redeemed_at=timezone.now() - timedelta(days=2)
        )

        self.client.force_authenticate(user=self.consumer)
        response = self.client.get("/api/user/offers/availed")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["id"], newer.id)
        self.assertEqual(results[0]["branch"]["id"], self.branch_b.id)
        self.assertEqual(results[0]["branch"]["name"], "Branch B")
        self.assertEqual(results[1]["id"], older.id)
        self.assertEqual(results[1]["branch"]["id"], self.branch_a.id)
        self.assertEqual(results[0]["offer"]["title"], "Lunch Deal")

    def test_availed_offers_requires_consumer_account(self):
        self.client.force_authenticate(user=self.business_user)
        response = self.client.get("/api/user/offers/availed")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
