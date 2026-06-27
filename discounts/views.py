from django.db.models import Max
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .address_utils import get_user_address, promote_next_default_address
from .models import Address, Branch, Category, Offer, UserPreferences
from .offer_utils import active_offer_q, filter_active_offers
from .serializers import (
    AddressSerializer,
    CategorySerializer,
    MapBranchSerializer,
    OfferSerializer,
    UserPreferencesSerializer,
)


class CategoriesListAPIView(generics.ListAPIView):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class OffersListAPIView(generics.ListAPIView):
    serializer_class = OfferSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Offer.objects.select_related(
            "business", "business__category"
        ).prefetch_related("branches")
        queryset = filter_active_offers(queryset)

        category_id = self.request.query_params.get("category_id")
        if category_id:
            queryset = queryset.filter(business__category_id=category_id)

        branch_id = self.request.query_params.get("branch_id")
        if branch_id:
            queryset = queryset.filter(branches__id=branch_id)

        return queryset.order_by("-discount_percent", "-id").distinct()


class MapBranchesAPIView(generics.ListAPIView):
    serializer_class = MapBranchSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        now = timezone.now()
        queryset = (
            Branch.objects.select_related("business", "business__category")
            .annotate(
                highest_discount_percent=Max(
                    "offers__discount_percent",
                    filter=active_offer_q(now, prefix="offers"),
                )
            )
            .filter(highest_discount_percent__isnull=False)
        )

        category_id = self.request.query_params.get("category_id")
        if category_id:
            queryset = queryset.filter(business__category_id=category_id)

        return queryset.order_by("-highest_discount_percent", "name")


class MapBusinessesAPIView(MapBranchesAPIView):
    """Backward-compatible alias: map pins are branch locations."""

    pass


class BusinessOffersAPIView(generics.ListAPIView):
    serializer_class = OfferSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        business_id = self.kwargs["business_id"]
        queryset = (
            Offer.objects.select_related("business", "business__category")
            .prefetch_related("branches")
            .filter(business_id=business_id)
        )
        return filter_active_offers(queryset).order_by("-discount_percent", "-id")


class BranchOffersAPIView(generics.ListAPIView):
    serializer_class = OfferSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        branch_id = self.kwargs["branch_id"]
        queryset = (
            Offer.objects.select_related("business", "business__category")
            .prefetch_related("branches")
            .filter(branches__id=branch_id)
        )
        return filter_active_offers(queryset).order_by("-discount_percent", "-id").distinct()


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


class UserAddressesAPIView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.addresses.order_by("-is_default", "id")


class UserAddressDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "address_id"

    def get_object(self):
        return get_user_address(self.request.user, self.kwargs["address_id"])

    def perform_destroy(self, instance):
        user = self.request.user
        was_default = instance.is_default
        instance.delete()
        if was_default:
            promote_next_default_address(user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "Address deleted successfully.", "errors": {}},
            status=status.HTTP_200_OK,
        )
