from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .fields import OptionalImageField
from .models import Branch, Business, Category, Offer, OfferBranchStats
from .offer_utils import can_user_redeem_offer
from .serializers import CategorySerializer

User = get_user_model()


class BusinessRegisterSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=120,
        trim_whitespace=True,
        error_messages={
            "required": "Business name is required.",
            "blank": "Business name cannot be empty.",
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
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        required=True,
        error_messages={
            "required": "Business category is required.",
            "does_not_exist": "Selected category does not exist.",
        },
    )
    logo = OptionalImageField(required=False, allow_null=True)

    def run_validation(self, data=serializers.empty):
        if data is not serializers.empty and hasattr(data, "get"):
            payload = data.copy() if hasattr(data, "copy") else dict(data)
            logo = payload.get("logo")
            if logo in (None, "", b"", [], "null", "none", "undefined"):
                payload.pop("logo", None)
            return super().run_validation(payload)
        return super().run_validation(data)

    def validate_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Business name is required.")
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
        category = validated_data.pop("category")
        logo = validated_data.pop("logo", None)

        user = User.objects.create_user(
            email=email,
            password=password,
            account_type=User.AccountType.BUSINESS,
        )
        business = Business.objects.create(
            owner=user,
            name=name,
            category=category,
            logo=logo,
        )
        return business


class BusinessProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="owner.email", read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        required=False,
        error_messages={"does_not_exist": "Selected category does not exist."},
    )
    category_name = serializers.CharField(source="category.name", read_only=True)
    category = CategorySerializer(read_only=True)
    logo = OptionalImageField(required=False, allow_null=True, write_only=True)
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            "id",
            "name",
            "email",
            "logo",
            "logo_url",
            "category_id",
            "category_name",
            "category",
        ]
        read_only_fields = ["id", "email", "category_name", "category"]

    def run_validation(self, data=serializers.empty):
        if data is not serializers.empty and hasattr(data, "get"):
            payload = data.copy() if hasattr(data, "copy") else dict(data)
            logo = payload.get("logo")
            if logo in (None, "", b"", [], "null", "none", "undefined"):
                payload.pop("logo", None)
            return super().run_validation(payload)
        return super().run_validation(data)

    def get_logo_url(self, obj: Business) -> str | None:
        if not obj.logo:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.logo.url)
        return obj.logo.url

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["category_id"] = instance.category_id
        return data


class BusinessLoginTokenObtainPairSerializer(TokenObtainPairSerializer):
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
        if not self.user.is_business_account:
            raise serializers.ValidationError(
                {"email": "This account is not registered as a business."}
            )
        if not hasattr(self.user, "business_profile"):
            raise serializers.ValidationError(
                {"email": "Business profile not found for this account."}
            )
        data.pop("refresh", None)
        data["business"] = BusinessProfileSerializer(
            self.user.business_profile, context=self.context
        ).data
        return data


class BranchSerializer(serializers.ModelSerializer):
    formattedAddress = serializers.CharField(source="formatted_address", read_only=True)

    class Meta:
        model = Branch
        fields = [
            "id",
            "name",
            "street",
            "house_number",
            "postal_code",
            "city",
            "latitude",
            "longitude",
            "formattedAddress",
        ]

    def validate_latitude(self, value):
        if value < -90 or value > 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if value < -180 or value > 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

    def create(self, validated_data):
        business = self.context["business"]
        return Branch.objects.create(business=business, **validated_data)


class OfferBranchStatsSerializer(serializers.ModelSerializer):
    branch_id = serializers.IntegerField(source="branch.id", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = OfferBranchStats
        fields = ["branch_id", "branch_name", "scan_count", "avail_count"]


class BusinessOfferSerializer(serializers.ModelSerializer):
    discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    branch_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Branch.objects.none(),
        write_only=True,
        error_messages={
            "required": "At least one branch must be selected.",
            "empty": "At least one branch must be selected.",
        },
    )
    branches = BranchSerializer(many=True, read_only=True)
    branch_stats = OfferBranchStatsSerializer(many=True, read_only=True)
    qr_code = serializers.UUIDField(read_only=True)
    is_active = serializers.SerializerMethodField()
    category_id = serializers.IntegerField(
        source="business.category.id", read_only=True
    )
    category_name = serializers.CharField(
        source="business.category.name", read_only=True
    )
    category = CategorySerializer(source="business.category", read_only=True)

    class Meta:
        model = Offer
        fields = [
            "id",
            "offer_type",
            "title",
            "description",
            "discount_percent",
            "item_name",
            "original_price",
            "discounted_price",
            "usage_limit_type",
            "usage_limit_count",
            "branch_ids",
            "branches",
            "is_enabled",
            "is_time_limited",
            "starts_at",
            "ends_at",
            "qr_code",
            "is_active",
            "category_id",
            "category_name",
            "category",
            "branch_stats",
            "created_at",
        ]
        read_only_fields = ["id", "qr_code", "created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        business = self.context.get("business")
        if business is not None:
            queryset = business.branches.all()
            branch_field = self.fields["branch_ids"]
            branch_field.queryset = queryset
            branch_field.child_relation.queryset = queryset

    def get_is_active(self, obj: Offer) -> bool:
        return obj.is_active

    def _get_business(self):
        return self.context["business"]

    def _validate_branches_belong_to_business(self, branches):
        business = self._get_business()
        invalid = [branch.pk for branch in branches if branch.business_id != business.pk]
        if invalid:
            raise serializers.ValidationError(
                {"branch_ids": "One or more branches do not belong to your business."}
            )

    def _validate_offer_type_fields(self, attrs):
        offer_type = attrs.get(
            "offer_type", getattr(self.instance, "offer_type", None)
        )

        if offer_type == Offer.OfferType.PERCENTAGE_BILL:
            discount = attrs.get("discount_percent")
            if discount is None and self.instance:
                discount = self.instance.discount_percent
            if discount is None:
                raise serializers.ValidationError(
                    {"discount_percent": "Discount percentage is required."}
                )
            attrs["discount_percent"] = discount
            if discount <= 0 or discount > 100:
                raise serializers.ValidationError(
                    {"discount_percent": "Discount must be between 0.01 and 100."}
                )
            attrs["item_name"] = ""
            attrs["original_price"] = None
            attrs["discounted_price"] = None
        elif offer_type == Offer.OfferType.ITEM:
            item_name = attrs.get(
                "item_name", getattr(self.instance, "item_name", "")
            )
            original = attrs.get(
                "original_price", getattr(self.instance, "original_price", None)
            )
            discounted = attrs.get(
                "discounted_price", getattr(self.instance, "discounted_price", None)
            )
            if not item_name or not item_name.strip():
                raise serializers.ValidationError(
                    {"item_name": "Item or service name is required."}
                )
            if original is None:
                raise serializers.ValidationError(
                    {"original_price": "Original price is required."}
                )
            if discounted is None:
                raise serializers.ValidationError(
                    {"discounted_price": "Discounted price is required."}
                )
            if original <= 0:
                raise serializers.ValidationError(
                    {"original_price": "Original price must be greater than zero."}
                )
            if discounted < 0:
                raise serializers.ValidationError(
                    {"discounted_price": "Discounted price cannot be negative."}
                )
            if discounted >= original:
                raise serializers.ValidationError(
                    {"discounted_price": "Discounted price must be less than original price."}
                )
            attrs["discount_percent"] = Offer.compute_discount_percent(
                Decimal(str(original)), Decimal(str(discounted))
            )
            attrs["item_name"] = item_name.strip()

    def _validate_usage_limits(self, attrs):
        limit_type = attrs.get(
            "usage_limit_type",
            getattr(self.instance, "usage_limit_type", None),
        )
        count = attrs.get(
            "usage_limit_count",
            getattr(self.instance, "usage_limit_count", 1),
        )

        recurring_types = {
            Offer.UsageLimitType.N_TIMES_PER_WEEK,
            Offer.UsageLimitType.N_TIMES_PER_MONTH,
            Offer.UsageLimitType.N_TIMES_TOTAL,
        }
        if limit_type in recurring_types and count < 1:
            raise serializers.ValidationError(
                {"usage_limit_count": "Usage limit count must be at least 1."}
            )

        if limit_type in {
            Offer.UsageLimitType.ONE_TIME,
            Offer.UsageLimitType.ONCE_PER_WEEK,
            Offer.UsageLimitType.ONCE_PER_MONTH,
        }:
            attrs["usage_limit_count"] = 1

    def _validate_time_limits(self, attrs):
        is_time_limited = attrs.get(
            "is_time_limited",
            getattr(self.instance, "is_time_limited", False),
        )
        if not is_time_limited:
            attrs["starts_at"] = None
            attrs["ends_at"] = None
            return

        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if not starts_at and not ends_at:
            raise serializers.ValidationError(
                {
                    "starts_at": "Start or end time is required for time-limited offers.",
                    "ends_at": "Start or end time is required for time-limited offers.",
                }
            )
        if starts_at and ends_at and starts_at >= ends_at:
            raise serializers.ValidationError(
                {"ends_at": "End time must be after start time."}
            )

    def validate(self, attrs):
        branches = attrs.pop("branch_ids", None)
        if branches is not None:
            self._validate_branches_belong_to_business(branches)
            attrs["_branches"] = branches
        elif self.instance is None:
            raise serializers.ValidationError(
                {"branch_ids": "At least one branch must be selected."}
            )
        self._validate_offer_type_fields(attrs)
        self._validate_usage_limits(attrs)
        self._validate_time_limits(attrs)
        return attrs

    def create(self, validated_data):
        branches = validated_data.pop("_branches")
        business = self._get_business()
        offer = Offer.objects.create(business=business, **validated_data)
        offer.branches.set(branches)
        return offer

    def update(self, instance, validated_data):
        branches = validated_data.pop("_branches", None)
        offer = super().update(instance, validated_data)
        if branches is not None:
            offer.branches.set(branches)
        return offer


class OfferScanSerializer(serializers.Serializer):
    branch_id = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(),
        source="branch",
        error_messages={
            "required": "Branch is required.",
            "does_not_exist": "Branch not found.",
        },
    )
    qr_code = serializers.UUIDField(
        error_messages={
            "required": "QR code is required.",
            "invalid": "Enter a valid QR code.",
        }
    )

    def validate(self, attrs):
        offer = self.context["offer"]
        branch = attrs["branch"]
        qr_code = attrs["qr_code"]

        if offer.qr_code != qr_code:
            raise serializers.ValidationError({"qr_code": "Invalid QR code for this offer."})

        if not offer.is_active:
            raise serializers.ValidationError({"qr_code": "This offer is not currently active."})

        if not offer.branches.filter(pk=branch.pk).exists():
            raise serializers.ValidationError(
                {"branch_id": "This offer is not available at the selected branch."}
            )

        return attrs


class OfferRedeemSerializer(OfferScanSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        user = self.context["request"].user
        offer = self.context["offer"]
        branch = attrs["branch"]

        can_redeem, message = can_user_redeem_offer(user, offer, branch)
        if not can_redeem:
            raise serializers.ValidationError({"non_field_errors": [message]})
        return attrs
