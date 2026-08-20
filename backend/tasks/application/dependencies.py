from collections.abc import Callable
from dataclasses import dataclass, field

from audit.ports.recording import AuditRecorder
from tasks.ports.assignees import AssigneeDirectory
from tasks.ports.authorization import TaskAuthorization
from tasks.ports.clock import Clock
from tasks.ports.evidence import EvidenceStorage
from tasks.ports.locations import LocationDirectory
from tasks.ports.notifications import NoopTaskNotificationSink, TaskNotificationSink
from tasks.ports.repositories import TaskRepository
from tasks.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class TaskDependencies:
    authorization: TaskAuthorization
    assignees: AssigneeDirectory
    locations: LocationDirectory
    repository: TaskRepository
    clock: Clock
    audit: AuditRecorder
    unit_of_work_factory: Callable[[], UnitOfWork]
    storage: EvidenceStorage | None = None
    notifications: TaskNotificationSink = field(default_factory=NoopTaskNotificationSink)
