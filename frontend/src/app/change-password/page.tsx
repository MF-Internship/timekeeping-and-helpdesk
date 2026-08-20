import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { ChangePasswordForm } from "@/features/identity/ui/ChangePasswordForm";

export default function ChangePasswordPage() {
  return (
    <section>
      <IdentityRouteBoundary route="change-password">
        <ChangePasswordForm />
      </IdentityRouteBoundary>
    </section>
  );
}
