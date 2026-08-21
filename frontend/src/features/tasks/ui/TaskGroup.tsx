import type { TaskItem } from "../api/task-api";
import type { useTaskManagement } from "../model/use-task-management";
import { TaskCard } from "./TaskCard";
import styles from "./TaskManagement.module.css";

export function TaskGroup(props: {
  id: string;
  title: string;
  tasks: readonly TaskItem[];
  management: ReturnType<typeof useTaskManagement>;
  onDetail(taskId: number): void;
}) {
  return (
    <section aria-labelledby={`task-group-${props.id}`}>
      <h3 className="sr-only" id={`task-group-${props.id}`}>
        {props.title}
      </h3>
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
