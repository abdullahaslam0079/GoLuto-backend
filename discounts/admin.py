from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm

from .models import (
    Address,
    Branch,
    Business,
    Category,
    Offer,
    OfferBranchStats,
    OfferRedemption,
    OfferScan,
    User,
    UserPreferences,
)


class UserCreationForm(BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("email",)


class UserChangeForm(BaseUserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    ordering = ("email",)
    list_display = ("email", "account_type", "is_staff", "is_active", "is_superuser")
    search_fields = ("email",)
    list_filter = ("account_type", "is_staff", "is_superuser", "is_active")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Account", {"fields": ("account_type",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "account_type"),
            },
        ),
    )

    filter_horizontal = ("groups", "user_permissions")


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "category")
    list_filter = ("category",)
    search_fields = ("name", "owner__email")
    inlines = [BranchInline]


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "business", "city", "latitude", "longitude")
    list_filter = ("city", "business__category")
    search_fields = ("name", "business__name", "city")


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "business",
        "title",
        "offer_type",
        "discount_percent",
        "usage_limit_type",
        "is_enabled",
        "is_time_limited",
        "has_image",
    )
    list_filter = ("offer_type", "is_enabled", "is_time_limited", "business__category")
    search_fields = ("title", "business__name", "item_name")
    filter_horizontal = ("branches",)

    @admin.display(boolean=True, description="Image")
    def has_image(self, obj):
        return bool(obj.image)


@admin.register(OfferBranchStats)
class OfferBranchStatsAdmin(admin.ModelAdmin):
    list_display = ("offer", "branch", "scan_count", "avail_count")


@admin.register(OfferScan)
class OfferScanAdmin(admin.ModelAdmin):
    list_display = ("offer", "branch", "user", "scanned_at")


@admin.register(OfferRedemption)
class OfferRedemptionAdmin(admin.ModelAdmin):
    list_display = ("offer", "branch", "user", "redeemed_at")


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "notifications_enabled")


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "street",
        "house_number",
        "city",
        "is_default",
    )
    list_filter = ("is_default", "city")
    search_fields = ("user__email", "street", "city")
