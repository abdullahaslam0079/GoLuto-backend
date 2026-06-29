import uuid
from decimal import Decimal

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class AccountType(models.TextChoices):
        CONSUMER = "consumer", "Consumer"
        BUSINESS = "business", "Business"

    username = None
    email = models.EmailField(unique=True)
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.CONSUMER,
    )
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    @property
    def is_business_account(self) -> bool:
        return self.account_type == self.AccountType.BUSINESS

    def __str__(self) -> str:
        return self.email


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self) -> str:
        return self.name


class Business(models.Model):
    owner = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="business_profile"
    )
    name = models.CharField(max_length=120)
    logo = models.ImageField(upload_to="business_logos/", null=True, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="businesses"
    )

    def __str__(self) -> str:
        return self.name


class Branch(models.Model):
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="branches"
    )
    name = models.CharField(max_length=120)
    street = models.CharField(max_length=120)
    house_number = models.CharField(max_length=20)
    postal_code = models.CharField(max_length=20)
    city = models.CharField(max_length=80)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        verbose_name_plural = "branches"
        ordering = ["name", "id"]

    @property
    def formatted_address(self) -> str:
        return f"{self.street} {self.house_number}, {self.postal_code} {self.city}"

    def __str__(self) -> str:
        return f"{self.business.name} - {self.name}"


class Offer(models.Model):
    class OfferType(models.TextChoices):
        PERCENTAGE_BILL = "percentage_bill", "Percentage off entire bill"
        ITEM = "item", "Item or service discount"

    class UsageLimitType(models.TextChoices):
        ONE_TIME = "one_time", "One time only"
        ONCE_PER_WEEK = "once_per_week", "Once per week"
        ONCE_PER_MONTH = "once_per_month", "Once per month"
        N_TIMES_PER_WEEK = "n_times_per_week", "N times per week"
        N_TIMES_PER_MONTH = "n_times_per_month", "N times per month"
        N_TIMES_TOTAL = "n_times_total", "N times total"

    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="offers"
    )
    branches = models.ManyToManyField(Branch, related_name="offers")
    offer_type = models.CharField(max_length=20, choices=OfferType.choices)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="offer_images/", null=True, blank=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    item_name = models.CharField(max_length=120, blank=True)
    original_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    discounted_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    usage_limit_type = models.CharField(max_length=20, choices=UsageLimitType.choices)
    usage_limit_count = models.PositiveIntegerField(default=1)
    is_enabled = models.BooleanField(default=True)
    is_time_limited = models.BooleanField(default=False)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    qr_code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    @staticmethod
    def compute_discount_percent(
        original_price: Decimal, discounted_price: Decimal
    ) -> Decimal:
        if original_price <= 0:
            return Decimal("0.00")
        percent = (original_price - discounted_price) / original_price * Decimal("100")
        return percent.quantize(Decimal("0.01"))

    @property
    def is_active(self) -> bool:
        if not self.is_enabled:
            return False
        if not self.is_time_limited:
            return True

        now = timezone.now()
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True

    def __str__(self) -> str:
        return f"{self.business.name} - {self.title}"


class OfferBranchStats(models.Model):
    offer = models.ForeignKey(
        Offer, on_delete=models.CASCADE, related_name="branch_stats"
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="offer_stats"
    )
    scan_count = models.PositiveIntegerField(default=0)
    avail_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "offer branch stats"
        constraints = [
            models.UniqueConstraint(
                fields=["offer", "branch"], name="unique_offer_branch_stats"
            )
        ]

    def __str__(self) -> str:
        return f"{self.offer.title} @ {self.branch.name}"


class OfferScan(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="scans")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="scans")
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offer_scans",
    )
    bill_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    original_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    amount_to_pay = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scanned_at"]

    def __str__(self) -> str:
        return f"Scan<{self.offer_id}@{self.branch_id}>"


class OfferRedemption(models.Model):
    offer = models.ForeignKey(
        Offer, on_delete=models.CASCADE, related_name="redemptions"
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="redemptions"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="offer_redemptions"
    )
    bill_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    original_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    amount_to_pay = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-redeemed_at"]
        indexes = [
            models.Index(
                fields=["user", "offer", "redeemed_at"],
                name="offer_redemp_user_offer_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Redemption<{self.offer_id}@{self.branch_id}>"


class UserPreferences(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="preferences"
    )
    notifications_enabled = models.BooleanField(default=True)
    preferred_categories = models.ManyToManyField(Category, blank=True)

    def __str__(self) -> str:
        return f"Preferences<{self.user.email}>"


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    street = models.CharField(max_length=120)
    house_number = models.CharField(max_length=20)
    postal_code = models.CharField(max_length=20)
    city = models.CharField(max_length=80)
    county = models.CharField(max_length=80)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "addresses"

    @property
    def formatted_address(self) -> str:
        return f"{self.street} {self.house_number}, {self.postal_code} {self.city}"

    def __str__(self) -> str:
        return self.formatted_address


class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="password_reset_tokens"
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["user", "used_at"]),
        ]

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and timezone.now() < self.expires_at

    def mark_used(self) -> None:
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])

    def __str__(self) -> str:
        return f"PasswordReset<{self.user.email}>"
