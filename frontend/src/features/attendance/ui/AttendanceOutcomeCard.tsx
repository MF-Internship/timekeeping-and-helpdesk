import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";

import type { AttendanceOutcome } from "../model/use-attendance-experience";

export function AttendanceOutcomeCard({
  outcome,
  onRetry,
}: {
  outcome?: AttendanceOutcome;
  onRetry(): void;
}) {
  if (!outcome) return null;
  if (outcome.kind === "success")
    return (
      <Card role="status">
        <Badge tone="ready" icon="✓">
          {outcome.action} thành công
        </Badge>
        <p>{outcome.message}</p>
      </Card>
    );
  return (
    <Card role="alert">
      <Badge tone="critical" icon="!">
        Máy chủ từ chối
      </Badge>
      <p>{outcome.message}</p>
      <p>Đây là kết quả chính thức từ máy chủ. Bản xem trước GPS chỉ để tham khảo.</p>
      <Button onClick={onRetry}>Thử lại với GPS mới</Button>
    </Card>
  );
}
