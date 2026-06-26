from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Address, Business, Category, Offer, UserPreferences

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True, max_length=301, trim_whitespace=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = ("name", "email", "password", "password_confirm")

    def validate_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Full name is required.")
        return value.strip()

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        validate_password(attrs["password"])
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
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = [
            "id",
            "business_id",
            "business_name",
            "category_id",
            "category_name",
            "title",
            "description",
            "discount_percent",
            "is_enabled",
            "is_time_limited",
            "starts_at",
            "ends_at",
            "is_active",
        ]

    def get_is_active(self, obj: Offer) -> bool:
        return obj.is_active


class MapBusinessSerializer(serializers.ModelSerializer):
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
            "latitude",
            "longitude",
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
    houseNumber = serializers.CharField(source="house_number")
    postalCode = serializers.CharField(source="postal_code")
    isDefault = serializers.BooleanField(
        source="is_default", required=False, default=False
    )
    formattedAddress = serializers.CharField(source="formatted_address", read_only=True)
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()

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

    def get_id(self, obj: Address) -> str:
        return f"addr_{obj.pk}"

    def create(self, validated_data):
        user = self.context["request"].user
        is_default = validated_data.get("is_default", False)
        if is_default:
            user.addresses.filter(is_default=True).update(is_default=False)
        elif not user.addresses.exists():
            validated_data["is_default"] = True
        return Address.objects.create(user=user, **validated_data)


class LoginTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data.pop("refresh", None)
        data["user"] = LoginUserSerializer(user).data
        data["addresses"] = AddressSerializer(
            user.addresses.order_by("-is_default", "id"), many=True
        ).data
        return data


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
