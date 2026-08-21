import type { GpsViewState } from "../model/guidance-view-state";
import { formatMetres } from "./format";
import styles from "./GpsAccuracyIndicator.module.css";
import { Check, Clock3, LoaderCircle, LocateFixed, TriangleAlert, WifiOff } from "lucide-react";

const ICON = {
  idle: LocateFixed,
  requesting: LoaderCircle,
  refreshing: LoaderCircle,
  ready: Check,
  weak: TriangleAlert,
  stale: Clock3,
  unavailable: WifiOff,
};

export function GpsAccuracyIndicator({
  accuracyM,
  state,
}: {
  accuracyM?: number;
  state: GpsViewState;
}) {
  const Icon = ICON[state];
  const label =
    accuracyM === undefined ? "Chưa có sai số GPS" : `Sai số ${formatMetres(accuracyM)}`;
  return (
    <div className={`${styles.indicator} ${styles[state]}`} aria-label={label}>
      <Icon className={styles.icon} aria-hidden="true" />
      <span>{accuracyM === undefined ? "—" : formatMetres(accuracyM)}</span>
      <small>{accuracyM === undefined ? "GPS" : "sai số"}</small>
    </div>
  );
}
