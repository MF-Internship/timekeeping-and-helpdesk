import { AttendancePanel } from "@/features/attendance/ui/AttendancePanel";
import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";

export default function AttendancePage() {
  return (
    <main>
      <h1>Chấm công</h1>
      <IdentityRouteBoundary route="attendance">
        <AttendancePanel />
      </IdentityRouteBoundary>
    </main>
  );
}
