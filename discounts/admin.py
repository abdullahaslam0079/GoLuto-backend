from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm

from .models import Business, Category, Offer, User, UserPreferences


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
    list_display = ("email", "is_staff", "is_active", "is_superuser")
    search_fields = ("email",)
    list_filter = ("is_staff", "is_superuser", "is_active")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
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
                "fields": ("email", "password1", "password2"),
            },
        ),
    )

    filter_horizontal = ("groups", "user_permissions")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "latitude", "longitude")
    list_filter = ("category",)
    search_fields = ("name",)


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "business",
        "title",
        "discount_percent",
        "is_enabled",
        "is_time_limited",
        "starts_at",
        "ends_at",
    )
    list_filter = ("is_enabled", "is_time_limited", "business__category")
    search_fields = ("title", "business__name")


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "notifications_enabled")
