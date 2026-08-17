from drf_spectacular.utils import extend_schema, extend_schema_view
from drf_spectacular.views import SpectacularAPIView


@extend_schema_view(get=extend_schema(operation_id="api_schema_retrieve"))
class MachineSchemaView(SpectacularAPIView):
    """Machine-readable schema endpoint; no interactive UI is registered."""

    pass
