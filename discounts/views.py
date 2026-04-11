from django.db.models import Max, Q
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Business, Category, Offer, UserPreferences
from .serializers import (
    CategorySerializer,
    MapBusinessSerializer,
    OfferSerializer,
    UserPreferencesSerializer,
)


def active_offer_q(now):
    return Q(
        offers__is_enabled=True,
    ) & (
        Q(offers__is_time_limited=False)
        | (
            Q(offers__is_time_limited=True)
            & (Q(offers__starts_at__isnull=True) | Q(offers__starts_at__lte=now))
            & (Q(offers__ends_at__isnull=True) | Q(offers__ends_at__gte=now))
        )
    )


class CategoriesListAPIView(generics.ListAPIView):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class OffersListAPIView(generics.ListAPIView):
    serializer_class = OfferSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        now = timezone.now()
        queryset = Offer.objects.select_related(
            "business", "business__category"
        ).filter(is_enabled=True)
        queryset = queryset.filter(
            Q(is_time_limited=False)
            | (
                Q(is_time_limited=True)
                & (Q(starts_at__isnull=True) | Q(starts_at__lte=now))
                & (Q(ends_at__isnull=True) | Q(ends_at__gte=now))
            )
        )

        category_id = self.request.query_params.get("category_id")
        if category_id:
            queryset = queryset.filter(business__category_id=category_id)

        return queryset.order_by("-discount_percent", "-id")


class MapBusinessesAPIView(generics.ListAPIView):
    serializer_class = MapBusinessSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        now = timezone.now()
        return (
            Business.objects.select_related("category")
            .annotate(
                highest_discount_percent=Max(
                    "offers__discount_percent",
                    filter=active_offer_q(now),
                )
            )
            .exclude(highest_discount_percent__isnull=True)
            .order_by("-highest_discount_percent", "name")
        )


class BusinessOffersAPIView(generics.ListAPIView):
    serializer_class = OfferSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        now = timezone.now()
        business_id = self.kwargs["business_id"]
        return (
            Offer.objects.select_related("business", "business__category")
            .filter(
                business_id=business_id,
                is_enabled=True,
            )
            .filter(
                Q(is_time_limited=False)
                | (
                    Q(is_time_limited=True)
                    & (Q(starts_at__isnull=True) | Q(starts_at__lte=now))
                    & (Q(ends_at__isnull=True) | Q(ends_at__gte=now))
                )
            )
            .order_by("-discount_percent", "-id")
        )


class UserPreferencesAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
        serializer = UserPreferencesSerializer(preferences)
        return Response(serializer.data)

    def put(self, request):
        preferences, _ = UserPreferences.objects.get_or_create(user=request.user)
        serializer = UserPreferencesSerializer(preferences, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
