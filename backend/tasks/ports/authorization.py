from __future__ import annotations

from enum import StrEnum
from typing import Protocol


class TaskCreateMode(StrEnum):
    SELF = "SELF"
    ASSIGN = "ASSIGN"


class TaskReadScope(StrEnum):
    SELF = "SELF"
    ALL = "ALL"


class TaskUpdateScope(StrEnum):
    SELF = "SELF"
    ANY = "ANY"


class TaskAuthorization(Protocol):
    def authorize_create(self, actor_id: int) -> TaskCreateMode: ...
    def authorize_read(self, actor_id: int) -> TaskReadScope: ...
    def authorize_update(self, actor_id: int) -> TaskUpdateScope: ...
    def authorize_delete(self, actor_id: int) -> None: ...
    def authorize_override(self, actor_id: int) -> None: ...
    def authorize_field_completion(self, actor_id: int) -> None: ...
    def authorize_photo_read(self, actor_id: int) -> TaskReadScope: ...
