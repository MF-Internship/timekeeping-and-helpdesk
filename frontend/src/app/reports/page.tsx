import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { ReportsPanel } from "@/features/reports/ui/ReportsPanel";
import { PageIntro } from "@/shared/ui/typography";

export default function ReportsPage() {
  return (
    <section>
      <PageIntro
        eyebrow="Báo cáo"
        title="Báo cáo chấm công và công việc"
        description="Theo dõi trạng thái chấm công, chất lượng lượt thử và tiến độ công việc."
      />
      <IdentityRouteBoundary route="reports">
        <ReportsPanel />
      </IdentityRouteBoundary>
    </section>
  );
}
