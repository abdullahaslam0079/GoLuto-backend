from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Address, Branch, Business, Category, Offer, PasswordResetToken, UserPreferences
from .offer_utils import build_media_url, get_highest_discount_active_offer

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        write_only=True,
        max_length=301,
        trim_whitespace=True,
        error_messages={
            "required": "Full name is required.",
            "blank": "Full name cannot be empty.",
        },
    )
    email = serializers.EmailField(
        error_messages={
            "required": "Email is required.",
            "blank": "Email cannot be empty.",
            "invalid": "Enter a valid email address.",
        }
    )
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        error_messages={
            "required": "Password is required.",
            "blank": "Password cannot be empty.",
        },
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        error_messages={
            "required": "Password confirmation is required.",
            "blank": "Password confirmation cannot be empty.",
        },
    )

    class Meta:
        model = User
        fields = ("name", "email", "password", "password_confirm")

    def validate_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Full name is required.")
        return value.strip()

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return email

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        email = validated_data.pop("email")
        name = validated_data.pop("name")
        first_name, _, last_name = name.partition(" ")
        return User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            **validated_data,
        )


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class OfferSerializer(serializers.ModelSerializer):
    business_id = serializers.IntegerField(source="business.id", read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)
    category_id = serializers.IntegerField(source="business.category.id", read_only=True)
    category_name = serializers.CharField(
        source="business.category.name", read_only=True
    )
    category = CategorySerializer(source="business.category", read_only=True)
    branch_ids = serializers.PrimaryKeyRelatedField(
        many=True, source="branches", read_only=True
    )
    is_active = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = [
            "id",
            "business_id",
            "business_name",
            "category_id",
            "category_name",
            "category",
            "branch_ids",
            "offer_type",
            "title",
            "description",
            "image_url",
            "discount_percent",
            "item_name",
            "original_price",
            "discounted_price",
            "usage_limit_type",
            "usage_limit_count",
            "is_enabled",
            "is_time_limited",
            "starts_at",
            "ends_at",
            "qr_code",
            "is_active",
        ]

    def get_is_active(self, obj: Offer) -> bool:
        return obj.is_active

    def get_image_url(self, obj: Offer) -> str | None:
        if not obj.image:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url


class MapBranchSerializer(serializers.ModelSerializer):
    business_id = serializers.IntegerField(source="business.id", read_only=True)
    business_name = serializers.CharField(source="business.name", read_only=True)
    business_logo_url = serializers.SerializerMethodField()
    category_id = serializers.IntegerField(source="business.category.id", read_only=True)
    category_name = serializers.CharField(source="business.category.name", read_only=True)
    category = CategorySerializer(source="business.category", read_only=True)
    highest_discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    highest_discount_offer_image_url = serializers.SerializerMethodField()
    formattedAddress = serializers.CharField(source="formatted_address", read_only=True)

    class Meta:
        model = Branch
        fields = [
            "id",
            "business_id",
            "business_name",
            "business_logo_url",
            "category_id",
            "category_name",
            "category",
            "name",
            "latitude",
            "longitude",
            "formattedAddress",
            "highest_discount_percent",
            "highest_discount_offer_image_url",
        ]

    def get_business_logo_url(self, obj: Branch) -> str | None:
        return build_media_url(self.context.get("request"), obj.business.logo)

    def get_highest_discount_offer_image_url(self, obj: Branch) -> str | None:
        top_offer = get_highest_discount_active_offer(obj)
        if top_offer is None:
            return None
        return build_media_url(self.context.get("request"), top_offer.image)


class MapBusinessSerializer(serializers.ModelSerializer):
    """Legacy alias kept for backward compatibility; map data is branch-based."""

    highest_discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Business
        fields = [
            "id",
            "name",
            "category_name",
            "highest_discount_percent",
        ]


class LoginUserSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "name")

    def get_id(self, obj: User) -> str:
        return str(obj.pk)

    def get_name(self, obj: User) -> str:
        return obj.get_full_name().strip()


class AddressSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    street = serializers.CharField(
        error_messages={
            "required": "Street is required.",
            "blank": "Street cannot be empty.",
        }
    )
    houseNumber = serializers.CharField(
        source="house_number",
        error_messages={
            "required": "House number is required.",
            "blank": "House number cannot be empty.",
        },
    )
    postalCode = serializers.CharField(
        source="postal_code",
        error_messages={
            "required": "Postal code is required.",
            "blank": "Postal code cannot be empty.",
        },
    )
    city = serializers.CharField(
        error_messages={
            "required": "City is required.",
            "blank": "City cannot be empty.",
        }
    )
    county = serializers.CharField(
        error_messages={
            "required": "County is required.",
            "blank": "County cannot be empty.",
        }
    )
    isDefault = serializers.BooleanField(
        source="is_default", required=False, default=False
    )
    formattedAddress = serializers.CharField(source="formatted_address", read_only=True)
    latitude = serializers.FloatField(
        error_messages={
            "required": "Latitude is required.",
            "invalid": "Latitude must be a valid number.",
        }
    )
    longitude = serializers.FloatField(
        error_messages={
            "required": "Longitude is required.",
            "invalid": "Longitude must be a valid number.",
        }
    )

    class Meta:
        model = Address
        fields = [
            "id",
            "street",
            "houseNumber",
            "postalCode",
            "city",
            "county",
            "latitude",
            "longitude",
            "isDefault",
            "formattedAddress",
        ]

    def validate_latitude(self, value: float) -> float:
        if value < -90 or value > 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value: float) -> float:
        if value < -180 or value > 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

    def get_id(self, obj: Address) -> str:
        return f"addr_{obj.pk}"

    def _apply_default_logic(self, user, is_default: bool, exclude_pk: int | None = None):
        if is_default:
            queryset = user.addresses.filter(is_default=True)
            if exclude_pk is not None:
                queryset = queryset.exclude(pk=exclude_pk)
            queryset.update(is_default=False)
            return True

        queryset = user.addresses
        if exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)
        if not queryset.filter(is_default=True).exists():
            next_address = queryset.order_by("id").first()
            if next_address:
                next_address.is_default = True
                next_address.save(update_fields=["is_default"])
                return False
        return is_default

    def create(self, validated_data):
        user = self.context["request"].user
        is_default = validated_data.get("is_default", False)
        if is_default:
            user.addresses.filter(is_default=True).update(is_default=False)
        elif not user.addresses.exists():
            validated_data["is_default"] = True
        return Address.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user = self.context["request"].user
        is_default = validated_data.get("is_default", instance.is_default)

        if "is_default" in validated_data and not is_default and instance.is_default:
            other_addresses = user.addresses.exclude(pk=instance.pk)
            if not other_addresses.exists():
                validated_data["is_default"] = True
            else:
                self._apply_default_logic(user, is_default=False, exclude_pk=instance.pk)
        elif is_default and not instance.is_default:
            self._apply_default_logic(user, is_default=True, exclude_pk=instance.pk)

        return super().update(instance, validated_data)


class LoginTokenObtainPairSerializer(TokenObtainPairSerializer):
    default_error_messages = {
        "no_active_account": "Invalid email or password.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"] = serializers.EmailField(
            error_messages={
                "required": "Email is required.",
                "blank": "Email cannot be empty.",
                "invalid": "Enter a valid email address.",
            }
        )
        self.fields["password"].error_messages = {
            "required": "Password is required.",
            "blank": "Password cannot be empty.",
        }

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        if user.is_business_account:
            raise serializers.ValidationError(
                {"email": "Please use the business login endpoint for business accounts."}
            )
        data.pop("refresh", None)
        data["user"] = LoginUserSerializer(user).data
        data["addresses"] = AddressSerializer(
            user.addresses.order_by("-is_default", "id"), many=True
        ).data
        return data


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(
        error_messages={
            "required": "Email is required.",
            "blank": "Email cannot be empty.",
            "invalid": "Enter a valid email address.",
        }
    )

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.UUIDField(
        error_messages={
            "required": "Reset token is required.",
            "invalid": "Enter a valid reset token.",
        }
    )
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        error_messages={
            "required": "Password is required.",
            "blank": "Password cannot be empty.",
        },
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        error_messages={
            "required": "Password confirmation is required.",
            "blank": "Password confirmation cannot be empty.",
        },
    )

    def validate_token(self, value):
        try:
            reset_token = PasswordResetToken.objects.select_related("user").get(
                token=value
            )
        except PasswordResetToken.DoesNotExist as exc:
            raise serializers.ValidationError(
                "Invalid or expired reset token."
            ) from exc
        if not reset_token.is_valid:
            raise serializers.ValidationError("Invalid or expired reset token.")
        self.context["reset_token"] = reset_token
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        user = self.context["reset_token"].user
        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def save(self, **kwargs):
        reset_token = self.context["reset_token"]
        user = reset_token.user
        user.set_password(self.validated_data["password"])
        user.save(update_fields=["password"])
        reset_token.mark_used()
        return user


class UserPreferencesSerializer(serializers.ModelSerializer):
    preferred_categories = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.all()
    )
    preferred_category_details = CategorySerializer(
        source="preferred_categories", many=True, read_only=True
    )

    class Meta:
        model = UserPreferences
        fields = [
            "notifications_enabled",
            "preferred_categories",
            "preferred_category_details",
        ]
