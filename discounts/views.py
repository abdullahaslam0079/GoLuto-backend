from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .address_utils import get_user_address, promote_next_default_address
from .models import Address, Branch, Category, Offer, OfferRedemption, UserPreferences
from .offer_utils import (
    active_offer_q,
    branch_highlight_queryset,
    build_user_redemption_map,
    filter_active_offers,
    get_user_offer_usage_status,
)
from .serializers import (
    AddressSerializer,
    CategorySerializer,
    MapBranchSerializer,
    OfferSerializer,
    OfferUsageSerializer,
    UserAvailedOfferSerializer,
    UserPreferencesSerializer,
)

User = get_user_model()


class UserOfferUsageContextMixin:
    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        if user.is_authenticated and user.account_type == User.AccountType.CONSUMER:
            queryset = self.filter_queryset(self.get_queryset())
            offer_ids = list(queryset.values_list("id", flat=True))
            context["user_offer_usage_by_id"] = build_user_redemption_map(
                user, offer_ids
            )
        return context


class CategoriesListAPIView(generics.ListAPIView):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class OffersListAPIView(UserOfferUsageContextMixin, generics.ListAPIView):
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
        queryset = branch_highlight_queryset(Branch.objects.all(), now)
        queryset = queryset.filter(highest_discount_percent__isnull=False)

        category_id = self.request.query_params.get("category_id")
        if category_id:
            queryset = queryset.filter(business__category_id=category_id)

        return queryset.order_by("-highest_discount_percent", "name")


class MapBusinessesAPIView(MapBranchesAPIView):
    """Backward-compatible alias: map pins are branch locations."""

    pass


class BusinessOffersAPIView(UserOfferUsageContextMixin, generics.ListAPIView):
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


class BranchOffersAPIView(UserOfferUsageContextMixin, generics.ListAPIView):
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


class UserAvailedOffersAPIView(generics.ListAPIView):
    serializer_class = UserAvailedOfferSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.account_type != User.AccountType.CONSUMER:
            return OfferRedemption.objects.none()

        return (
            OfferRedemption.objects.filter(user=self.request.user)
            .select_related(
                "offer",
                "offer__business",
                "offer__business__category",
                "branch",
                "branch__business",
            )
            .order_by("-redeemed_at", "-id")
        )

    def list(self, request, *args, **kwargs):
        if request.user.account_type != User.AccountType.CONSUMER:
            return Response(
                {
                    "message": "Consumer account required.",
                    "errors": {"detail": ["Consumer account required."]},
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "message": "Availed offers retrieved successfully.",
                "errors": {},
                "results": serializer.data,
            }
        )


class OfferUsageAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, offer_id):
        if request.user.account_type != User.AccountType.CONSUMER:
            return Response(
                {
                    "message": "Consumer account required.",
                    "errors": {"detail": ["Consumer account required."]},
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        offer = Offer.objects.filter(pk=offer_id).first()
        if offer is None:
            return Response(
                {
                    "message": "Offer not found.",
                    "errors": {"detail": ["Offer not found."]},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        usage = get_user_offer_usage_status(request.user, offer)
        serializer = OfferUsageSerializer.from_usage(offer.id, usage)
        return Response(
            {
                "message": "Offer usage retrieved successfully.",
                "errors": {},
                **serializer.data,
            }
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
