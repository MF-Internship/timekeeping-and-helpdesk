import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { JobHealthPanel } from "@/features/operations/ui/JobHealthPanel";

export default function JobHealthPage() {
  return (
    <main>
      <h1>Sức khỏe đối soát chấm công</h1>
      <IdentityRouteBoundary route="job-health">
        <JobHealthPanel />
      </IdentityRouteBoundary>
    </main>
  );
}
