from django.urls import path

from .views import (
    BranchOffersAPIView,
    BusinessOffersAPIView,
    CategoriesListAPIView,
    MapBranchesAPIView,
    MapBusinessesAPIView,
    OfferByQRAPIView,
    OfferPaymentPreviewAPIView,
    OfferUsageAPIView,
    OffersListAPIView,
    UserAddressDetailAPIView,
    UserAddressesAPIView,
    UserAvailedOffersAPIView,
    UserPreferencesAPIView,
)
from .views_business import (
    BusinessBranchDetailAPIView,
    BusinessBranchListCreateAPIView,
    BusinessLoginAPIView,
    BusinessLogoutAPIView,
    BusinessOfferDetailAPIView,
    BusinessOfferListCreateAPIView,
    BusinessProfileAPIView,
    BusinessRegisterAPIView,
    OfferAvailAPIView,
    OfferRedeemAPIView,
    OfferScanAPIView,
)

urlpatterns = [
    path("categories", CategoriesListAPIView.as_view(), name="categories"),
    path("offers", OffersListAPIView.as_view(), name="offers"),
    path("map/branches", MapBranchesAPIView.as_view(), name="map-branches"),
    path("map/businesses", MapBusinessesAPIView.as_view(), name="map-businesses"),
    path(
        "business/<int:business_id>/offers",
        BusinessOffersAPIView.as_view(),
        name="business-offers",
    ),
    path(
        "branch/<int:branch_id>/offers",
        BranchOffersAPIView.as_view(),
        name="branch-offers",
    ),
    path(
        "offers/by-qr/<uuid:qr_code>",
        OfferByQRAPIView.as_view(),
        name="offer-by-qr",
    ),
    path(
        "offers/<int:offer_id>/payment-preview",
        OfferPaymentPreviewAPIView.as_view(),
        name="offer-payment-preview",
    ),
    path(
        "offers/<int:offer_id>/scan",
        OfferScanAPIView.as_view(),
        name="offer-scan",
    ),
    path(
        "offers/<int:offer_id>/redeem",
        OfferRedeemAPIView.as_view(),
        name="offer-redeem",
    ),
    path(
        "offers/<int:offer_id>/avail",
        OfferAvailAPIView.as_view(),
        name="offer-avail",
    ),
    path(
        "offers/<int:offer_id>/usage",
        OfferUsageAPIView.as_view(),
        name="offer-usage",
    ),
    path(
        "user/offers/availed",
        UserAvailedOffersAPIView.as_view(),
        name="user-availed-offers",
    ),
    path("user/preferences", UserPreferencesAPIView.as_view(), name="user-preferences"),
    path("user/addresses", UserAddressesAPIView.as_view(), name="user-addresses"),
    path(
        "user/addresses/<str:address_id>",
        UserAddressDetailAPIView.as_view(),
        name="user-address-detail",
    ),
    path(
        "business/auth/register",
        BusinessRegisterAPIView.as_view(),
        name="business-auth-register",
    ),
    path(
        "business/auth/token",
        BusinessLoginAPIView.as_view(),
        name="business-auth-token",
    ),
    path(
        "business/auth/logout",
        BusinessLogoutAPIView.as_view(),
        name="business-auth-logout",
    ),
    path("business/profile", BusinessProfileAPIView.as_view(), name="business-profile"),
    path(
        "business/branches",
        BusinessBranchListCreateAPIView.as_view(),
        name="business-branches",
    ),
    path(
        "business/branches/<int:branch_id>",
        BusinessBranchDetailAPIView.as_view(),
        name="business-branch-detail",
    ),
    path(
        "business/offers",
        BusinessOfferListCreateAPIView.as_view(),
        name="business-offers-manage",
    ),
    path(
        "business/offers/<int:offer_id>",
        BusinessOfferDetailAPIView.as_view(),
        name="business-offer-detail",
    ),
]
