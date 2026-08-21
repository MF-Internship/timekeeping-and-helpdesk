import type { TodayAttendance } from "@/features/attendance/api/attendance-api";
import { formatMinutes } from "@/shared/formatters/duration";
import { ArrowDownToLine, ArrowUpFromLine, Clock3, MapPin } from "lucide-react";
import styles from "./AttendancePanel.module.css";

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
    <ol className={styles.punchList}>
      {punches.map((punch) => (
        <PunchItem key={punch.id} punch={punch} />
      ))}
    </ol>
  );
}

function PunchItem({ punch }: { punch: TodayAttendance["punches"][number] }) {
  const isCheckIn = punch.kind === "IN";
  const Icon = isCheckIn ? ArrowDownToLine : ArrowUpFromLine;
  return (
    <li>
      <span className="sr-only">
        #{punch.punch_index} {punch.kind} — {punch.location.name}
      </span>
      <span className={styles.punchIcon}>
        <Icon aria-hidden="true" />
      </span>
      <div>
        <strong>{isCheckIn ? "Check In" : "Check Out"}</strong>
        <time dateTime={punch.recorded_at}>{formatTime(punch.recorded_at)}</time>
        <span>
          <MapPin aria-hidden="true" /> {punch.location.name}
        </span>
      </div>
      <a href={punch.maps_url} target="_blank" rel="noopener noreferrer">
        Bản đồ
      </a>
    </li>
  );
}

function SessionTimeline({ sessions }: Pick<TodayAttendance, "sessions">) {
  return (
    <section className={styles.sessions} aria-label="Phiên làm việc">
      <h3>
        <Clock3 aria-hidden="true" /> Phiên làm việc ({sessions.length})
      </h3>
      {sessions.length === 0 ? (
        <p>Chưa có phiên làm việc.</p>
      ) : (
        <ol className={styles.sessionList}>
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
      ? `${formatMinutes(session.duration_minutes ?? 0)} phút`
      : "Đang mở";
  return (
    <li>
      <span className="sr-only">
        Location {session.check_in_location_id} →{" "}
        {session.check_out_location_id ? `Location ${session.check_out_location_id}` : "chưa có"} —{" "}
        {state}
      </span>
      <span>Phiên #{session.id}</span>
      <strong>{state}</strong>
      <small>
        Điểm vào #{session.check_in_location_id} →{" "}
        {session.check_out_location_id
          ? `Điểm ra #${session.check_out_location_id}`
          : "Chưa Check Out"}
      </small>
    </li>
  );
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("vi-VN", { hour: "2-digit", minute: "2-digit" }).format(
    new Date(value),
  );
}
