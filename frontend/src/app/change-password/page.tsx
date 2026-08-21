import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { ChangePasswordForm } from "@/features/identity/ui/ChangePasswordForm";
import { PageIntro } from "@/shared/ui/typography";

export default function ChangePasswordPage() {
  return (
    <section>
      <PageIntro
        title="Đổi mật khẩu"
        description="Sử dụng mật khẩu mạnh và không chia sẻ mật khẩu với người khác."
      />
      <IdentityRouteBoundary route="change-password">
        <ChangePasswordForm />
      </IdentityRouteBoundary>
    </section>
  );
}
