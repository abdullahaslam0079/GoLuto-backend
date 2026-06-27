from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from django.utils import timezone

from .models import Branch, Offer, OfferRedemption, OfferScan
from .offer_utils import (
    branch_highlight_queryset,
    can_user_redeem_offer,
    get_user_offer_usage_status,
    increment_branch_stat,
)
from .permissions import IsBusinessAccount, IsConsumerAccount
from .serializers import OfferUsageSerializer
from .serializers_business import (
    BranchSerializer,
    BusinessLoginTokenObtainPairSerializer,
    BusinessOfferSerializer,
    BusinessProfileSerializer,
    BusinessRegisterSerializer,
    OfferRedeemSerializer,
    OfferScanSerializer,
)


class BusinessRegisterAPIView(generics.CreateAPIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = BusinessRegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        business = serializer.save()
        return Response(
            {
                "message": "Business account created successfully.",
                "errors": {},
                "business": BusinessProfileSerializer(
                    business, context={"request": request}
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class BusinessLoginAPIView(TokenObtainPairView):
    authentication_classes = []
    serializer_class = BusinessLoginTokenObtainPairSerializer


class BusinessProfileAPIView(APIView):
    permission_classes = [IsBusinessAccount]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        business = request.user.business_profile
        serializer = BusinessProfileSerializer(
            business, context={"request": request}
        )
        return Response(serializer.data)

    def put(self, request):
        business = request.user.business_profile
        serializer = BusinessProfileSerializer(
            business,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class BusinessBranchListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = BranchSerializer
    permission_classes = [IsBusinessAccount]

    def get_queryset(self):
        return branch_highlight_queryset(
            self.request.user.business_profile.branches.all(),
            timezone.now(),
        ).order_by("name", "id")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["business"] = self.request.user.business_profile
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        branch = serializer.save()
        output = BranchSerializer(branch, context=self.get_serializer_context()).data
        return Response(
            {
                "message": "Branch created successfully.",
                "errors": {},
                **output,
            },
            status=status.HTTP_201_CREATED,
        )


class BusinessBranchDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BranchSerializer
    permission_classes = [IsBusinessAccount]
    lookup_url_kwarg = "branch_id"

    def get_queryset(self):
        return branch_highlight_queryset(
            self.request.user.business_profile.branches.all(),
            timezone.now(),
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["business"] = self.request.user.business_profile
        return context

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        response.data = {
            "message": "Branch updated successfully.",
            "errors": {},
            **response.data,
        }
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.offers.exists():
            return Response(
                {
                    "message": "Cannot delete a branch that has offers assigned to it.",
                    "errors": {"branch_id": ["Remove offers from this branch first."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.delete()
        return Response(
            {"message": "Branch deleted successfully.", "errors": {}},
            status=status.HTTP_200_OK,
        )


class BusinessOfferListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = BusinessOfferSerializer
    permission_classes = [IsBusinessAccount]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return (
            self.request.user.business_profile.offers.prefetch_related(
                "branches", "branch_stats__branch"
            )
            .order_by("-created_at", "-id")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["business"] = self.request.user.business_profile
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offer = serializer.save()
        output = BusinessOfferSerializer(
            offer, context=self.get_serializer_context()
        ).data
        return Response(
            {
                "message": "Offer created successfully.",
                "errors": {},
                **output,
            },
            status=status.HTTP_201_CREATED,
        )


class BusinessOfferDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BusinessOfferSerializer
    permission_classes = [IsBusinessAccount]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_url_kwarg = "offer_id"

    def get_queryset(self):
        return self.request.user.business_profile.offers.prefetch_related(
            "branches", "branch_stats__branch"
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["business"] = self.request.user.business_profile
        return context

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        response.data = {
            "message": "Offer updated successfully.",
            "errors": {},
            **response.data,
        }
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Offer deleted successfully.", "errors": {}},
            status=status.HTTP_200_OK,
        )


class OfferScanAPIView(APIView):
    permission_classes = [IsConsumerAccount]

    def post(self, request, offer_id):
        offer = get_object_or_404(Offer, pk=offer_id)
        serializer = OfferScanSerializer(
            data=request.data,
            context={"offer": offer, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        branch = serializer.validated_data["branch"]

        with transaction.atomic():
            OfferScan.objects.create(offer=offer, branch=branch, user=request.user)
            increment_branch_stat(offer, branch, scan=True)

        return Response(
            {
                "message": "Offer scanned successfully.",
                "errors": {},
                "offer_id": offer.id,
                "branch_id": branch.id,
            },
            status=status.HTTP_200_OK,
        )


class OfferRedeemAPIView(APIView):
    permission_classes = [IsConsumerAccount]

    def post(self, request, offer_id):
        offer = get_object_or_404(Offer, pk=offer_id)
        serializer = OfferRedeemSerializer(
            data=request.data,
            context={"offer": offer, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        branch = serializer.validated_data["branch"]

        with transaction.atomic():
            locked_offer = Offer.objects.select_for_update().get(pk=offer.pk)
            can_redeem, message = can_user_redeem_offer(
                request.user, locked_offer, branch
            )
            if not can_redeem:
                return Response(
                    {
                        "message": message,
                        "errors": {"non_field_errors": [message]},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            OfferRedemption.objects.create(
                offer=locked_offer, branch=branch, user=request.user
            )
            increment_branch_stat(locked_offer, branch, avail=True)
            usage = get_user_offer_usage_status(request.user, locked_offer)
            usage_data = OfferUsageSerializer.from_usage(locked_offer.id, usage).data

        return Response(
            {
                "message": "Offer redeemed successfully.",
                "errors": {},
                "offer_id": offer.id,
                "branch_id": branch.id,
                **usage_data,
            },
            status=status.HTTP_200_OK,
        )
