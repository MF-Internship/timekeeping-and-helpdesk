import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { HolidayManager } from "@/features/locations/ui/HolidayManager";
import { PageIntro } from "@/shared/ui/typography";

export default function HolidaysPage() {
  return (
    <section>
      <PageIntro
        eyebrow="Lịch làm việc"
        title="Ngày nghỉ"
        description="Cấu hình ngày nghỉ được áp dụng trong hệ thống."
      />
      <IdentityRouteBoundary route="holidays">
        <HolidayManager />
      </IdentityRouteBoundary>
    </section>
  );
}
