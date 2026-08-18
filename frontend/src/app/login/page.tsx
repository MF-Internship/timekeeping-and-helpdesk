import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { LoginForm } from "@/features/identity/ui/LoginForm";

export default function LoginPage() {
  return (
    <main>
      <h1>Đăng nhập</h1>
      <IdentityRouteBoundary route="login">
        <LoginForm />
      </IdentityRouteBoundary>
    </main>
  );
}
