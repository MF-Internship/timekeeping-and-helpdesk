import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { AccountPanel } from "@/features/identity/ui/AccountPanel";
export default function AccountPage() {
  return (
    <IdentityRouteBoundary route="account">
      <AccountPanel />
    </IdentityRouteBoundary>
  );
}
