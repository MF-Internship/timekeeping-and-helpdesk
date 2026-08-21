"use client";
import * as Tabs from "@radix-ui/react-tabs";
import { Bell, BriefcaseBusiness, Clock3, ExternalLink, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { UI_MESSAGES } from "@/shared/messages";
import { EmptyState, ErrorState, SkeletonState } from "@/shared/ui/async-state";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { PageHeader } from "@/shared/ui/typography";
import type { NotificationEventType, NotificationItem } from "../api/notification-api";
import { groupNotifications } from "../model/notification-groups";
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
const EVENT_ICONS: Record<NotificationEventType, typeof Bell> = {
  TASK_ASSIGNED: BriefcaseBusiness,
  TASK_UPCOMING: BriefcaseBusiness,
  TASK_OVERDUE: BriefcaseBusiness,
  ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END: Clock3,
  MULTI_ASSIGNEE_TASK_COMPLETED: BriefcaseBusiness,
};
export function NotificationInbox() {
  const notifications = useNotifications();
  return (
    <section className={styles.panel}>
      <PageHeader
        title={UI_MESSAGES.notifications.title}
        description="Cập nhật công việc và chấm công cần bạn chú ý."
      />
      <PushOptInControl />
      <InboxContent notifications={notifications} />
    </section>
  );
}
function InboxContent({ notifications }: { notifications: ReturnType<typeof useNotifications> }) {
  const [tab, setTab] = useState("all");
  if (notifications.loadState.kind === "loading") return <SkeletonState rows={4} />;
  if (notifications.loadState.kind === "failed")
    return (
      <ErrorState
        message={UI_MESSAGES.notifications.loadFailure}
        onRetry={() => void notifications.refresh()}
      />
    );
  const { data, refreshError } = notifications.loadState;
  const items = tab === "unread" ? data.items.filter((item) => item.is_unread) : data.items;
  return (
    <Tabs.Root value={tab} onValueChange={setTab}>
      <div className={styles.inboxHeader}>
        <Tabs.List className={styles.tabs} aria-label="Lọc thông báo">
          <Tabs.Trigger value="all">Tất cả</Tabs.Trigger>
          <Tabs.Trigger value="unread">
            Chưa đọc <span>{data.unread_count}</span>
          </Tabs.Trigger>
        </Tabs.List>
        <Button
          variant="quiet"
          aria-label="Làm mới thông báo"
          onClick={() => void notifications.refresh()}
        >
          <RefreshCw aria-hidden="true" size={17} />
          Làm mới
        </Button>
      </div>
      {refreshError ? <p role="alert">{UI_MESSAGES.notifications.refreshFailure}</p> : null}
      <Tabs.Content value={tab}>
        {items.length === 0 ? (
          <EmptyState
            message={
              tab === "unread" ? "Bạn đã đọc tất cả thông báo." : UI_MESSAGES.notifications.empty
            }
          />
        ) : (
          groupNotifications(items).map((group) => (
            <section
              className={styles.group}
              key={group.period}
              aria-labelledby={`notifications-${group.period}`}
            >
              <h3 id={`notifications-${group.period}`}>{group.label}</h3>
              <ul className={styles.list}>
                {group.items.map((item) => (
                  <NotificationRow
                    key={item.public_id}
                    item={item}
                    readState={notifications.reads[item.public_id]}
                    onRead={() => void notifications.markRead(item.public_id)}
                  />
                ))}
              </ul>
            </section>
          ))
        )}
      </Tabs.Content>
    </Tabs.Root>
  );
}
function NotificationRow({
  item,
  readState,
  onRead,
}: {
  item: NotificationItem;
  readState: ReturnType<typeof useNotifications>["reads"][string];
  onRead(): void;
}) {
  const pending = readState?.kind === "submitting";
  const Icon = EVENT_ICONS[item.event_type];
  return (
    <li className={item.is_unread ? styles.unread : undefined}>
      <div className={styles.eventIcon}>
        <Icon aria-hidden="true" />
      </div>
      <div className={styles.itemBody}>
        <div className={styles.itemHeading}>
          <h4>{item.title}</h4>
          {item.is_unread ? <Badge tone="warning">Chưa đọc</Badge> : null}
        </div>
        <p>{EVENT_LABELS[item.event_type]}</p>
        <time dateTime={item.created_at}>
          {new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium", timeStyle: "short" }).format(
            new Date(item.created_at),
          )}
        </time>
        <ReadFailure failed={readState?.kind === "failed"} onRead={onRead} />
      </div>
      <div className={styles.actions}>
        <Link
          className={styles.openLink}
          href={`/notifications/open/${item.public_id}`}
          aria-label="Mở đích đến an toàn"
        >
          <ExternalLink aria-hidden="true" />
          Mở đích đến an toàn
        </Link>
        <ReadButton unread={item.is_unread} pending={pending} onRead={onRead} />
      </div>
    </li>
  );
}

function ReadFailure({ failed, onRead }: { failed: boolean; onRead(): void }) {
  if (!failed) return null;
  return (
    <p role="alert">
      {UI_MESSAGES.notifications.readFailure}{" "}
      <Button variant="quiet" onClick={onRead}>
        Thử lại
      </Button>
    </p>
  );
}

function ReadButton({
  unread,
  pending,
  onRead,
}: {
  unread: boolean;
  pending: boolean;
  onRead(): void;
}) {
  if (!unread) return null;
  return (
    <Button loading={pending} onClick={onRead}>
      {pending ? "Đang đánh dấu…" : "Đánh dấu đã đọc"}
    </Button>
  );
}
