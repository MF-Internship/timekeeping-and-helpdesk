from collections.abc import Callable

from django.urls import URLPattern, path

from operations.adapters.api.views import JobHealthView
from operations.application.container import OperationsContainer


def operations_urlpatterns(
    container_provider: Callable[[], OperationsContainer],
) -> list[URLPattern]:
    JobHealthView.container_provider = staticmethod(container_provider)
    return [path("operations/job-health", JobHealthView.as_view(), name="operations-job-health")]
