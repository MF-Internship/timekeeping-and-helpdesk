import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { LoginForm } from "@/features/identity/ui/LoginForm";
import { PageIntro } from "@/shared/ui/typography";

export default function LoginPage() {
  return (
    <section>
      <PageIntro title="Đăng nhập" description="Sử dụng tài khoản nội bộ để truy cập hệ thống." />
      <IdentityRouteBoundary route="login">
        <LoginForm />
      </IdentityRouteBoundary>
    </section>
  );
}
