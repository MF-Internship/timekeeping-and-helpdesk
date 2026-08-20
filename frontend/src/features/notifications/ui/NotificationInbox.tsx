"use client";

import Link from "next/link";

import { UI_MESSAGES } from "@/shared/messages";
import { LoadingState } from "@/shared/ui/async-state";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { PageIntro } from "@/shared/ui/typography";

import type { NotificationEventType, NotificationItem } from "../api/notification-api";
import { useNotifications } from "../model/use-notifications";
import { PushOptInControl } from "./PushOptInControl";
import styles from "./Notifications.module.css";

const EVENT_LABELS: Record<NotificationEventType, string> = {
  TASK_ASSIGNED: "Công việc mới được giao",
  TASK_UPCOMING: "Công việc sắp đến hạn",
  TASK_OVERDUE: "Công việc quá hạn",
  ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END: "Ca chấm công chưa đóng",
  MULTI_ASSIGNEE_TASK_COMPLETED: "Công việc chung đã hoàn thành",
};

export function NotificationInbox() {
  const notifications = useNotifications();
  return (
    <section className={styles.panel}>
      <PageIntro
        eyebrow="Feature 008"
        title={UI_MESSAGES.notifications.title}
        description="Hộp thư trong ứng dụng là nguồn thông báo đầy đủ, kể cả khi Web Push bị tắt hoặc không khả dụng."
      />
      <PushOptInControl />
      <InboxContent notifications={notifications} />
    </section>
  );
}

function InboxContent({ notifications }: { notifications: ReturnType<typeof useNotifications> }) {
  if (notifications.loadState.kind === "loading") return <LoadingState />;
  if (notifications.loadState.kind === "failed") {
    return (
      <Card role="alert">
        <p>{UI_MESSAGES.notifications.loadFailure}</p>
        <Button onClick={() => void notifications.refresh()}>{UI_MESSAGES.retry}</Button>
      </Card>
    );
  }
  const { data, refreshError } = notifications.loadState;
  return (
    <section aria-labelledby="notification-inbox-heading">
      <header className={styles.inboxHeader}>
        <h3 id="notification-inbox-heading">Thông báo trong ứng dụng</h3>
        <Badge tone={data.unread_count > 0 ? "warning" : "neutral"}>
          {data.unread_count} chưa đọc
        </Badge>
        <Button variant="quiet" onClick={() => void notifications.refresh()}>
          Làm mới
        </Button>
      </header>
      {refreshError ? <p role="alert">{UI_MESSAGES.notifications.refreshFailure}</p> : null}
      {data.items.length === 0 ? <p role="status">{UI_MESSAGES.notifications.empty}</p> : null}
      <ul className={styles.list}>
        {data.items.map((item) => (
          <NotificationRow
            key={item.public_id}
            item={item}
            readState={notifications.reads[item.public_id]}
            onRead={() => void notifications.markRead(item.public_id)}
          />
        ))}
      </ul>
    </section>
  );
}

function NotificationRow(props: {
  item: NotificationItem;
  readState: ReturnType<typeof useNotifications>["reads"][string];
  onRead(): void;
}) {
  const pending = props.readState?.kind === "submitting";
  return (
    <li>
      <Card className={props.item.is_unread ? styles.unread : undefined}>
        <div className={styles.itemHeading}>
          <h4>{props.item.title}</h4>
          <Badge tone={props.item.is_unread ? "warning" : "neutral"}>
            {props.item.is_unread ? "Chưa đọc" : "Đã đọc"}
          </Badge>
        </div>
        <p>{EVENT_LABELS[props.item.event_type]}</p>
        <time dateTime={props.item.created_at}>
          {new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium", timeStyle: "short" }).format(
            new Date(props.item.created_at),
          )}
        </time>
        <div className="actions">
          <Link className={styles.openLink} href={`/notifications/open/${props.item.public_id}`}>
            Mở đích đến an toàn
          </Link>
          <ReadAction unread={props.item.is_unread} pending={pending} onRead={props.onRead} />
        </div>
        {props.readState?.kind === "failed" ? (
          <p role="alert">
            {UI_MESSAGES.notifications.readFailure}{" "}
            <Button variant="quiet" onClick={props.onRead}>
              Thử lại
            </Button>
          </p>
        ) : null}
      </Card>
    </li>
  );
}

function ReadAction(props: { unread: boolean; pending: boolean; onRead(): void }) {
  if (!props.unread) return null;
  return (
    <Button loading={props.pending} onClick={props.onRead}>
      {props.pending ? "Đang đánh dấu…" : "Đánh dấu đã đọc"}
    </Button>
  );
}
