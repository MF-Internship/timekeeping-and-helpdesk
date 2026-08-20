from attendance.models import AttendanceAttempt
from attendance.ports.attempts import AttemptDraft


class DjangoAttemptWriter:
    def append(self, draft: AttemptDraft) -> None:
        AttendanceAttempt.objects.create(
            user_id=draft.user_id,
            kind=draft.kind.value,
            work_date=draft.work_date,
            recorded_at=draft.recorded_at,
            outcome=draft.outcome.value,
            attendance_id=draft.attendance_id,
            captured_latitude=draft.latitude,
            captured_longitude=draft.longitude,
            accuracy_m=draft.accuracy_m,
            nearest_location_id=draft.nearest_location_id,
            nearest_distance_m=draft.nearest_distance_m,
            candidate_count=draft.candidate_count,
            device_metadata=draft.device_metadata,
            request_ip=draft.request_ip,
        )
