from dataclasses import dataclass

from tasks.application.commands import TaskCommandService
from tasks.application.dependencies import TaskDependencies
from tasks.application.evidence import TaskEvidenceService
from tasks.application.evidence_cleanup import EvidenceUploadCleanupService
from tasks.application.queries import TaskQueryService
from tasks.ports.authorization import TaskAuthorization


@dataclass(frozen=True, slots=True)
class TaskContainer:
    authorization: TaskAuthorization
    commands: TaskCommandService
    queries: TaskQueryService
    evidence: TaskEvidenceService
    evidence_cleanup: EvidenceUploadCleanupService


def build_task_container(dependencies: TaskDependencies) -> TaskContainer:
    return TaskContainer(
        dependencies.authorization,
        TaskCommandService(dependencies),
        TaskQueryService(dependencies),
        TaskEvidenceService(dependencies),
        EvidenceUploadCleanupService(dependencies),
    )
