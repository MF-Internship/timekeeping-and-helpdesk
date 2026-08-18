from functools import lru_cache
from pathlib import Path

from django.conf import settings

from audit.adapters.persistence.recording import DjangoAuditRecorder
from identity.adapters.persistence.unit_of_work import DjangoUnitOfWork
from identity.adapters.persistence.users import DjangoUserRepository
from identity.adapters.security.passwords import DjangoPasswordService
from identity.adapters.security.sessions import SimpleJWTSessionRepository
from identity.application.authentication import AuthenticationService
from identity.application.authorization import DjangoAuthorizationGateway
from identity.application.container import IdentityContainer
from identity.application.dependencies import IdentityDependencies
from identity.application.queries import UserQueryService
from identity.application.self_service import SelfService
from identity.application.user_admin import UserAdminService
from identity.domain.accounts import AccountSnapshot
from locations.adapters.persistence.repositories import (
    DjangoConfigRepository,
    DjangoHolidayRepository,
    DjangoLocationRepository,
)
from locations.adapters.persistence.unit_of_work import (
    DjangoUnitOfWork as LocationsDjangoUnitOfWork,
)
from locations.adapters.source_data.csv_source import CsvLocationSource
from locations.application.config_admin import ConfigAdminService
from locations.application.container import LocationsContainer
from locations.application.dependencies import LocationDependencies
from locations.application.holidays import HolidayService
from locations.application.location_admin import LocationAdminService
from locations.application.queries import ConfigQueryService, LocationQueryService
from locations.application.readiness import ReadinessDependencies, ReferenceDataReadinessService
from locations.application.seed import LocationSeedService


@lru_cache(maxsize=1)
def identity_container() -> IdentityContainer:
    users = DjangoUserRepository()
    passwords = DjangoPasswordService()
    sessions = SimpleJWTSessionRepository()
    audit = DjangoAuditRecorder()
    dependencies = IdentityDependencies(
        users=users,
        passwords=passwords,
        sessions=sessions,
        unit_of_work_factory=DjangoUnitOfWork,
        audit=audit,
    )
    authentication = AuthenticationService(dependencies)
    self_service = SelfService(dependencies)
    queries = UserQueryService(users)
    user_admin = UserAdminService(dependencies)
    return IdentityContainer(
        users=users,
        passwords=passwords,
        sessions=sessions,
        unit_of_work_factory=DjangoUnitOfWork,
        audit=audit,
        authentication=authentication,
        self_service=self_service,
        queries=queries,
        user_admin=user_admin,
    )


def identity_target_lookup(raw_user_id: str) -> AccountSnapshot | None:
    try:
        user_id = int(raw_user_id)
    except ValueError:
        return None
    return identity_container().users.get(user_id)


def authorize_identity_logout(actor_id: int, raw_refresh: str) -> None:
    identity_container().authentication.authorize_logout(actor_id, raw_refresh)


@lru_cache(maxsize=1)
def locations_container() -> LocationsContainer:
    dependencies = _locations_dependencies()
    return _build_locations_container(dependencies)


def _locations_dependencies() -> LocationDependencies:
    locations = DjangoLocationRepository()
    configs = DjangoConfigRepository()
    holidays = DjangoHolidayRepository()
    source = CsvLocationSource()
    authorization = DjangoAuthorizationGateway()
    audit = DjangoAuditRecorder()
    return LocationDependencies(
        locations=locations,
        configs=configs,
        holidays=holidays,
        source=source,
        authorization=authorization,
        audit=audit,
        unit_of_work_factory=LocationsDjangoUnitOfWork,
    )


def _build_locations_container(dependencies: LocationDependencies) -> LocationsContainer:
    return LocationsContainer(
        authorization=dependencies.authorization,
        location_queries=LocationQueryService(dependencies.locations),
        location_admin=LocationAdminService(dependencies),
        config_queries=ConfigQueryService(dependencies.configs),
        config_admin=ConfigAdminService(dependencies),
        holidays=HolidayService(dependencies),
        seed=LocationSeedService(dependencies),
        readiness=ReferenceDataReadinessService(
            ReadinessDependencies(
                dependencies.configs,
                dependencies.locations,
                dependencies.source,
                _location_source_paths(),
            )
        ),
    )


def _location_source_paths() -> tuple[Path, Path]:
    docs = settings.BASE_DIR.parent / "docs"
    return docs / "dia_chi_ttkd.csv", docs / "dia_chi_cua_hang.csv"
