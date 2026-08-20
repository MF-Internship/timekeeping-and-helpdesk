import type { TodayAttendance } from "@/features/attendance/api/attendance-api";

type TimelineProps = Pick<TodayAttendance, "punches" | "sessions">;

export function TodayTimeline({ punches, sessions }: TimelineProps) {
  return (
    <>
      <PunchTimeline punches={punches} />
      <SessionTimeline sessions={sessions} />
    </>
  );
}

function PunchTimeline({ punches }: Pick<TodayAttendance, "punches">) {
  if (punches.length === 0) return <p>Chưa có lượt chấm công hôm nay.</p>;
  return (
    <ol className="record-list">
      {punches.map((punch) => (
        <PunchItem key={punch.id} punch={punch} />
      ))}
    </ol>
  );
}

function PunchItem({ punch }: { punch: TodayAttendance["punches"][number] }) {
  return (
    <li>
      <span>
        #{punch.punch_index} {punch.kind} — {punch.recorded_at} — {punch.location.name}
      </span>
      <a href={punch.maps_url} target="_blank" rel="noopener noreferrer">
        Bản đồ
      </a>
    </li>
  );
}

function SessionTimeline({ sessions }: Pick<TodayAttendance, "sessions">) {
  return (
    <section aria-label="Phiên làm việc">
      <h3>Phiên làm việc ({sessions.length})</h3>
      {sessions.length === 0 ? (
        <p>Chưa có phiên làm việc.</p>
      ) : (
        <ol>
          {sessions.map((session) => (
            <SessionItem key={session.id} session={session} />
          ))}
        </ol>
      )}
    </section>
  );
}

function SessionItem({ session }: { session: TodayAttendance["sessions"][number] }) {
  const state = session.closed_by_job
    ? "Thiếu Check Out"
    : session.check_out_at
      ? `${session.duration_minutes} phút`
      : "Đang mở";
  return (
    <li>
      #{session.id}: Location {session.check_in_location_id} →{" "}
      {session.check_out_location_id ? `Location ${session.check_out_location_id}` : "chưa có"} —{" "}
      {state}
    </li>
  );
}
