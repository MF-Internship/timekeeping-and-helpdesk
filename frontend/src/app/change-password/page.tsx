import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { ChangePasswordForm } from "@/features/identity/ui/ChangePasswordForm";

export default function ChangePasswordPage() {
  return (
    <main>
      <h1>Đổi mật khẩu</h1>
      <IdentityRouteBoundary route="change-password">
        <ChangePasswordForm />
      </IdentityRouteBoundary>
    </main>
  );
}
