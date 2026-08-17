from django.conf import settings
from django.urls import URLPattern, URLResolver, path

urlpatterns: list[URLPattern | URLResolver] = []

if settings.API_DOCS_ENABLED:
    from config.schema import MachineSchemaView

    urlpatterns.append(path("api/v1/schema/", MachineSchemaView.as_view(), name="api-schema"))
