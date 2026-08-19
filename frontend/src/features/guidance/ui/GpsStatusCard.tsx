import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { SectionHeading } from "@/shared/ui/section-heading";

import type { GpsViewState } from "../model/guidance-view-state";
import type { AcquisitionError, GuidancePosition } from "../model/position-types";
import { UI_MESSAGES } from "@/shared/messages";
import { formatClockTime, formatCoordinate, formatMetres } from "./format";
import { GpsAccuracyIndicator } from "./GpsAccuracyIndicator";
import styles from "./GpsStatusCard.module.css";

const LABEL: Record<GpsViewState, string> = {
  idle: "Chưa đọc GPS",
  requesting: "Đang yêu cầu vị trí",
  refreshing: "Đang làm mới GPS",
  ready: "GPS đạt yêu cầu",
  weak: "GPS chưa đủ chính xác",
  stale: "Bản xem trước đã cũ",
  unavailable: "Không lấy được GPS",
};

const TEXT = UI_MESSAGES.guidance;

function FailureCopy({ error }: { error?: AcquisitionError }) {
  if (!error) return null;
  const failure = TEXT.failure[error.kind];
  return (
    <>
      <h3>{TEXT.failureHeading}</h3>
      <p>{failure.title}</p>
      <p>{failure.remedy}</p>
      <p>{TEXT.failureNoPosition}</p>
      <p>{TEXT.failureDeviceOnly}</p>
    </>
  );
}

function AccuracyCopy({
  position,
  thresholdM,
}: {
  position?: GuidancePosition;
  thresholdM?: number;
}) {
  if (!position) return null;
  const sufficient = thresholdM !== undefined ? position.accuracyM <= thresholdM : undefined;
  return (
    <>
      <p>
        {TEXT.accuracyLabel}: <strong>{formatMetres(position.accuracyM)}</strong>
      </p>
      {thresholdM !== undefined && (
        <p>
          {TEXT.accuracyThresholdLabel}: {formatMetres(thresholdM)}
        </p>
      )}
      {sufficient !== undefined && (
        <>
          <p>{sufficient ? TEXT.accuracySufficient : TEXT.accuracyInsufficient}</p>
          <p>{TEXT.accuracyIndependent}</p>
        </>
      )}
    </>
  );
}

function FreshnessCopy({ state, position }: { state: GpsViewState; position?: GuidancePosition }) {
  if (!position) return null;
  return state === "stale" ? (
    <>
      <p>{TEXT.stale}</p>
      <p>{TEXT.punchTakesNewReading}</p>
    </>
  ) : (
    <p>{TEXT.fresh}</p>
  );
}

function GpsDetails({
  state,
  position,
  ageSeconds,
}: {
  state: GpsViewState;
  position?: GuidancePosition;
  ageSeconds?: number;
}) {
  if (!position) return null;
  return (
    <details>
      <summary>Chi tiết GPS</summary>
      <p>
        {TEXT.latitudeLabel}: {formatCoordinate(position.latitude)} — {TEXT.longitudeLabel}:{" "}
        {formatCoordinate(position.longitude)}
      </p>
      <p>
        {TEXT.capturedAtLabel}: {formatClockTime(position.capturedAt)}
      </p>
      <p>
        {TEXT.ageLabel}: {Math.floor(ageSeconds ?? 0)} {TEXT.secondsUnit}
      </p>
      {state === "weak" && (
        <>
          <h3>{TEXT.remediationHeading}</h3>
          <ul>
            {TEXT.remediation.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ul>
          <p>{TEXT.remediationNote}</p>
        </>
      )}
      <p>{TEXT.advisoryLabel}</p>
    </details>
  );
}

export function GpsStatusCard({
  state,
  position,
  error,
  thresholdM,
  ageSeconds,
  onRefresh,
}: {
  state: GpsViewState;
  position?: GuidancePosition;
  error?: AcquisitionError;
  thresholdM?: number;
  ageSeconds?: number;
  onRefresh(): void;
}) {
  const busy = state === "requesting" || state === "refreshing";
  const actionLabel = state === "idle" ? TEXT.trigger : TEXT.refresh;
  return (
    <Card aria-label={TEXT.positionHeading} aria-busy={busy || undefined} className={styles.card}>
      <SectionHeading
        title="Trạng thái GPS"
        level={2}
        action={
          <Button variant="quiet" disabled={busy} onClick={onRefresh} aria-label={actionLabel}>
            {actionLabel}
          </Button>
        }
      />
      <div className={styles.body} role="status" aria-label="Trạng thái GPS" aria-live="polite">
        <GpsAccuracyIndicator accuracyM={position?.accuracyM} state={state} />
        <div>
          <p className={styles.label}>{LABEL[state]}</p>
          <FailureCopy error={error} />
          <AccuracyCopy position={position} thresholdM={thresholdM} />
          <FreshnessCopy state={state} position={position} />
        </div>
      </div>
      <GpsDetails state={state} position={position} ageSeconds={ageSeconds} />
    </Card>
  );
}
