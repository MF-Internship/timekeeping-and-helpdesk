import { Badge } from "@/shared/ui/badge";
import { Card } from "@/shared/ui/card";

import type { TodayAttendance } from "../api/attendance-api";
import styles from "./AttendancePanel.module.css";

export function AttendanceContextHeader({ today }: { today: TodayAttendance }) {
  const open = today.has_open_session;
  return (
    <Card className={styles.context}>
      <div>
        <p className={styles.eyebrow}>Trạng thái chấm công</p>
        <h2>{open ? "Đang trong ca làm việc" : "Sẵn sàng bắt đầu ca"}</h2>
      </div>
      <Badge tone={open ? "ready" : "neutral"} icon={open ? "●" : "○"}>
        {open ? "Đang trong ca" : "Chưa vào ca"}
      </Badge>
    </Card>
  );
}
