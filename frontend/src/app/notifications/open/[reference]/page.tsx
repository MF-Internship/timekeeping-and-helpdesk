"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { IdentityRouteBoundary } from "@/features/identity/model/IdentityRouteBoundary";
import { resolveNotificationTarget } from "@/features/notifications/api/notification-api";
import { Button } from "@/shared/ui/button";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export default function NotificationOpenPage() {
  return (
    <IdentityRouteBoundary route="notifications">
      <SafeNotificationOpen />
    </IdentityRouteBoundary>
  );
}

function SafeNotificationOpen() {
  const params = useParams<{ reference: string }>();
  const router = useRouter();
  const reference = typeof params.reference === "string" ? params.reference : "";
  const invalid = !UUID.test(reference);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    if (invalid) return;
    void resolveNotificationTarget(reference)
      .then((target) => {
        if (!active) return;
        router.replace(
          target.destination === "TASK" ? `/tasks?focus=${target.target_id}` : "/attendance",
        );
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
    };
  }, [invalid, reference, router]);

  if (!invalid && !failed) return <p role="status">Đang kiểm tra quyền truy cập hiện tại…</p>;
  return (
    <section role="alert">
      <p>Không thể mở thông báo này. Liên kết có thể đã cũ hoặc bạn không còn quyền truy cập.</p>
      <Button onClick={() => router.replace("/notifications")}>Về hộp thư</Button>
    </section>
  );
}
