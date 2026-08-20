from collections.abc import Callable

from django.urls import URLPattern, path

from tasks.adapters.api.views import (
    TaskDetailView,
    TaskEvidenceUploadView,
    TaskFieldCompletionView,
    TaskListCreateView,
    TaskOverrideView,
    TaskPhotoAccessView,
    TaskStatusView,
)
from tasks.application.container import TaskContainer


def task_urlpatterns(container: Callable[[], TaskContainer]) -> list[URLPattern]:
    list_create = TaskListCreateView.as_view(container_provider=container)
    detail = TaskDetailView.as_view(container_provider=container)
    status = TaskStatusView.as_view(container_provider=container)
    override = TaskOverrideView.as_view(container_provider=container)
    upload = TaskEvidenceUploadView.as_view(container_provider=container)
    field = TaskFieldCompletionView.as_view(container_provider=container)
    photo = TaskPhotoAccessView.as_view(container_provider=container)
    return [
        path("tasks/", list_create, name="tasks-list"),
        path("tasks/<str:task_id>/", detail, name="tasks-detail"),
        path("tasks/<str:task_id>/status", status, name="tasks-status"),
        path("tasks/<str:task_id>/complete-override", override, name="tasks-complete-override"),
        path("tasks/<str:task_id>/evidence-uploads", upload, name="tasks-evidence-uploads"),
        path("tasks/<str:task_id>/complete-field", field, name="tasks-complete-field"),
        path("tasks/<str:task_id>/photos/<str:photo_id>/access", photo, name="tasks-photo-access"),
    ]
