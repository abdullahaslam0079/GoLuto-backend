from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm

from .models import (
    Address,
    Branch,
    Business,
    Category,
    DeviceToken,
    Notification,
    Offer,
    OfferBranchStats,
    OfferEngagementStats,
    OfferGalleryImage,
    OfferLike,
    OfferRedemption,
    OfferScan,
    OfferViewEvent,
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


class OfferGalleryImageInline(admin.TabularInline):
    model = OfferGalleryImage
    extra = 1
    fields = ("image", "source_url", "sort_order")
    ordering = ("sort_order", "id")


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "business",
        "title",
        "offer_type",
        "redemption_mode",
        "discount_percent",
        "usage_limit_type",
        "is_enabled",
        "is_time_limited",
        "has_image",
    )
    list_filter = (
        "offer_type",
        "redemption_mode",
        "is_enabled",
        "is_time_limited",
        "business__category",
    )
    search_fields = ("title", "business__name", "item_name")
    filter_horizontal = ("branches",)
    exclude = ("image",)
    inlines = [OfferGalleryImageInline]

    @admin.display(boolean=True, description="Images")
    def has_image(self, obj):
        return obj.gallery_images.exists() or bool(obj.image)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            # M2M branches are not available until save_related; notify there.
            obj._notify_on_create = True

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        offer = form.instance
        first = offer.gallery_images.order_by("sort_order", "id").first()
        offer.image = first.image.name if first else None
        offer.save(update_fields=["image"])
        if getattr(offer, "_notify_on_create", False):
            from .notification_utils import notify_favorited_business_new_offer

            notify_favorited_business_new_offer(offer)
            offer._notify_on_create = False


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


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "platform", "updated_at")
    list_filter = ("platform",)
    search_fields = ("user__email", "token")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "type", "title", "read_at", "created_at")
    list_filter = ("type",)
    search_fields = ("user__email", "title", "body")
    readonly_fields = ("created_at",)


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
