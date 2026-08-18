from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    LEADER = "LEADER"
    MANAGER = "MANAGER"
    HELPDESK = "HELPDESK"


class PermissionAction(StrEnum):
    ATTENDANCE_CHECK_IN_SELF = "attendance.check_in.self"
    ATTENDANCE_CHECK_OUT_SELF = "attendance.check_out.self"
    ATTENDANCE_VIEW_SELF = "attendance.view.self"
    ATTENDANCE_VIEW_ALL = "attendance.view.all"
    TASK_CREATE_SELF = "task.create.self"
    TASK_COMPLETE_FIELD = "task.complete.field"
    TASK_VIEW_SELF = "task.view.self"
    TASK_UPDATE_SELF = "task.update.self"
    TASK_VIEW_ALL = "task.view.all"
    TASK_CREATE_ASSIGN = "task.create.assign"
    TASK_UPDATE_ANY = "task.update.any"
    TASK_COMPLETE_OVERRIDE = "task.complete.override"
    LOCATION_VIEW = "location.view"
    CONFIG_VIEW = "config.view"
    LOCATION_MANAGE = "location.manage"
    CONFIG_MANAGE_ATTENDANCE = "config.manage_attendance"
    HOLIDAY_MANAGE = "holiday.manage"
    USER_VIEW = "user.view"
    USER_MANAGE = "user.manage"
    USER_ASSIGN_ROLE = "user.assign_role"
    REPORT_VIEW_SELF = "report.view.self"
    REPORT_VIEW_ALL = "report.view.all"
    REPORT_EXPORT = "report.export"
    PHOTO_VIEW_ALL = "photo.view.all"
    PHOTO_VIEW_SELF = "photo.view.self"

    @property
    def is_mutation(self) -> bool:
        return self not in {
            self.ATTENDANCE_VIEW_SELF,
            self.ATTENDANCE_VIEW_ALL,
            self.TASK_VIEW_SELF,
            self.TASK_VIEW_ALL,
            self.LOCATION_VIEW,
            self.CONFIG_VIEW,
            self.REPORT_VIEW_SELF,
            self.REPORT_VIEW_ALL,
            self.REPORT_EXPORT,
            self.PHOTO_VIEW_ALL,
            self.PHOTO_VIEW_SELF,
        }


ROLE_PERMISSIONS: dict[Role, frozenset[PermissionAction]] = {
    Role.LEADER: frozenset(
        {
            PermissionAction.ATTENDANCE_VIEW_ALL,
            PermissionAction.TASK_VIEW_ALL,
            PermissionAction.LOCATION_VIEW,
            PermissionAction.CONFIG_VIEW,
            PermissionAction.REPORT_VIEW_ALL,
            PermissionAction.REPORT_EXPORT,
            PermissionAction.PHOTO_VIEW_ALL,
        }
    ),
    Role.MANAGER: frozenset(
        {
            PermissionAction.ATTENDANCE_VIEW_ALL,
            PermissionAction.TASK_CREATE_SELF,
            PermissionAction.TASK_COMPLETE_FIELD,
            PermissionAction.TASK_VIEW_ALL,
            PermissionAction.TASK_CREATE_ASSIGN,
            PermissionAction.TASK_UPDATE_ANY,
            PermissionAction.TASK_COMPLETE_OVERRIDE,
            PermissionAction.LOCATION_VIEW,
            PermissionAction.CONFIG_VIEW,
            PermissionAction.LOCATION_MANAGE,
            PermissionAction.CONFIG_MANAGE_ATTENDANCE,
            PermissionAction.HOLIDAY_MANAGE,
            PermissionAction.USER_VIEW,
            PermissionAction.USER_MANAGE,
            PermissionAction.USER_ASSIGN_ROLE,
            PermissionAction.REPORT_VIEW_ALL,
            PermissionAction.REPORT_EXPORT,
            PermissionAction.PHOTO_VIEW_ALL,
        }
    ),
    Role.HELPDESK: frozenset(
        {
            PermissionAction.ATTENDANCE_CHECK_IN_SELF,
            PermissionAction.ATTENDANCE_CHECK_OUT_SELF,
            PermissionAction.ATTENDANCE_VIEW_SELF,
            PermissionAction.TASK_CREATE_SELF,
            PermissionAction.TASK_COMPLETE_FIELD,
            PermissionAction.TASK_VIEW_SELF,
            PermissionAction.TASK_UPDATE_SELF,
            PermissionAction.LOCATION_VIEW,
            PermissionAction.CONFIG_VIEW,
            PermissionAction.REPORT_VIEW_SELF,
            PermissionAction.PHOTO_VIEW_SELF,
        }
    ),
}

PERMISSION_IMPLIES: dict[PermissionAction, PermissionAction] = {
    PermissionAction.TASK_VIEW_ALL: PermissionAction.TASK_VIEW_SELF,
    PermissionAction.TASK_UPDATE_ANY: PermissionAction.TASK_UPDATE_SELF,
    PermissionAction.ATTENDANCE_VIEW_ALL: PermissionAction.ATTENDANCE_VIEW_SELF,
    PermissionAction.REPORT_VIEW_ALL: PermissionAction.REPORT_VIEW_SELF,
    PermissionAction.PHOTO_VIEW_ALL: PermissionAction.PHOTO_VIEW_SELF,
}

ASSIGNABLE_ROLES = frozenset({Role.LEADER, Role.HELPDESK})


@dataclass(frozen=True, slots=True)
class PermissionDecision:
    requested_action: PermissionAction
    allowed: bool
    granted_by: PermissionAction | None


def decide_permission(role: Role, requested_action: PermissionAction) -> PermissionDecision:
    grants = ROLE_PERMISSIONS[role]
    if requested_action in grants:
        return PermissionDecision(requested_action, True, requested_action)
    granted_by = next(
        (grant for grant in grants if PERMISSION_IMPLIES.get(grant) == requested_action),
        None,
    )
    return PermissionDecision(requested_action, granted_by is not None, granted_by)


def effective_capabilities(role: Role) -> frozenset[PermissionAction]:
    direct = ROLE_PERMISSIONS[role]
    implied = {PERMISSION_IMPLIES[action] for action in direct if action in PERMISSION_IMPLIES}
    return direct | implied
