"use client";

import { useJobHealth } from "../model/job-health-state";
import { Button } from "@/shared/ui/button";
import { StatusBadge } from "@/shared/ui/status-badge";
import styles from "./JobHealthPanel.module.css";

export function JobHealthPanel() {
  const { data, error, refreshing, refresh } = useJobHealth();
  if (!data && refreshing) return <p role="status">Đang tải trạng thái đối soát…</p>;
  if (!data && error) return <p role="alert">Không thể tải trạng thái đối soát.</p>;
  if (!data) return null;
  return <HealthSnapshot data={data} error={error} refreshing={refreshing} refresh={refresh} />;
}

function HealthSnapshot({ data, error, refreshing, refresh }: ReturnType<typeof useJobHealth>) {
  if (!data) return null;
  return (
    <section className={styles.surface} aria-label="Trạng thái đối soát Check Out">
      <div className={styles.header}>
        <div>
          <StatusBadge tone={data.state === "ok" ? "ready" : "critical"}>{data.state}</StatusBadge>
          <p>Làm mới lúc {new Date(data.refreshed_at).toLocaleString("vi-VN")}</p>
        </div>
        <Button type="button" disabled={refreshing} onClick={() => void refresh()}>
          {refreshing ? "Đang làm mới…" : "Làm mới"}
        </Button>
      </div>
      <div className={styles.metrics}>
        <div className={styles.metric}>
          <span>Phiên quá hạn</span>
          <strong>{data.overdue_open_session_count}</strong>
        </div>
        <div className={styles.metric}>
          <span>Đã đóng tự động</span>
          <strong>{data.evidence_counts.job_closed_session_count}</strong>
        </div>
        <div className={styles.metric}>
          <span>Thiếu Check Out</span>
          <strong>{data.evidence_counts.missing_checkout_anomaly_count}</strong>
        </div>
      </div>
      {data.investigation_links?.accounts ? (
        <a href={data.investigation_links.accounts}>Điều tra tài khoản</a>
      ) : null}
      {data.escalation_guidance ? (
        <p className={styles.notice}>{data.escalation_guidance}</p>
      ) : null}
      {error ? (
        <p className={styles.notice} role="alert">
          Lần làm mới gần nhất thất bại; đang hiển thị dữ liệu cũ.
        </p>
      ) : null}
    </section>
  );
}
