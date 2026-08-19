"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

import type { GuidancePosition, NearbyEntry } from "../model/position-types";
import styles from "./LocationDiagnostics.module.css";

const LazySpatialDiagram = dynamic(
  () => import("./SpatialDiagram").then((module) => module.SpatialDiagram),
  { loading: () => <p role="status">Đang chuẩn bị sơ đồ…</p> },
);

export function SpatialPanel({
  position,
  entries,
  focused,
  onFocus,
  busy,
}: {
  position?: GuidancePosition;
  entries: readonly NearbyEntry[];
  focused?: NearbyEntry;
  onFocus(code: string): void;
  busy: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <details className={styles.details} onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary>Sơ đồ vị trí tương đối</summary>
      <div>
        <p>
          Sơ đồ hỗ trợ trực quan. Tên, địa chỉ, khoảng cách và trạng thái đầy đủ luôn có trong danh
          sách.
        </p>
        {open && (
          <LazySpatialDiagram
            position={position}
            entries={entries}
            focused={focused}
            onFocus={onFocus}
            busy={busy}
          />
        )}
      </div>
    </details>
  );
}
