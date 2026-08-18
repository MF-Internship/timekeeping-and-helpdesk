import type { TodayAttendance } from "@/features/attendance/api/attendance-api";

export function TodayTimeline({ punches }: { punches: TodayAttendance["punches"] }) {
  if (punches.length === 0) return <p>Chưa có lượt chấm công hôm nay.</p>;
  return (
    <ol className="record-list">
      {punches.map((punch) => (
        <li key={punch.id}>
          <span>
            #{punch.punch_index} {punch.kind} — {punch.recorded_at} — {punch.location.name}
          </span>
          <a href={punch.maps_url} target="_blank" rel="noopener noreferrer">
            Bản đồ
          </a>
        </li>
      ))}
    </ol>
  );
}
