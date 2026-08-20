import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { TaskManagementPanel } from "@/features/tasks/ui/TaskManagementPanel";

export default function TasksPage() {
  return (
    <IdentityRouteBoundary route="tasks">
      <TaskManagementPanel />
    </IdentityRouteBoundary>
  );
}
