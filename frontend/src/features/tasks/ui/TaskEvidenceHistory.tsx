"use client";

import { Button } from "@/shared/ui/button";
import { googleMapsSearchUrl } from "@/shared/formatters/maps";

import { accessTaskPhoto, type TaskDetail } from "../api/task-api";
import { TaskFailureNotice } from "./TaskFailureNotice";
import styles from "./TaskManagement.module.css";

export function TaskEvidenceHistory({ detail, error }: { detail?: TaskDetail; error?: unknown }) {
  if (error) return <TaskFailureNotice error={error} />;
  if (!detail) return null;
  return (
    <section aria-label={`Lịch sử ${detail.title}`}>
      <h2>Lịch sử — {detail.title}</h2>
      {detail.updates.length === 0 ? (
        <p>Chưa có cập nhật trạng thái.</p>
      ) : (
        <ol>
          {detail.updates.map((update) => (
            <li key={update.id}>
              <div>
                <strong>{update.status}</strong> — {update.actor.full_name} —{" "}
                <time dateTime={update.recorded_at}>
                  {new Date(update.recorded_at).toLocaleString("vi-VN")}
                </time>
              </div>
              {update.captured_latitude && update.captured_longitude ? (
                <div className={styles.evidenceMeta}>
                  <span>
                    GPS: {update.captured_latitude}, {update.captured_longitude}
                  </span>
                  <span>Sai số: {update.accuracy_m} m</span>
                  <span>Chất lượng: {update.gps_quality ?? "Chưa phân loại"}</span>
                  <span>Đối chiếu: {evidenceLocationLabel(update)}</span>
                  {evidenceMapsUrl(update) ? (
                    <a href={evidenceMapsUrl(update)} target="_blank" rel="noopener noreferrer">
                      Mở vị trí trên Google Maps
                    </a>
                  ) : null}
                </div>
              ) : null}
              {update.photos?.length ? (
                <div className={styles.photoActions}>
                  {update.photos.map((photo, index) => (
                    <Button
                      key={photo.id}
                      variant="quiet"
                      onClick={() => void openPhoto(detail.id, photo.id)}
                    >
                      Xem ảnh {index + 1}
                    </Button>
                  ))}
                </div>
              ) : null}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

async function openPhoto(taskId: number, photoId: number) {
  const result = await accessTaskPhoto(taskId, photoId);
  window.open(result.url, "_blank", "noopener,noreferrer");
}

function resolutionLabel(method: string | null) {
  const labels: Record<string, string> = {
    AUTO_SINGLE: "Tự động khớp một địa điểm",
    USER_SELECTED: "Người dùng chọn trong vùng chồng lấn",
    GPS_ONLY: "Chỉ ghi nhận GPS",
  };
  return method ? (labels[method] ?? method) : "Chưa đối chiếu";
}

function evidenceLocationLabel(update: TaskDetail["updates"][number]) {
  if (update.resolved_address) {
    return `${update.resolved_address} (${resolutionLabel(update.resolution_method)})`;
  }
  if (update.actual_location) {
    return `${update.actual_location.name} — ${update.actual_location.address} (${resolutionLabel(update.resolution_method)})`;
  }
  if (update.gps_quality === "GOOD") return "Ngoài mọi địa điểm đã đăng ký";
  return "GPS sai số cao, chưa xác nhận địa chỉ";
}

function evidenceMapsUrl(update: TaskDetail["updates"][number]) {
  if (update.maps_url) return update.maps_url;
  if (!update.captured_latitude || !update.captured_longitude) return undefined;
  return googleMapsSearchUrl(update.captured_latitude, update.captured_longitude);
}
