import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { UserDirectory } from "@/features/identity/ui/UserDirectory";

export default function UsersPage() {
  return (
    <main>
      <h1>Quản lý người dùng</h1>
      <IdentityRouteBoundary route="users">
        <UserDirectory />
      </IdentityRouteBoundary>
    </main>
  );
}
