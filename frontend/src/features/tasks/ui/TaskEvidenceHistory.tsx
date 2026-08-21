"use client";

import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { googleMapsSearchUrl } from "@/shared/formatters/maps";
import { Camera, Clock3, MapPin } from "lucide-react";

import { accessTaskPhoto, type TaskDetail } from "../api/task-api";
import { TaskFailureNotice } from "./TaskFailureNotice";
import styles from "./TaskManagement.module.css";

export function TaskEvidenceHistory({ detail, error }: { detail?: TaskDetail; error?: unknown }) {
  if (error) return <TaskFailureNotice error={error} />;
  if (!detail) return null;
  return (
    <Card className={styles.history} aria-label={`Lịch sử ${detail.title}`}>
      <div className={styles.historyHeading}>
        <div>
          <span>Lịch sử cập nhật</span>
          <h2>{detail.title}</h2>
        </div>
        <span className={styles.updateCount}>
          <Clock3 aria-hidden="true" size={17} /> {detail.updates.length} cập nhật
        </span>
      </div>
      {detail.updates.length === 0 ? (
        <p>Chưa có cập nhật trạng thái.</p>
      ) : (
        <ol className={styles.timeline}>
          {detail.updates.map((update) => (
            <HistoryUpdate key={update.id} taskId={detail.id} update={update} />
          ))}
        </ol>
      )}
    </Card>
  );
}

function HistoryUpdate({
  taskId,
  update,
}: {
  taskId: number;
  update: TaskDetail["updates"][number];
}) {
  const note = update.note ?? update.block_reason ?? update.completion_note;
  const mapsUrl = evidenceMapsUrl(update);
  return (
    <li>
      <span className={styles.timelineDot} aria-hidden="true" />
      <div className={styles.updateHeading}>
        <strong>{statusLabel(update.status)}</strong>
        <time dateTime={update.recorded_at}>
          {new Date(update.recorded_at).toLocaleString("vi-VN")}
        </time>
      </div>
      <p className={styles.actor}>Cập nhật bởi {update.actor.full_name}</p>
      {note ? <p className={styles.updateNote}>{note}</p> : null}
      <EvidenceLocation update={update} mapsUrl={mapsUrl} />
      <EvidencePhotos taskId={taskId} photos={update.photos} />
    </li>
  );
}

function EvidenceLocation({
  update,
  mapsUrl,
}: {
  update: TaskDetail["updates"][number];
  mapsUrl?: string;
}) {
  if (!update.captured_latitude || !update.captured_longitude) return null;
  return (
    <div className={styles.evidenceMeta}>
      <MapPin aria-hidden="true" size={16} />
      <span>
        GPS: {update.captured_latitude}, {update.captured_longitude}
      </span>
      <span>Sai số: {update.accuracy_m} m</span>
      <span>Chất lượng: {update.gps_quality ?? "Chưa phân loại"}</span>
      <span>Đối chiếu: {evidenceLocationLabel(update)}</span>
      {mapsUrl ? (
        <a href={mapsUrl} target="_blank" rel="noopener noreferrer">
          Mở vị trí trên Google Maps
        </a>
      ) : null}
    </div>
  );
}

function EvidencePhotos({
  taskId,
  photos,
}: {
  taskId: number;
  photos: TaskDetail["updates"][number]["photos"];
}) {
  if (!photos?.length) return null;
  return (
    <div className={styles.photoActions}>
      <Camera aria-hidden="true" size={17} />
      {photos.map((photo, index) => (
        <Button key={photo.id} variant="quiet" onClick={() => void openPhoto(taskId, photo.id)}>
          Xem ảnh {index + 1}
        </Button>
      ))}
    </div>
  );
}

function statusLabel(status: string) {
  return (
    {
      TODO: "Cần làm",
      IN_PROGRESS: "Đang thực hiện",
      BLOCKED: "Bị chặn",
      COMPLETED: "Đã hoàn thành",
    }[status] ?? status
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
