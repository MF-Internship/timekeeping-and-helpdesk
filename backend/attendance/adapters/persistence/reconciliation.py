from __future__ import annotations

from datetime import date

from django.db.models import Exists, OuterRef

from attendance.domain.attendance import AttendanceAnomalyReason
from attendance.models import AttendanceAnomaly, AttendanceSession
from operations.ports.attendance_health import AttendanceHealthEvidence


class DjangoReconciliationRepository:
    def candidate_ids(self, current_date: date) -> tuple[int, ...]:
        return tuple(
            AttendanceSession.objects.filter(
                work_date__lt=current_date,
                check_out__isnull=True,
                closed_by_job=False,
            )
            .order_by("work_date", "id")
            .values_list("id", flat=True)
        )

    def reconcile_locked(self, session_id: int, current_date: date) -> bool:
        session = AttendanceSession.objects.select_for_update().get(pk=session_id)
        if not (
            session.work_date < current_date
            and session.check_out_id is None  # type: ignore[attr-defined]
            and not session.closed_by_job
        ):
            return False
        session.closed_by_job = True
        session.save(update_fields=["closed_by_job"])
        AttendanceAnomaly.objects.create(
            attendance_id=session.check_in_id,  # type: ignore[attr-defined]
            reason=AttendanceAnomalyReason.MISSING_CHECK_OUT.value,
            metadata={},
        )
        return True

    def read_evidence(self, current_date: date) -> AttendanceHealthEvidence:
        missing = AttendanceAnomaly.objects.filter(
            attendance_id=OuterRef("check_in_id"),
            reason=AttendanceAnomalyReason.MISSING_CHECK_OUT.value,
        )
        closed = AttendanceSession.objects.filter(closed_by_job=True).annotate(
            has_missing=Exists(missing)
        )
        linked_closed = AttendanceSession.objects.filter(
            closed_by_job=True,
            check_in_id=OuterRef("attendance_id"),
        )
        missing_rows = AttendanceAnomaly.objects.filter(
            reason=AttendanceAnomalyReason.MISSING_CHECK_OUT.value
        ).annotate(has_closed=Exists(linked_closed))
        return AttendanceHealthEvidence(
            overdue_open_session_count=AttendanceSession.objects.filter(
                work_date__lt=current_date, check_out__isnull=True, closed_by_job=False
            ).count(),
            job_closed_session_count=closed.count(),
            missing_checkout_anomaly_count=missing_rows.count(),
            job_closed_without_anomaly_count=closed.filter(has_missing=False).count(),
            anomaly_without_job_closed_count=missing_rows.filter(has_closed=False).count(),
        )
