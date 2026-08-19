"use client";

import type { ReactNode } from "react";

import { ErrorState, LoadingState } from "@/shared/ui/async-state";
import { Button } from "@/shared/ui/button";

import { useGuidance } from "../model/guidance-state";
import { toGuidanceViewState } from "../model/guidance-view-state";
import { GpsStatusCard } from "./GpsStatusCard";
import { GuidanceStateNotice } from "./GuidanceStateNotice";
import { LocationDiagnostics } from "./LocationDiagnostics";
import { LocationSummaryCard } from "./LocationSummaryCard";
import { NearbyLocations } from "./NearbyLocations";
import { SpatialPanel } from "./SpatialPanel";
import { LocationReference } from "./LocationReference";
import styles from "./GuidancePanel.module.css";

export type Guidance = ReturnType<typeof useGuidance>;

function GuidanceNotices({
  guidance,
  view,
}: {
  guidance: Guidance;
  view: ReturnType<typeof toGuidanceViewState>;
}) {
  return (
    <>
      {guidance.reference.status === "loading" && (
        <LoadingState message="Đang tải dữ liệu địa điểm…" />
      )}
      {view.error && (
        <GuidanceStateNotice error={view.error} onRetry={() => void guidance.refresh()} />
      )}
      {view.error && guidance.reference.status === "ready" && (
        <LocationReference locations={guidance.reference.data.locations} />
      )}
      {view.referenceUnavailable && (
        <ErrorState
          message="Không tải được danh mục địa điểm hoặc cấu hình; vị trí chưa được đối chiếu."
          onRetry={guidance.start}
        />
      )}
    </>
  );
}

function GuidanceLocations({
  guidance,
  view,
  busy,
}: {
  guidance: Guidance;
  view: ReturnType<typeof toGuidanceViewState>;
  busy: boolean;
}) {
  return (
    <>
      {view.position && (
        <NearbyLocations
          entries={view.nearby}
          focusedCode={view.focused?.code}
          onFocus={guidance.focus}
        />
      )}
      <SpatialPanel
        position={view.position}
        entries={view.nearby}
        focused={view.focused}
        onFocus={guidance.focus}
        busy={busy}
      />
      <LocationDiagnostics position={view.position} focused={view.focused} />
    </>
  );
}

export function GuidanceContent({
  guidance,
  context,
  primaryAction,
  outcome,
}: {
  guidance: Guidance;
  context?: ReactNode;
  primaryAction?: ReactNode;
  outcome?: ReactNode;
}) {
  const view = toGuidanceViewState(guidance);
  const busy = view.gpsState === "requesting" || view.gpsState === "refreshing";
  return (
    <div className={styles.stack}>
      <LocationSummaryCard location={view.focused} overlapCount={view.overlapCount} />
      {context}
      <GpsStatusCard
        state={view.gpsState}
        position={view.position}
        error={view.error}
        thresholdM={view.thresholdM}
        ageSeconds={view.ageSeconds}
        onRefresh={() => void (view.gpsState === "idle" ? guidance.start() : guidance.refresh())}
      />
      {primaryAction}
      {outcome}
      <GuidanceNotices guidance={guidance} view={view} />
      <GuidanceLocations guidance={guidance} view={view} busy={busy} />
    </div>
  );
}

export function GuidancePanel() {
  const guidance = useGuidance();
  const started = guidance.status !== "idle" || guidance.reference.status !== "idle";
  if (!started)
    return (
      <Button variant="primary" onClick={guidance.start}>
        Xem vị trí
      </Button>
    );
  return <GuidanceContent guidance={guidance} />;
}
