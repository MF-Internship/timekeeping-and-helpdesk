import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { ConfigEditor } from "@/features/locations/ui/ConfigEditor";

export default function ConfigPage() {
  return (
    <main>
      <h1>Cấu hình vận hành</h1>
      <IdentityRouteBoundary route="config">
        <ConfigEditor />
      </IdentityRouteBoundary>
    </main>
  );
}
