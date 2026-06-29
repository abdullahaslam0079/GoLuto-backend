from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Address, Branch, Business, Category, Offer, OfferRedemption, OfferScan
from .offer_pricing import compute_offer_payment
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
                "bill_amount": "80.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_redemption_count"], 1)
        self.assertEqual(response.data["user_remaining_uses"], 0)
        self.assertFalse(response.data["is_available_for_user"])
        self.assertEqual(response.data["payment"]["amount_to_pay"], "72.00")
        self.assertEqual(response.data["payment"]["original_amount"], "80.00")
        self.assertEqual(response.data["payment"]["discount_amount"], "8.00")

    def test_second_redeem_is_rejected(self):
        self.client.post(
            f"/api/offers/{self.offer.id}/redeem",
            {
                "branch_id": self.branch.id,
                "qr_code": str(self.offer.qr_code),
                "bill_amount": "80.00",
            },
            format="json",
        )
        response = self.client.post(
            f"/api/offers/{self.offer.id}/redeem",
            {
                "branch_id": self.branch.id,
                "qr_code": str(self.offer.qr_code),
                "bill_amount": "80.00",
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


class LocationFilteringAPITests(APITestCase):
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
        self.berlin_near = Branch.objects.create(
            business=self.business,
            name="Berlin Near",
            street="Near",
            house_number="1",
            postal_code="10115",
            city="Berlin",
            latitude=Decimal("52.520008"),
            longitude=Decimal("13.404954"),
        )
        self.berlin_far = Branch.objects.create(
            business=self.business,
            name="Berlin Far",
            street="Far",
            house_number="2",
            postal_code="10117",
            city="Berlin",
            latitude=Decimal("52.560008"),
            longitude=Decimal("13.454954"),
        )
        self.munich_branch = Branch.objects.create(
            business=self.business,
            name="Munich Branch",
            street="Marienplatz",
            house_number="1",
            postal_code="80331",
            city="Munich",
            latitude=Decimal("48.137154"),
            longitude=Decimal("11.576124"),
        )
        self.berlin_offer_near = Offer.objects.create(
            business=self.business,
            offer_type=Offer.OfferType.PERCENTAGE_BILL,
            title="Berlin Near Deal",
            description="Near deal",
            discount_percent=Decimal("15.00"),
            usage_limit_type=Offer.UsageLimitType.ONE_TIME,
        )
        self.berlin_offer_near.branches.set([self.berlin_near])
        self.berlin_offer_far = Offer.objects.create(
            business=self.business,
            offer_type=Offer.OfferType.PERCENTAGE_BILL,
            title="Berlin Far Deal",
            description="Far deal",
            discount_percent=Decimal("20.00"),
            usage_limit_type=Offer.UsageLimitType.ONE_TIME,
        )
        self.berlin_offer_far.branches.set([self.berlin_far])
        self.munich_offer = Offer.objects.create(
            business=self.business,
            offer_type=Offer.OfferType.PERCENTAGE_BILL,
            title="Munich Deal",
            description="Munich deal",
            discount_percent=Decimal("25.00"),
            usage_limit_type=Offer.UsageLimitType.ONE_TIME,
        )
        self.munich_offer.branches.set([self.munich_branch])
        Address.objects.create(
            user=self.consumer,
            street="Unter den Linden",
            house_number="1",
            postal_code="10117",
            city="Berlin",
            county="Berlin",
            latitude=Decimal("52.517036"),
            longitude=Decimal("13.388860"),
            is_default=True,
        )

    def test_offers_filtered_by_default_address_city(self):
        self.client.force_authenticate(user=self.consumer)
        response = self.client.get("/api/offers")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [offer["title"] for offer in response.data]
        self.assertIn("Berlin Near Deal", titles)
        self.assertIn("Berlin Far Deal", titles)
        self.assertNotIn("Munich Deal", titles)

    def test_offers_sorted_nearest_first(self):
        self.client.force_authenticate(user=self.consumer)
        response = self.client.get("/api/offers")
        berlin_offers = [
            offer for offer in response.data if offer["title"].startswith("Berlin")
        ]
        self.assertEqual(berlin_offers[0]["title"], "Berlin Near Deal")
        self.assertLess(
            berlin_offers[0]["nearest_distance_km"],
            berlin_offers[1]["nearest_distance_km"],
        )

    def test_map_branches_filtered_by_city(self):
        self.client.force_authenticate(user=self.consumer)
        response = self.client.get("/api/map/branches")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        branch_names = [branch["name"] for branch in response.data]
        self.assertIn("Berlin Near", branch_names)
        self.assertIn("Berlin Far", branch_names)
        self.assertNotIn("Munich Branch", branch_names)

    def test_map_branches_sorted_nearest_first(self):
        self.client.force_authenticate(user=self.consumer)
        response = self.client.get("/api/map/branches")
        berlin_branches = [
            branch for branch in response.data if branch["name"].startswith("Berlin")
        ]
        self.assertEqual(berlin_branches[0]["name"], "Berlin Near")
        self.assertLess(
            berlin_branches[0]["distance_km"],
            berlin_branches[1]["distance_km"],
        )

    def test_selected_address_changes_visible_city(self):
        munich_address = Address.objects.create(
            user=self.consumer,
            street="Sendlinger",
            house_number="1",
            postal_code="80331",
            city="Munich",
            county="Bavaria",
            latitude=Decimal("48.135125"),
            longitude=Decimal("11.581981"),
        )
        self.client.force_authenticate(user=self.consumer)
        response = self.client.get(
            f"/api/offers?address_id=addr_{munich_address.id}"
        )
        titles = [offer["title"] for offer in response.data]
        self.assertIn("Munich Deal", titles)
        self.assertNotIn("Berlin Near Deal", titles)

    def test_small_town_falls_back_to_radius(self):
        nearby_branch = Branch.objects.create(
            business=self.business,
            name="Suburban Branch",
            street="Ring",
            house_number="5",
            postal_code="16515",
            city="Oranienburg",
            latitude=Decimal("52.525500"),
            longitude=Decimal("13.410500"),
        )
        nearby_offer = Offer.objects.create(
            business=self.business,
            offer_type=Offer.OfferType.PERCENTAGE_BILL,
            title="Suburban Deal",
            description="Just outside Berlin",
            discount_percent=Decimal("12.00"),
            usage_limit_type=Offer.UsageLimitType.ONE_TIME,
        )
        nearby_offer.branches.set([nearby_branch])

        self.client.force_authenticate(user=self.consumer)
        response = self.client.get(
            "/api/offers",
            {
                "latitude": "52.524000",
                "longitude": "13.405000",
                "city": "Kleinstadt",
            },
        )
        titles = [offer["title"] for offer in response.data]
        self.assertIn("Suburban Deal", titles)
        self.assertNotIn("Munich Deal", titles)


class OfferPaymentTests(TestCase):
    def setUp(self):
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
        self.item_offer = Offer.objects.create(
            business=self.business,
            offer_type=Offer.OfferType.ITEM,
            title="Burger deal",
            item_name="Classic Burger",
            original_price=Decimal("10.00"),
            discounted_price=Decimal("7.00"),
            discount_percent=Decimal("30.00"),
            usage_limit_type=Offer.UsageLimitType.ONE_TIME,
        )
        self.percent_offer = Offer.objects.create(
            business=self.business,
            offer_type=Offer.OfferType.PERCENTAGE_BILL,
            title="10% off bill",
            discount_percent=Decimal("10.00"),
            usage_limit_type=Offer.UsageLimitType.ONE_TIME,
        )

    def test_item_offer_payment_is_fixed_discounted_price(self):
        payment = compute_offer_payment(self.item_offer)
        self.assertEqual(payment.amount_to_pay, Decimal("7.00"))
        self.assertEqual(payment.original_amount, Decimal("10.00"))
        self.assertEqual(payment.discount_amount, Decimal("3.00"))
        self.assertFalse(payment.requires_bill_amount)

    def test_percentage_offer_requires_bill_amount(self):
        payment = compute_offer_payment(self.percent_offer)
        self.assertIsNone(payment.amount_to_pay)
        self.assertTrue(payment.requires_bill_amount)

    def test_percentage_offer_calculates_payment_from_bill(self):
        payment = compute_offer_payment(self.percent_offer, bill_amount=Decimal("80.00"))
        self.assertEqual(payment.original_amount, Decimal("80.00"))
        self.assertEqual(payment.discount_amount, Decimal("8.00"))
        self.assertEqual(payment.amount_to_pay, Decimal("72.00"))

    def test_item_payment_summary(self):
        payment = compute_offer_payment(self.item_offer)
        self.assertIn("€7.00", payment.summary)
        self.assertIn("Classic Burger", payment.summary)


class OfferPaymentAPITests(APITestCase):
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
        self.item_offer = Offer.objects.create(
            business=self.business,
            offer_type=Offer.OfferType.ITEM,
            title="Burger deal",
            item_name="Classic Burger",
            original_price=Decimal("10.00"),
            discounted_price=Decimal("7.00"),
            discount_percent=Decimal("30.00"),
            usage_limit_type=Offer.UsageLimitType.ONE_TIME,
        )
        self.item_offer.branches.add(self.branch)
        self.percent_offer = Offer.objects.create(
            business=self.business,
            offer_type=Offer.OfferType.PERCENTAGE_BILL,
            title="10% off bill",
            discount_percent=Decimal("10.00"),
            usage_limit_type=Offer.UsageLimitType.ONE_TIME,
        )
        self.percent_offer.branches.add(self.branch)
        self.client.force_authenticate(user=self.consumer)

    def test_item_scan_returns_amount_to_pay(self):
        response = self.client.post(
            f"/api/offers/{self.item_offer.id}/scan",
            {
                "branch_id": self.branch.id,
                "qr_code": str(self.item_offer.qr_code),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["payment"]["amount_to_pay"], "7.00")
        self.assertEqual(response.data["payment"]["original_amount"], "10.00")
        scan = OfferScan.objects.get()
        self.assertEqual(scan.amount_to_pay, Decimal("7.00"))

    def test_percentage_scan_requires_bill_amount(self):
        response = self.client.post(
            f"/api/offers/{self.percent_offer.id}/scan",
            {
                "branch_id": self.branch.id,
                "qr_code": str(self.percent_offer.qr_code),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("bill_amount", response.data["errors"])

    def test_percentage_scan_calculates_payment(self):
        response = self.client.post(
            f"/api/offers/{self.percent_offer.id}/scan",
            {
                "branch_id": self.branch.id,
                "qr_code": str(self.percent_offer.qr_code),
                "bill_amount": "80.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["payment"]["amount_to_pay"], "72.00")

    def test_payment_preview_for_item_offer(self):
        response = self.client.post(
            f"/api/offers/{self.item_offer.id}/payment-preview",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["payment"]["amount_to_pay"], "7.00")

    def test_payment_preview_for_percentage_offer(self):
        response = self.client.post(
            f"/api/offers/{self.percent_offer.id}/payment-preview",
            {"bill_amount": "50.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["payment"]["amount_to_pay"], "45.00")

    def test_by_qr_resolves_poster_offer(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(
            f"/api/offers/by-qr/{self.item_offer.qr_code}",
            {"branch_id": self.branch.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["offer"]["id"], self.item_offer.id)
        self.assertEqual(response.data["payment"]["amount_to_pay"], "7.00")
        self.assertIn("counter", response.data["payment"]["summary"].lower())
        self.assertFalse(response.data["can_avail"])

    def test_by_qr_includes_usage_when_authenticated(self):
        response = self.client.get(
            f"/api/offers/by-qr/{self.item_offer.qr_code}",
            {"branch_id": self.branch.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["can_avail"])

    def test_by_qr_percentage_without_bill_amount(self):
        response = self.client.get(
            f"/api/offers/by-qr/{self.percent_offer.qr_code}",
            {"branch_id": self.branch.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["payment"]["requires_bill_amount"])
        self.assertIsNone(response.data["payment"]["amount_to_pay"])

    def test_avail_completes_poster_flow_in_one_step(self):
        self.assertEqual(OfferRedemption.objects.filter(offer=self.item_offer).count(), 0)
        response = self.client.post(
            f"/api/offers/{self.item_offer.id}/avail",
            {
                "branch_id": self.branch.id,
                "qr_code": str(self.item_offer.qr_code),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["payment"]["amount_to_pay"], "7.00")
        self.assertIn("counter", response.data["message"].lower())
        self.assertEqual(OfferScan.objects.count(), 1)
        self.assertEqual(OfferRedemption.objects.count(), 1)
