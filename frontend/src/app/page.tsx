import { HomeDashboard } from "@/features/home/ui/HomeDashboard";
import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";

export default function Page() {
  return (
    <IdentityRouteBoundary route="home">
      <HomeDashboard />
    </IdentityRouteBoundary>
  );
}
