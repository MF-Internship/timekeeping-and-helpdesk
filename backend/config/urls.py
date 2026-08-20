from django.conf import settings
from django.urls import URLPattern, URLResolver, include, path

from attendance.adapters.api.urls import attendance_urlpatterns
from config.composition import (
    attendance_container,
    identity_container,
    identity_target_lookup,
    locations_container,
    operations_container,
    reporting_container,
    task_container,
)
from identity.adapters.api.urls import identity_urlpatterns
from locations.adapters.api.urls import location_urlpatterns
from notifications.adapters.api.urls import urlpatterns as notification_urlpatterns
from operations.adapters.api.urls import operations_urlpatterns
from reporting.adapters.api.urls import reporting_urlpatterns
from tasks.adapters.api.urls import task_urlpatterns

urlpatterns: list[URLPattern | URLResolver] = [
    path(
        "api/v1/",
        include(
            identity_urlpatterns(
                identity_container,
                identity_target_lookup,
            )
            + location_urlpatterns(locations_container)
            + attendance_urlpatterns(attendance_container)
            + operations_urlpatterns(operations_container)
            + reporting_urlpatterns(reporting_container)
            + task_urlpatterns(task_container)
            + notification_urlpatterns
        ),
    ),
]

if settings.API_DOCS_ENABLED:
    from config.schema import MachineSchemaView

    urlpatterns.append(path("api/v1/schema/", MachineSchemaView.as_view(), name="api-schema"))
