import type { GuidancePosition, NearbyEntry } from "../model/position-types";
import { formatClockTime, formatCoordinate, formatMetres } from "./format";
import styles from "./LocationDiagnostics.module.css";

export function LocationDiagnostics({
  position,
  focused,
}: {
  position?: GuidancePosition;
  focused?: NearbyEntry;
}) {
  if (!position) return null;
  return (
    <details className={styles.details}>
      <summary>Chi tiết kỹ thuật và xử lý sự cố</summary>
      <div>
        <p>Vĩ độ: {formatCoordinate(position.latitude)}</p>
        <p>Kinh độ: {formatCoordinate(position.longitude)}</p>
        <p>Thời điểm đọc: {formatClockTime(position.capturedAt)}</p>
        {focused && (
          <>
            <p>Khoảng cách chính xác: {formatMetres(focused.distanceM)}</p>
            <p>Bán kính cấu hình: {formatMetres(focused.radiusM)}</p>
          </>
        )}
        <h3>Cải thiện tín hiệu</h3>
        <ul>
          <li>Bật quyền vị trí chính xác.</li>
          <li>Di chuyển ra khu vực thoáng.</li>
          <li>Chờ một lát rồi làm mới GPS.</li>
        </ul>
      </div>
    </details>
  );
}
