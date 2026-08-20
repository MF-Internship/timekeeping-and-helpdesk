import { UI_MESSAGES } from "@/shared/messages";

import type { TaskItem } from "../api/task-api";
import type { useTaskManagement } from "../model/use-task-management";
import { TaskCard } from "./TaskCard";
import styles from "./TaskManagement.module.css";

const LABELS = {
  overdue: UI_MESSAGES.tasks.overdue,
  today: UI_MESSAGES.tasks.today,
  upcoming: UI_MESSAGES.tasks.upcoming,
  completed: UI_MESSAGES.tasks.completedGroup,
} as const;

export function TaskGroup(props: {
  group: keyof typeof LABELS;
  tasks: readonly TaskItem[];
  management: ReturnType<typeof useTaskManagement>;
  onDetail(taskId: number): void;
}) {
  return (
    <section aria-labelledby={`task-group-${props.group}`}>
      <h2 id={`task-group-${props.group}`}>{LABELS[props.group]}</h2>
      {props.tasks.length === 0 ? <p>Không có công việc.</p> : null}
      <div className={styles.group}>
        {props.tasks.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            management={props.management}
            onDetail={props.onDetail}
          />
        ))}
      </div>
    </section>
  );
}
