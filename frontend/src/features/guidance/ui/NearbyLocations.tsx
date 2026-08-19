"use client";

import { useState } from "react";

import { Button } from "@/shared/ui/button";
import { Card } from "@/shared/ui/card";
import { EmptyState } from "@/shared/ui/async-state";

import type { NearbyEntry } from "../model/position-types";
import { NearbyLocationItem } from "./NearbyLocationItem";
import { UI_MESSAGES } from "@/shared/messages";
import styles from "./NearbyLocations.module.css";

const DEFAULT_ROWS = 3;

function verdictFor(insideCount: number) {
  if (insideCount === 0) return UI_MESSAGES.guidance.outsideAll;
  if (insideCount === 1) return UI_MESSAGES.guidance.insideOne;
  return UI_MESSAGES.guidance.insideMany;
}

function collapsedEntries(entries: readonly NearbyEntry[]) {
  const containing = entries.filter((entry) => entry.status === "INSIDE_GEOFENCE");
  const outside = entries.filter((entry) => entry.status === "OUTSIDE_GEOFENCE");
  const selected = new Set([
    ...containing.map((entry) => entry.code),
    ...outside.slice(0, Math.max(DEFAULT_ROWS - containing.length, 0)).map((entry) => entry.code),
  ]);
  return entries.filter((entry) => selected.has(entry.code));
}

function NearbyVerdict({ insideCount }: { insideCount: number }) {
  return (
    <div role="status">
      <p>{verdictFor(insideCount)}</p>
      {insideCount > 1 && <p>{UI_MESSAGES.guidance.insideManyNote}</p>}
    </div>
  );
}

function ListControls({
  expanded,
  hiddenCount,
  collapsedCount,
  onExpand,
  onCollapse,
}: {
  expanded: boolean;
  hiddenCount: number;
  collapsedCount: number;
  onExpand(): void;
  onCollapse(): void;
}) {
  return (
    <>
      {hiddenCount > 0 && (
        <Button variant="quiet" onClick={onExpand} aria-expanded={expanded}>
          Xem thêm {hiddenCount} địa điểm
        </Button>
      )}
      {expanded && collapsedCount > 0 && (
        <Button variant="quiet" onClick={onCollapse}>
          Thu gọn
        </Button>
      )}
    </>
  );
}

export function NearbyLocations({
  entries,
  focusedCode,
  onFocus,
}: {
  entries: readonly NearbyEntry[];
  focusedCode?: string;
  onFocus(code: string): void;
}) {
  const [expanded, setExpanded] = useState(false);
  if (entries.length === 0)
    return (
      <Card aria-label={UI_MESSAGES.guidance.nearbyHeading}>
        <h2>{UI_MESSAGES.guidance.nearbyHeading}</h2>
        <EmptyState message={UI_MESSAGES.guidance.noActiveLocations} />
      </Card>
    );
  const visible = expanded ? entries : collapsedEntries(entries);
  const insideCount = entries.filter((entry) => entry.status === "INSIDE_GEOFENCE").length;
  const collapsedCount = entries.length - collapsedEntries(entries).length;
  return (
    <Card aria-label={UI_MESSAGES.guidance.nearbyHeading}>
      <h2>{UI_MESSAGES.guidance.nearbyHeading}</h2>
      <NearbyVerdict insideCount={insideCount} />
      <fieldset className={styles.choices}>
        <legend>{UI_MESSAGES.guidance.targetChooser}</legend>
        <ul className={styles.list}>
          {visible.map((entry) => (
            <NearbyLocationItem
              key={entry.code}
              entry={entry}
              nearest={entry.code === entries[0]?.code}
              focused={entry.code === focusedCode}
              onFocus={onFocus}
            />
          ))}
        </ul>
      </fieldset>
      <p>{UI_MESSAGES.guidance.estimateNote}</p>
      <ListControls
        expanded={expanded}
        hiddenCount={entries.length - visible.length}
        collapsedCount={collapsedCount}
        onExpand={() => setExpanded(true)}
        onCollapse={() => setExpanded(false)}
      />
    </Card>
  );
}
