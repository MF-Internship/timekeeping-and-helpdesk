from datetime import UTC, datetime

import pytest

from tasks.domain.tasks import CompletionMethod, TaskStatus
from tasks.domain.transitions import (
    TransitionOutcome,
    build_completion_snapshot,
    decide_transition,
    resolve_block_reason,
)


@pytest.mark.unit
@pytest.mark.parametrize("source", list(TaskStatus))
@pytest.mark.parametrize("target", list(TaskStatus))
def test_canonical_transition_matrix(source: TaskStatus, target: TaskStatus) -> None:
    allowed = {
        (TaskStatus.TODO, TaskStatus.IN_PROGRESS),
        (TaskStatus.TODO, TaskStatus.BLOCKED),
        (TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED),
        (TaskStatus.BLOCKED, TaskStatus.IN_PROGRESS),
    }
    decision = decide_transition(source, target)
    if source is target and source is not TaskStatus.COMPLETED:
        assert decision.outcome is TransitionOutcome.NO_OP
    elif (source, target) in allowed:
        assert decision.outcome is TransitionOutcome.TRANSITION
    else:
        assert decision.outcome is TransitionOutcome.REJECTED


@pytest.mark.unit
def test_block_reason_prefers_dedicated_value_and_normalizes_whitespace() -> None:
    assert (
        resolve_block_reason(TaskStatus.BLOCKED, note=" fallback ", block_reason=" reason ")
        == "reason"
    )
    assert (
        resolve_block_reason(TaskStatus.BLOCKED, note=" fallback ", block_reason="  ") == "fallback"
    )
    assert resolve_block_reason(TaskStatus.IN_PROGRESS, note="note", block_reason="reason") is None
    with pytest.raises(ValueError, match="block_reason"):
        resolve_block_reason(TaskStatus.BLOCKED, note=" ", block_reason=None)


@pytest.mark.unit
def test_completion_snapshot_is_override_only_and_note_is_nonblank() -> None:
    now = datetime(2026, 8, 20, tzinfo=UTC)
    snapshot = build_completion_snapshot(7, now, " done ")
    assert snapshot.completed_by_id == 7
    assert snapshot.completed_at == now
    assert snapshot.completion_method is CompletionMethod.MANAGER_OVERRIDE
    assert snapshot.completion_note == "done"
    with pytest.raises(ValueError, match="completion_note"):
        build_completion_snapshot(7, now, "  ")
