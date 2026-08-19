import { UI_MESSAGES } from "@/shared/messages";

import type { GuidanceLocation } from "../model/nearby";
import { formatMetres } from "./format";

const TEXT = UI_MESSAGES.guidance;

export function LocationReference({ locations }: { locations: readonly GuidanceLocation[] }) {
  if (locations.length === 0) return <p>{TEXT.noActiveLocations}</p>;
  return (
    <section aria-label={TEXT.referenceHeading}>
      <h3>{TEXT.referenceHeading}</h3>
      <ul className="record-list">
        {locations.map((location) => (
          <li key={location.code}>
            <p>
              <strong>{location.code}</strong> — {location.name}
            </p>
            <p>{location.address}</p>
            <p>
              {TEXT.radiusLabel}: {formatMetres(Number(location.radius_m))}
            </p>
          </li>
        ))}
      </ul>
      <p>{TEXT.referenceIndependent}</p>
    </section>
  );
}
