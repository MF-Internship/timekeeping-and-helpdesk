import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";

import type { AcquisitionError } from "../model/position-types";

const COPY = {
  PERMISSION_DENIED: [
    "Quyền vị trí đã bị từ chối",
    "Mở cài đặt trình duyệt hoặc thiết bị, cho phép quyền vị trí rồi thử lại.",
  ],
  UNAVAILABLE: ["GPS không khả dụng", "Thiết bị hoặc trình duyệt hiện không thể cung cấp vị trí."],
  TIMEOUT: ["Quá thời gian lấy GPS", "Di chuyển ra nơi thoáng, chờ tín hiệu ổn định rồi thử lại."],
  UNKNOWN: ["Không lấy được GPS", "Đã xảy ra lỗi không xác định. Hãy thử lại."],
} as const;

export function GuidanceStateNotice({
  error,
  onRetry,
}: {
  error: AcquisitionError;
  onRetry(): void;
}) {
  const [title, message] = COPY[error.kind];
  return (
    <Card role="alert">
      <Badge tone="critical" icon="!">
        {title}
      </Badge>
      <p>{message}</p>
      <Button onClick={onRetry}>Thử lấy vị trí lại</Button>
    </Card>
  );
}
