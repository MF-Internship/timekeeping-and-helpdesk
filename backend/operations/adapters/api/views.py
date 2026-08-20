from collections.abc import Callable
from typing import cast

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.error_codes import VALIDATION_FAILED
from core.errors import IdentityAPIError
from operations.adapters.api.permissions import CanonicalOperationsPermission
from operations.adapters.api.serializers import JobHealthSerializer, job_health_payload
from operations.application.container import OperationsContainer


class JobHealthView(APIView):
    permission_classes = (CanonicalOperationsPermission,)
    container_provider: Callable[[], OperationsContainer] | None = None

    @extend_schema(operation_id="operations_job_health_retrieve", responses=JobHealthSerializer)
    def get(self, request: Request) -> Response:
        if self.container_provider is None:
            raise RuntimeError("operations container is not configured")
        actor_id = cast(int, request.user.pk)
        result = self.container_provider().job_health.read(actor_id)
        if request.query_params or request.data:
            raise IdentityAPIError(VALIDATION_FAILED, status_code=400)
        response = Response(job_health_payload(result))
        response["Cache-Control"] = "private, no-store"
        return response
