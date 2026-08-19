import { Badge } from "@/shared/ui/badge";

import type { NearbyEntry } from "../model/position-types";
import { BoundaryReadout, DistanceReadout } from "./EntryReadouts";
import styles from "./NearbyLocations.module.css";

export function NearbyLocationItem({
  entry,
  nearest,
  focused,
  onFocus,
}: {
  entry: NearbyEntry;
  nearest: boolean;
  focused: boolean;
  onFocus(code: string): void;
}) {
  const inside = entry.status === "INSIDE_GEOFENCE";
  return (
    <li className={focused ? styles.focused : undefined}>
      <label className={styles.item}>
        <input
          type="radio"
          name="guidance-location"
          aria-label={`${entry.code} — ${entry.name}`}
          value={entry.code}
          checked={focused}
          onChange={() => onFocus(entry.code)}
        />
        <span className={styles.content}>
          <span className={styles.title}>
            <strong>
              {entry.code} — {entry.name}
            </strong>
            {nearest && <span>(Gần nhất)</span>}
          </span>
          <span>{entry.address}</span>
          <DistanceReadout entry={entry} />
          <BoundaryReadout entry={entry} />
          <span className={styles.badges}>
            <Badge tone={inside ? "ready" : "warning"} icon={inside ? "✓" : "!"}>
              {inside ? "Trong vùng" : "Ngoài vùng"}
            </Badge>
          </span>
        </span>
      </label>
    </li>
  );
}
