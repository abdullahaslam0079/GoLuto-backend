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

    class RedemptionMode(models.TextChoices):
        SCANNABLE = "scannable", "Scannable"
        VIEW_ONLY = "view_only", "View only"

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
    redemption_mode = models.CharField(
        max_length=20,
        choices=RedemptionMode.choices,
        default=RedemptionMode.SCANNABLE,
    )
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    detailed_description = models.TextField(blank=True)
    external_url = models.URLField(max_length=500, blank=True)
    external_url_label = models.CharField(max_length=80, blank=True)
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


class OfferGalleryImage(models.Model):
    offer = models.ForeignKey(
        Offer, on_delete=models.CASCADE, related_name="gallery_images"
    )
    image = models.ImageField(upload_to="offer_gallery/", null=True, blank=True)
    source_url = models.URLField(max_length=1000, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"Gallery<{self.offer_id}:{self.id}>"


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


class OfferEngagementStats(models.Model):
    offer = models.OneToOneField(
        Offer, on_delete=models.CASCADE, related_name="engagement_stats"
    )
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"OfferStats<{self.offer_id}>"


class BusinessEngagementStats(models.Model):
    business = models.OneToOneField(
        Business, on_delete=models.CASCADE, related_name="engagement_stats"
    )
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"BusinessStats<{self.business_id}>"


class OfferLike(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="offer_likes"
    )
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "offer"], name="unique_offer_like_per_user"
            )
        ]

    def __str__(self) -> str:
        return f"OfferLike<{self.user_id}:{self.offer_id}>"


class BusinessLike(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="business_likes"
    )
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "business"], name="unique_business_like_per_user"
            )
        ]

    def __str__(self) -> str:
        return f"BusinessLike<{self.user_id}:{self.business_id}>"


class OfferViewEvent(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="offer_view_events",
        null=True,
        blank=True,
    )
    offer = models.ForeignKey(
        Offer, on_delete=models.CASCADE, related_name="view_events"
    )
    viewed_on = models.DateField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "offer", "viewed_on"],
                condition=models.Q(user__isnull=False),
                name="unique_offer_view_per_user_day",
            )
        ]

    def __str__(self) -> str:
        return f"OfferView<{self.offer_id}@{self.viewed_on}>"


class UserPreferences(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="preferences"
    )
    notifications_enabled = models.BooleanField(default=True)
    preferred_categories = models.ManyToManyField(Category, blank=True)

    def __str__(self) -> str:
        return f"Preferences<{self.user.email}>"


class DeviceToken(models.Model):
    class Platform(models.TextChoices):
        IOS = "ios", "iOS"
        ANDROID = "android", "Android"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="device_tokens"
    )
    token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=16, choices=Platform.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "platform"]),
        ]

    def __str__(self) -> str:
        return f"DeviceToken<{self.user_id}:{self.platform}>"


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        FAVORITED_BUSINESS_NEW_OFFER = (
            "favorited_business_new_offer",
            "Favorited business new offer",
        )
        OFFER_EXPIRING_SOON = ("offer_expiring_soon", "Offer expiring soon")
        REDEMPTION_CONFIRMATION = (
            "redemption_confirmation",
            "Redemption confirmation",
        )
        GENERIC = ("generic", "Generic")

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(
        max_length=64,
        choices=NotificationType.choices,
        default=NotificationType.GENERIC,
    )
    title = models.CharField(max_length=160)
    body = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "read_at"]),
        ]

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def mark_read(self) -> None:
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])

    def __str__(self) -> str:
        return f"Notification<{self.user_id}:{self.type}>"


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
