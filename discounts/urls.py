from django.urls import path

from .views import (
    BusinessOffersAPIView,
    CategoriesListAPIView,
    MapBusinessesAPIView,
    OffersListAPIView,
    UserAddressDetailAPIView,
    UserAddressesAPIView,
    UserPreferencesAPIView,
)

urlpatterns = [
    path("categories", CategoriesListAPIView.as_view(), name="categories"),
    path("offers", OffersListAPIView.as_view(), name="offers"),
    path("map/businesses", MapBusinessesAPIView.as_view(), name="map-businesses"),
    path(
        "business/<int:business_id>/offers",
        BusinessOffersAPIView.as_view(),
        name="business-offers",
    ),
    path("user/preferences", UserPreferencesAPIView.as_view(), name="user-preferences"),
    path("user/addresses", UserAddressesAPIView.as_view(), name="user-addresses"),
    path(
        "user/addresses/<str:address_id>",
        UserAddressDetailAPIView.as_view(),
        name="user-address-detail",
    ),
]
