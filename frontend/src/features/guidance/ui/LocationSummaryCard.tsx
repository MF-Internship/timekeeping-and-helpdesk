import { Badge } from "@/shared/ui/badge";
import { Card } from "@/shared/ui/card";

import type { NearbyEntry } from "../model/position-types";
import { formatMetres } from "./format";
import styles from "./LocationSummaryCard.module.css";

export function LocationSummaryCard({
  location,
  overlapCount = 0,
}: {
  location?: NearbyEntry;
  overlapCount?: number;
}) {
  if (!location)
    return (
      <Card>
        <h2>Địa điểm gần bạn</h2>
        <p>Đọc GPS để xác định địa điểm gần nhất.</p>
      </Card>
    );
  const inside = location.status === "INSIDE_GEOFENCE";
  return (
    <Card aria-label="Địa điểm đang xem">
      <div className={styles.top}>
        <div>
          <p className={styles.eyebrow}>Địa điểm đang xem</p>
          <h2 id="location-summary-title">{location.name}</h2>
          <p>{location.code}</p>
        </div>
        <Badge tone={inside ? "ready" : "warning"} icon={inside ? "✓" : "!"}>
          {inside ? "Trong vùng" : "Ngoài vùng"}
        </Badge>
      </div>
      <p>{location.address}</p>
      <dl className={styles.metrics}>
        <div>
          <dt>Khoảng cách</dt>
          <dd>{formatMetres(location.distanceM)}</dd>
        </div>
        <div>
          <dt>Bán kính cho phép</dt>
          <dd>{formatMetres(location.radiusM)}</dd>
        </div>
        <div>
          <dt>Khoảng cách tới ranh giới</dt>
          <dd>{formatMetres(inside ? location.insideMarginM : location.distanceToBoundaryM)}</dd>
        </div>
      </dl>
      {overlapCount > 1 && (
        <Badge tone="neutral" icon="◎">
          Có {overlapCount} địa điểm chồng lấn
        </Badge>
      )}
      <p className={styles.advisory}>
        Chỉ thay đổi nội dung xem trước; không chọn địa điểm cho lần chấm công.
      </p>
    </Card>
  );
}
