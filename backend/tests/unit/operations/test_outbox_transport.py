from __future__ import annotations

import pytest

from operations.adapters.outbox import (
    DisabledOutboxTransport,
    LoggingOutboxTransport,
    transport_from_name,
)


def test_outbox_transport_registry_is_closed() -> None:
    assert isinstance(transport_from_name("disabled"), DisabledOutboxTransport)
    assert isinstance(transport_from_name("logging"), LoggingOutboxTransport)
    with pytest.raises(ValueError, match="OUTBOX_RELAY_TRANSPORT"):
        transport_from_name("smtp")
