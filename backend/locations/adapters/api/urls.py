from collections.abc import Callable

from django.urls import URLPattern, path

from locations.adapters.api.views import (
    ConfigView,
    HolidayDetailView,
    HolidayListCreateView,
    LocationDetailView,
    LocationListView,
)
from locations.application.container import LocationsContainer


def location_urlpatterns(
    container_provider: Callable[[], LocationsContainer],
) -> list[URLPattern]:
    injected = {"container_provider": container_provider}
    return [
        path("locations/", LocationListView.as_view(**injected), name="locations-list"),
        path(
            "locations/<str:location_id>/",
            LocationDetailView.as_view(**injected),
            name="locations-detail",
        ),
        path("config/", ConfigView.as_view(**injected), name="locations-config"),
        path("holidays/", HolidayListCreateView.as_view(**injected), name="holidays-list"),
        path(
            "holidays/<str:holiday_id>/",
            HolidayDetailView.as_view(**injected),
            name="holidays-detail",
        ),
    ]
