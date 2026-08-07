from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .address_utils import get_user_address, promote_next_default_address
from .location_utils import (
    filter_branches_for_location,
    filter_offers_for_location,
    resolve_user_location,
    sort_offers_by_nearest_distance,
)
from .engagement_utils import (
    pick_featured_offers_one_per_business,
    record_business_view,
    record_offer_view,
    toggle_business_like,
    toggle_offer_like,
)
from .models import Address, Branch, Business, Category, Offer, OfferRedemption, UserPreferences
from .offer_pricing import compute_offer_payment
from .offer_utils import (
    active_offer_q,
    branch_highlight_queryset,
    build_user_redemption_map,
    filter_active_offers,
    get_user_offer_usage_status,
)
from .permissions import IsConsumerAccount
from .serializers import (
    AddressSerializer,
    CategorySerializer,
    DiscountOfferSerializer,
    MapBranchSerializer,
    OfferPaymentPreviewRequestSerializer,
    OfferPaymentPreviewSerializer,
    OfferQRBranchSerializer,
    OfferQRSummarySerializer,
    OfferSerializer,
    OfferUsageSerializer,
    UserAvailedOfferSerializer,
    UserPreferencesSerializer,
)

User = get_user_model()


class UserLocationContextMixin:
    def get_user_location(self):
        if not hasattr(self, "_user_location"):
            self._user_location = resolve_user_location(self.request)
        return self._user_location

    def get_serializer_context(self):
        context = super().get_serializer_context()
        location = self.get_user_location()
        if location is not None:
            context["user_location"] = location
        return context


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


class OffersListAPIView(
    UserLocationContextMixin, UserOfferUsageContextMixin, generics.ListAPIView
):
    serializer_class = OfferSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Offer.objects.select_related(
            "business", "business__category"
        ).prefetch_related("branches", "gallery_images")
        queryset = filter_active_offers(queryset)

        category_id = self.request.query_params.get("category_id")
        if category_id:
            queryset = queryset.filter(business__category_id=category_id)

        branch_id = self.request.query_params.get("branch_id")
        if branch_id:
            queryset = queryset.filter(branches__id=branch_id)

        location = self.get_user_location()
        if location is not None:
            queryset, _ = filter_offers_for_location(queryset, location)
            return queryset

        return queryset.order_by("-discount_percent", "-id").distinct()


class OfferSearchAPIView(UserLocationContextMixin, APIView):
    """
    Full-text-ish offer search (icontains) across product fields and brand name.
    Results are paginated and ranked nearest-first when a user location is present.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        q = (request.query_params.get("q") or "").strip()

        try:
            page = max(int(request.query_params.get("page", 1)), 1)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(max(int(request.query_params.get("page_size", 20)), 1), 100)
        except (TypeError, ValueError):
            page_size = 20

        empty = {
            "count": 0,
            "page": page,
            "page_size": page_size,
            "results": [],
        }
        if not q:
            return Response(empty)

        queryset = (
            Offer.objects.select_related("business", "business__category")
            .prefetch_related("branches", "gallery_images")
        )
        queryset = filter_active_offers(queryset)
        queryset = queryset.filter(
            Q(title__icontains=q)
            | Q(item_name__icontains=q)
            | Q(description__icontains=q)
            | Q(detailed_description__icontains=q)
            | Q(business__name__icontains=q)
        ).distinct()

        location = self.get_user_location()
        if location is not None:
            queryset = sort_offers_by_nearest_distance(queryset, location)
        else:
            queryset = queryset.order_by("-discount_percent", "-id")

        total = queryset.count()
        start = (page - 1) * page_size
        items = list(queryset[start : start + page_size])

        usage_map = {}
        user = request.user
        if user.is_authenticated and user.account_type == User.AccountType.CONSUMER:
            usage_map = build_user_redemption_map(user, [offer.id for offer in items])

        context = {
            "request": request,
            "user_location": location,
            "user_offer_usage_by_id": usage_map,
        }
        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "results": OfferSerializer(items, many=True, context=context).data,
            }
        )


class MapBranchesAPIView(UserLocationContextMixin, generics.ListAPIView):
    serializer_class = MapBranchSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        now = timezone.now()
        queryset = branch_highlight_queryset(Branch.objects.all(), now)
        queryset = queryset.filter(highest_discount_percent__isnull=False)

        category_id = self.request.query_params.get("category_id")
        if category_id:
            queryset = queryset.filter(business__category_id=category_id)

        location = self.get_user_location()
        if location is not None:
            queryset, _ = filter_branches_for_location(queryset, location)
            return queryset

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
            .prefetch_related("branches", "gallery_images")
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
            .prefetch_related("branches", "gallery_images")
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
            .prefetch_related("offer__gallery_images")
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


class OfferPaymentPreviewAPIView(APIView):
    permission_classes = [IsConsumerAccount]

    def post(self, request, offer_id):
        offer = get_object_or_404(Offer, pk=offer_id)
        serializer = OfferPaymentPreviewRequestSerializer(
            data=request.data,
            context={"offer": offer},
        )
        serializer.is_valid(raise_exception=True)
        payment = serializer.validated_data["payment"]
        payment_data = OfferPaymentPreviewSerializer.from_preview(payment).data
        return Response(
            {
                "message": "Payment preview calculated successfully.",
                "errors": {},
                "offer_id": offer.id,
                "payment": payment_data,
            }
        )


class OfferByQRAPIView(APIView):
    """Resolve a poster QR code to offer + branch context and payment preview."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, qr_code):
        offer = (
            Offer.objects.select_related("business", "business__category")
            .prefetch_related("gallery_images")
            .filter(qr_code=qr_code)
            .first()
        )
        if offer is None:
            return Response(
                {
                    "message": "Offer not found.",
                    "errors": {"qr_code": ["Invalid or unknown QR code."]},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if offer.redemption_mode == Offer.RedemptionMode.VIEW_ONLY:
            return Response(
                {
                    "message": "This offer is view-only and cannot be redeemed.",
                    "errors": {"qr_code": ["This offer is view-only."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        branch_id = request.query_params.get("branch_id")
        if not branch_id:
            return Response(
                {
                    "message": "Branch is required.",
                    "errors": {"branch_id": ["branch_id query parameter is required."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        branch = Branch.objects.select_related("business").filter(pk=branch_id).first()
        if branch is None:
            return Response(
                {
                    "message": "Branch not found.",
                    "errors": {"branch_id": ["Branch not found."]},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if not offer.branches.filter(pk=branch.pk).exists():
            return Response(
                {
                    "message": "This offer is not available at this branch.",
                    "errors": {"branch_id": ["This offer is not available at this branch."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not offer.is_active:
            return Response(
                {
                    "message": "This offer is not currently active.",
                    "errors": {"detail": ["This offer is not currently active."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        bill_amount = request.query_params.get("bill_amount")
        if bill_amount is not None:
            preview_serializer = OfferPaymentPreviewRequestSerializer(
                data={"bill_amount": bill_amount},
                context={"offer": offer},
            )
            if not preview_serializer.is_valid():
                return Response(
                    {
                        "message": "Unable to calculate payment.",
                        "errors": preview_serializer.errors,
                        "offer": OfferQRSummarySerializer(
                            offer, context={"request": request}
                        ).data,
                        "branch": OfferQRBranchSerializer(branch).data,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            payment = preview_serializer.validated_data["payment"]
        else:
            payment = compute_offer_payment(offer)

        payment_data = OfferPaymentPreviewSerializer.from_preview(payment).data
        offer_data = OfferQRSummarySerializer(offer, context={"request": request}).data
        branch_data = OfferQRBranchSerializer(branch).data

        response_payload = {
            "message": "Offer retrieved successfully.",
            "errors": {},
            "offer": offer_data,
            "branch": branch_data,
            "payment": payment_data,
            "can_avail": False,
        }

        user = request.user
        if (
            user.is_authenticated
            and user.account_type == User.AccountType.CONSUMER
        ):
            usage = get_user_offer_usage_status(user, offer)
            response_payload["can_avail"] = usage.is_available_for_user
            response_payload.update(
                OfferUsageSerializer.from_usage(offer.id, usage).data
            )

        return Response(response_payload)


class DiscountsFeedAPIView(UserLocationContextMixin, UserOfferUsageContextMixin, APIView):
    """One spotlight offer per business, ranked by engagement then discount."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        queryset = (
            Offer.objects.select_related(
                "business",
                "business__category",
                "engagement_stats",
                "business__engagement_stats",
            )
            .prefetch_related("branches", "gallery_images")
        )
        queryset = filter_active_offers(queryset)

        category_id = request.query_params.get("category_id")
        if category_id:
            queryset = queryset.filter(business__category_id=category_id)

        location = resolve_user_location(request)
        if location is not None:
            queryset, _ = filter_offers_for_location(queryset, location)

        offers = list(queryset.distinct())
        featured = pick_featured_offers_one_per_business(offers)

        offer_ids = [offer.id for offer in featured]
        usage_map = {}
        user = request.user
        if user.is_authenticated and user.account_type == User.AccountType.CONSUMER:
            usage_map = build_user_redemption_map(user, offer_ids)

        context = {
            "request": request,
            "user_location": location,
            "user_offer_usage_by_id": usage_map,
        }
        data = DiscountOfferSerializer(featured, many=True, context=context).data
        return Response(data)


class OfferViewAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, offer_id):
        offer = get_object_or_404(
            Offer.objects.select_related("business"),
            pk=offer_id,
        )
        user = request.user if request.user.is_authenticated else None
        stats = record_offer_view(offer, user=user)
        return Response(
            {
                "message": "Offer view recorded.",
                "view_count": stats.view_count,
            }
        )


class OfferLikeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsConsumerAccount]

    def post(self, request, offer_id):
        offer = get_object_or_404(Offer, pk=offer_id)
        is_liked, stats = toggle_offer_like(request.user, offer)
        return Response(
            {
                "message": "Offer like updated.",
                "is_liked": is_liked,
                "like_count": stats.like_count,
            }
        )


class BusinessViewAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, business_id):
        business = get_object_or_404(Business, pk=business_id)
        user = request.user if request.user.is_authenticated else None
        stats = record_business_view(business, user=user)
        return Response(
            {
                "message": "Business view recorded.",
                "view_count": stats.view_count,
            }
        )


class BusinessLikeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsConsumerAccount]

    def post(self, request, business_id):
        business = get_object_or_404(Business, pk=business_id)
        is_liked, stats = toggle_business_like(request.user, business)
        return Response(
            {
                "message": "Business like updated.",
                "is_liked": is_liked,
                "like_count": stats.like_count,
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
