from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Q

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
    list_display = (
        "email",
        "phone",
        "account_type",
        "is_staff",
        "is_active",
        "is_superuser",
    )
    search_fields = ("email", "phone", "firebase_uid")
    list_filter = ("account_type", "is_staff", "is_superuser", "is_active")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Phone auth", {"fields": ("phone", "firebase_uid")}),
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
        "is_online",
        "discount_percent",
        "usage_limit_type",
        "is_enabled",
        "is_time_limited",
        "has_image",
        "view_count",
        "like_count",
        "unique_viewers",
    )
    list_filter = (
        "offer_type",
        "redemption_mode",
        "is_online",
        "is_enabled",
        "is_time_limited",
        "business__category",
    )
    search_fields = ("title", "business__name", "item_name")
    filter_horizontal = ("branches",)
    exclude = ("image",)
    inlines = [OfferGalleryImageInline]
    list_select_related = ("business", "engagement_stats")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("engagement_stats").annotate(
            annotated_unique_viewers=Count(
                "view_events__user",
                distinct=True,
                filter=Q(view_events__user__isnull=False),
            )
        )

    @admin.display(boolean=True, description="Images")
    def has_image(self, obj):
        return obj.gallery_images.exists() or bool(obj.image)

    @admin.display(description="Views", ordering="engagement_stats__view_count")
    def view_count(self, obj):
        try:
            return obj.engagement_stats.view_count
        except ObjectDoesNotExist:
            return 0

    @admin.display(description="Likes", ordering="engagement_stats__like_count")
    def like_count(self, obj):
        try:
            return obj.engagement_stats.like_count
        except ObjectDoesNotExist:
            return 0

    @admin.display(description="Unique viewers", ordering="annotated_unique_viewers")
    def unique_viewers(self, obj):
        return int(getattr(obj, "annotated_unique_viewers", 0) or 0)

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


@admin.register(OfferEngagementStats)
class OfferEngagementStatsAdmin(admin.ModelAdmin):
    list_display = ("offer", "view_count", "like_count")
    search_fields = ("offer__title", "offer__business__name")
    readonly_fields = ("offer", "view_count", "like_count")


@admin.register(OfferViewEvent)
class OfferViewEventAdmin(admin.ModelAdmin):
    list_display = ("offer", "user", "viewed_on")
    list_filter = ("viewed_on",)
    search_fields = ("offer__title", "user__email")
    readonly_fields = ("offer", "user", "viewed_on")


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
    list_display = ("id", "user", "notifications_enabled", "theme_preference")
    list_filter = ("theme_preference", "notifications_enabled")


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
