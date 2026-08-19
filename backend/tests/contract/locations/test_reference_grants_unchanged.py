from __future__ import annotations

import pytest

from identity.domain.authorization import ROLE_PERMISSIONS, PermissionAction, Role
from tests.integration.api.identity.helpers import authenticated_client, create_user
from tests.integration.api.locations.helpers import create_config, create_location

#: The two reference contracts the on-device guidance preview reads through, and
#: the only ones it reads through. Guidance introduces no third.
REFERENCE_GRANTS = (PermissionAction.LOCATION_VIEW, PermissionAction.CONFIG_VIEW)

#: The canonical holder set for each of those grants, written out rather than
#: derived, so widening a grant fails here instead of silently agreeing with a
#: freshly computed expectation (FR-037).
CANONICAL_HOLDERS = frozenset({Role.LEADER, Role.MANAGER, Role.HELPDESK})

#: The path each grant admits the guidance reader to.
REFERENCE_PATHS = {
    PermissionAction.LOCATION_VIEW: "/api/v1/locations/",
    PermissionAction.CONFIG_VIEW: "/api/v1/config/",
}

#: Words a capability string invented for this feature would plausibly contain.
#: None may appear, because guidance is a reading through existing grants and
#: adds no capability of its own (FR-037, FR-037a).
FEATURE_VOCABULARY = ("guidance", "geofence", "preview", "diagram")


@pytest.mark.contract
def test_reference_grants_are_held_by_exactly_the_canonical_roles() -> None:
    """Guidance reads through `location.view` and `config.view`, exactly as they were.

    The grant is stated from both directions: every canonical role still holds
    both grants, and no role outside that set holds either. A grant added to a
    fourth role, or removed from one of the three, breaks one direction or the
    other (FR-037).
    """
    for grant in REFERENCE_GRANTS:
        holders = frozenset(role for role, granted in ROLE_PERMISSIONS.items() if grant in granted)
        assert holders == CANONICAL_HOLDERS, grant
        assert grant.is_mutation is False


@pytest.mark.contract
def test_no_capability_string_was_invented_for_guidance() -> None:
    """The permission vocabulary knows nothing of this feature, and must not.

    A preview that needed its own capability would be an action rather than a
    reading; the absence of one is what keeps it a reading (FR-037a).
    """
    named = sorted(
        action.value
        for action in PermissionAction
        for word in FEATURE_VOCABULARY
        if word in action.value
    )
    assert named == []


@pytest.mark.django_db(transaction=True)
@pytest.mark.contract
@pytest.mark.parametrize("role", sorted(CANONICAL_HOLDERS))
def test_every_canonical_role_still_reads_both_reference_contracts(role: str) -> None:
    """The grants are not merely declared — each role still gets an answer.

    A grant narrowed at the view rather than in the role model would leave
    `ROLE_PERMISSIONS` intact and still deny the read, so the wire is checked
    too (FR-037).
    """
    create_config()
    create_location()
    api = authenticated_client(create_user(f"reference-reader-{role.lower()}", role))

    for path in REFERENCE_PATHS.values():
        assert api.get(path).status_code == 200, path
