import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { NotificationInbox } from "@/features/notifications/ui/NotificationInbox";

export default function NotificationsPage() {
  return (
    <IdentityRouteBoundary route="notifications">
      <NotificationInbox />
    </IdentityRouteBoundary>
  );
}
