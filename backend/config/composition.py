from functools import lru_cache
from pathlib import Path

from django.conf import settings

from attendance.adapters.clock import DjangoClock
from attendance.adapters.notification_facts import DjangoAttendanceNotificationFacts
from attendance.adapters.persistence.attempts import DjangoAttemptWriter
from attendance.adapters.persistence.reconciliation import DjangoReconciliationRepository
from attendance.adapters.persistence.repositories import DjangoAttendanceRepository
from attendance.adapters.persistence.unit_of_work import DjangoUnitOfWork as AttendanceUnitOfWork
from attendance.application.commands import AttendanceCommandService
from attendance.application.container import AttendanceContainer
from attendance.application.dependencies import AttendanceDependencies
from attendance.application.queries import AttendanceQueryService
from attendance.application.reconciliation import ReconciliationDependencies, ReconciliationService
from audit.adapters.persistence.recording import DjangoAuditRecorder
from config.attendance_adapters import DjangoAttendanceAuthorization, DjangoAttendanceReferenceData
from config.notification_adapters import (
    DjangoNotificationAccountFacts,
    DjangoNotificationAttendanceFacts,
    DjangoNotificationAuthorization,
    DjangoNotificationTaskFacts,
    DjangoPushSubscriptionRevoker,
    notification_shift_end,
)
from config.operations_adapters import DjangoReadOnlyRepeatableRead, DjangoReconciliationJobRuns
from config.task_adapters import (
    DjangoAssigneeDirectory,
    DjangoTaskAuthorization,
    DjangoTaskLocationDirectory,
)
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
from notifications.adapters.clock import DjangoClock as NotificationDjangoClock
from notifications.adapters.persistence.repositories import (
    DjangoDeliveryRepository,
    DjangoNotificationRepository,
    DjangoSubscriptionRepository,
)
from notifications.adapters.persistence.unit_of_work import (
    DjangoUnitOfWork as NotificationUnitOfWork,
)
from notifications.adapters.security.endpoint_policy import ExactEndpointPolicy
from notifications.adapters.security.subscription_cipher import FernetSubscriptionCipher
from notifications.adapters.web_push import WebPushTransport
from notifications.application.container import NotificationContainer, build_notification_container
from notifications.application.dependencies import NotificationDependencies
from operations.adapters.persistence.job_runs import DjangoJobRunRepository
from operations.application.container import OperationsContainer
from operations.application.dependencies import JobHealthDependencies
from operations.application.job_health import JobHealthService
from tasks.adapters.clock import DjangoClock as TaskDjangoClock
from tasks.adapters.evidence_storage import S3EvidenceStorage
from tasks.adapters.notification_facts import DjangoTaskNotificationFacts
from tasks.adapters.persistence.repositories import DjangoTaskRepository
from tasks.adapters.persistence.unit_of_work import DjangoUnitOfWork as TaskDjangoUnitOfWork
from tasks.application.container import TaskContainer, build_task_container
from tasks.application.dependencies import TaskDependencies


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
        push_subscriptions=DjangoPushSubscriptionRevoker(notification_container().subscriptions),
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


@lru_cache(maxsize=1)
def attendance_container() -> AttendanceContainer:
    authorization = DjangoAttendanceAuthorization()
    dependencies = AttendanceDependencies(
        authorization=authorization,
        clock=DjangoClock(),
        reference_data=DjangoAttendanceReferenceData(),
        repository=DjangoAttendanceRepository(),
        attempts=DjangoAttemptWriter(),
        audit=DjangoAuditRecorder(),
        unit_of_work_factory=AttendanceUnitOfWork,
        notifications=notification_container().occurrences,
    )
    return AttendanceContainer(
        authorization,
        AttendanceCommandService(dependencies),
        AttendanceQueryService(dependencies),
    )


def reconciliation_service() -> ReconciliationService:
    return ReconciliationService(
        ReconciliationDependencies(
            clock=DjangoClock(),
            repository=DjangoReconciliationRepository(),
            job_runs=DjangoReconciliationJobRuns(),
            unit_of_work_factory=AttendanceUnitOfWork,
        )
    )


@lru_cache(maxsize=1)
def operations_container() -> OperationsContainer:
    repository = DjangoReconciliationRepository()
    return OperationsContainer(
        JobHealthService(
            JobHealthDependencies(
                authorization=DjangoAuthorizationGateway(),
                clock=DjangoClock(),
                job_runs=DjangoJobRunRepository(),
                attendance_health=repository,
                read_unit_of_work_factory=DjangoReadOnlyRepeatableRead,
            )
        )
    )


@lru_cache(maxsize=1)
def task_container() -> TaskContainer:
    dependencies = TaskDependencies(
        authorization=DjangoTaskAuthorization(),
        assignees=DjangoAssigneeDirectory(),
        locations=DjangoTaskLocationDirectory(),
        repository=DjangoTaskRepository(),
        clock=TaskDjangoClock(),
        audit=DjangoAuditRecorder(),
        unit_of_work_factory=TaskDjangoUnitOfWork,
        storage=S3EvidenceStorage(),
        notifications=notification_container().occurrences,
    )
    return build_task_container(dependencies)


@lru_cache(maxsize=1)
def notification_container() -> NotificationContainer:
    cipher, endpoint_policy, transport = _web_push_adapters()
    task_facts = DjangoNotificationTaskFacts(DjangoTaskNotificationFacts(DjangoTaskAuthorization()))
    attendance_facts = DjangoNotificationAttendanceFacts(
        DjangoAttendanceNotificationFacts(DjangoAttendanceAuthorization(), notification_shift_end)
    )
    return build_notification_container(
        NotificationDependencies(
            notifications=DjangoNotificationRepository(),
            subscriptions=DjangoSubscriptionRepository(),
            deliveries=DjangoDeliveryRepository(),
            clock=NotificationDjangoClock(),
            unit_of_work_factory=NotificationUnitOfWork,
            accounts=DjangoNotificationAccountFacts(),
            tasks=task_facts,
            attendance=attendance_facts,
            authorization=DjangoNotificationAuthorization(),
            cipher=cipher,
            endpoint_policy=endpoint_policy,
            transport=transport,
        )
    )


def _web_push_adapters() -> tuple[object | None, object | None, object | None]:
    if not settings.WEB_PUSH_ENABLED:
        return None, None, None
    cipher = FernetSubscriptionCipher(tuple(settings.PUSH_SUBSCRIPTION_ENCRYPTION_KEYS))
    endpoint_policy = ExactEndpointPolicy(tuple(settings.WEB_PUSH_ALLOWED_ORIGINS))
    transport = WebPushTransport(
        vapid_private_key=settings.WEB_PUSH_VAPID_PRIVATE_KEY,
        vapid_subject=settings.WEB_PUSH_VAPID_SUBJECT,
    )
    return cipher, endpoint_policy, transport
