import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { ConfigEditor } from "@/features/locations/ui/ConfigEditor";
import { PageIntro } from "@/shared/ui/typography";

export default function ConfigPage() {
  return (
    <section>
      <PageIntro eyebrow="Quản trị" title="Cấu hình vận hành" description="Điều chỉnh quy tắc dùng chung có kiểm soát." />
      <IdentityRouteBoundary route="config">
        <ConfigEditor />
      </IdentityRouteBoundary>
    </section>
  );
}
