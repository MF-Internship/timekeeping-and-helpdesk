from attendance.application.dto import AttendanceSnapshot, IndexedPunch


def indexed_punches(punches: tuple[AttendanceSnapshot, ...]) -> tuple[IndexedPunch, ...]:
    ordered = sorted(punches, key=lambda item: (item.recorded_at, item.id))
    return tuple(IndexedPunch(punch, index) for index, punch in enumerate(ordered, start=1))


def punch_index(punches: tuple[AttendanceSnapshot, ...], attendance_id: int) -> int:
    return next(
        item.punch_index for item in indexed_punches(punches) if item.attendance.id == attendance_id
    )
