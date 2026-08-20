"use client";

import { useJobHealth } from "../model/job-health-state";
import { Button } from "@/shared/ui/button";

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
    <section aria-label="Trạng thái đối soát Check Out">
      <p>Trạng thái: {data.state}</p>
      <p>Làm mới lúc: {new Date(data.refreshed_at).toLocaleString("vi-VN")}</p>
      <p>Phiên quá hạn: {data.overdue_open_session_count}</p>
      <p>Đã đóng bởi job: {data.evidence_counts.job_closed_session_count}</p>
      <p>Anomaly thiếu Check Out: {data.evidence_counts.missing_checkout_anomaly_count}</p>
      {data.investigation_links?.accounts ? (
        <a href={data.investigation_links.accounts}>Điều tra tài khoản</a>
      ) : null}
      {data.escalation_guidance ? <p>{data.escalation_guidance}</p> : null}
      {error ? <p role="alert">Lần làm mới gần nhất thất bại; đang hiển thị dữ liệu cũ.</p> : null}
      <Button type="button" disabled={refreshing} onClick={() => void refresh()}>
        {refreshing ? "Đang làm mới…" : "Làm mới"}
      </Button>
    </section>
  );
}
