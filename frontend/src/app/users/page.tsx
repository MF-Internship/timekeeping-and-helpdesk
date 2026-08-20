import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { UserDirectory } from "@/features/identity/ui/UserDirectory";
import { PageIntro } from "@/shared/ui/typography";

export default function UsersPage() {
  return (
    <section>
      <PageIntro
        eyebrow="Quản trị"
        title="Người dùng"
        description="Quản lý tài khoản, vai trò và trạng thái truy cập."
      />
      <IdentityRouteBoundary route="users">
        <UserDirectory />
      </IdentityRouteBoundary>
    </section>
  );
}
