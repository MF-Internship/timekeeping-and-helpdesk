import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { HolidayManager } from "@/features/locations/ui/HolidayManager";

export default function HolidaysPage() {
  return (
    <main>
      <h1>Ngày nghỉ</h1>
      <IdentityRouteBoundary route="holidays">
        <HolidayManager />
      </IdentityRouteBoundary>
    </main>
  );
}
