import type { GpsViewState } from "../model/guidance-view-state";
import { formatMetres } from "./format";
import styles from "./GpsAccuracyIndicator.module.css";

const ICON: Record<GpsViewState, string> = {
  idle: "○",
  requesting: "…",
  refreshing: "↻",
  ready: "✓",
  weak: "!",
  stale: "◷",
  unavailable: "×",
};

export function GpsAccuracyIndicator({
  accuracyM,
  state,
}: {
  accuracyM?: number;
  state: GpsViewState;
}) {
  return (
    <div className={`${styles.indicator} ${styles[state]}`} aria-hidden="true">
      <span>{accuracyM === undefined ? "—" : formatMetres(accuracyM)}</span>
      <b>{ICON[state]}</b>
    </div>
  );
}
