import { AttendancePanel } from "@/features/attendance/ui/AttendancePanel";
import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";

export default function AttendancePage() {
  return (
    <IdentityRouteBoundary route="attendance">
      <AttendancePanel />
    </IdentityRouteBoundary>
  );
}
