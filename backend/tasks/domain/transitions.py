from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from tasks.domain.tasks import CompletionMethod, CompletionSnapshot, TaskStatus


class TransitionOutcome(StrEnum):
    TRANSITION = "TRANSITION"
    NO_OP = "NO_OP"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class TransitionDecision:
    source: TaskStatus
    target: TaskStatus
    outcome: TransitionOutcome


_ALLOWED = frozenset(
    {
        (TaskStatus.TODO, TaskStatus.IN_PROGRESS),
        (TaskStatus.TODO, TaskStatus.BLOCKED),
        (TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED),
        (TaskStatus.BLOCKED, TaskStatus.IN_PROGRESS),
    }
)


def decide_transition(source: TaskStatus, target: TaskStatus) -> TransitionDecision:
    if source is TaskStatus.COMPLETED or target is TaskStatus.COMPLETED:
        return TransitionDecision(source, target, TransitionOutcome.REJECTED)
    if source is target:
        return TransitionDecision(source, target, TransitionOutcome.NO_OP)
    outcome = (
        TransitionOutcome.TRANSITION if (source, target) in _ALLOWED else TransitionOutcome.REJECTED
    )
    return TransitionDecision(source, target, outcome)


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def resolve_block_reason(
    target: TaskStatus, *, note: str | None, block_reason: str | None
) -> str | None:
    if target is not TaskStatus.BLOCKED:
        return None
    resolved = normalize_optional_text(block_reason) or normalize_optional_text(note)
    if resolved is None:
        raise ValueError("block_reason")
    return resolved


def build_completion_snapshot(
    actor_id: int,
    completed_at: datetime,
    completion_note: str,
) -> CompletionSnapshot:
    normalized = normalize_optional_text(completion_note)
    if normalized is None:
        raise ValueError("completion_note")
    return CompletionSnapshot(
        completed_by_id=actor_id,
        completed_at=completed_at,
        completion_method=CompletionMethod.MANAGER_OVERRIDE,
        completion_note=normalized,
    )
