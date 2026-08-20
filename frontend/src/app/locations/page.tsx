import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { LocationDirectory } from "@/features/locations/ui/LocationDirectory";
import { PageIntro } from "@/shared/ui/typography";

export default function LocationsPage() {
  return (
    <section>
      <PageIntro eyebrow="Danh mục" title="Địa điểm" description="Quản lý địa điểm và vùng làm việc đã đăng ký." />
      <IdentityRouteBoundary route="locations">
        <LocationDirectory />
      </IdentityRouteBoundary>
    </section>
  );
}
