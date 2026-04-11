from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Business, Category, Offer, UserPreferences

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = ("email", "password", "password_confirm")

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
        return User.objects.create_user(email=email, password=password, **validated_data)


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
