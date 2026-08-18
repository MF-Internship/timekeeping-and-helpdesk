from django.conf import settings
from django.urls import URLPattern, URLResolver, include, path

from config.composition import (
    authorize_identity_logout,
    identity_container,
    identity_target_lookup,
    locations_container,
)
from identity.adapters.api.urls import identity_urlpatterns
from locations.adapters.api.urls import location_urlpatterns

urlpatterns: list[URLPattern | URLResolver] = [
    path(
        "api/v1/",
        include(
            identity_urlpatterns(
                identity_container,
                identity_target_lookup,
                authorize_identity_logout,
            )
            + location_urlpatterns(locations_container)
        ),
    ),
]

if settings.API_DOCS_ENABLED:
    from config.schema import MachineSchemaView

    urlpatterns.append(path("api/v1/schema/", MachineSchemaView.as_view(), name="api-schema"))
