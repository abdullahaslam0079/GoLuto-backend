import uuid

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
    username = None
    email = models.EmailField(unique=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self) -> str:
        return self.email


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self) -> str:
        return self.name


class Business(models.Model):
    name = models.CharField(max_length=120)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="businesses"
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    def __str__(self) -> str:
        return self.name


class Offer(models.Model):
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="offers"
    )
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2)
    is_enabled = models.BooleanField(default=True)
    is_time_limited = models.BooleanField(default=False)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

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
