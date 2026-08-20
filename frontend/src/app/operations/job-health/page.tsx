import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { JobHealthPanel } from "@/features/operations/ui/JobHealthPanel";
import { PageIntro } from "@/shared/ui/typography";

export default function JobHealthPage() {
  return (
    <section>
      <PageIntro
        eyebrow="Vận hành"
        title="Sức khỏe đối soát chấm công"
        description="Theo dõi trạng thái và lỗi của các tác vụ nền."
      />
      <IdentityRouteBoundary route="job-health">
        <JobHealthPanel />
      </IdentityRouteBoundary>
    </section>
  );
}
