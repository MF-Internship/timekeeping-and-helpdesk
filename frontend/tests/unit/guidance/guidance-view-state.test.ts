import { describe, expect, it } from "vitest";

import { toGuidanceViewState } from "@/features/guidance/model/guidance-view-state";

const position = {
  latitude: 10,
  longitude: 106,
  accuracyM: 14,
  capturedAt: "2026-08-20T00:00:00Z",
};
const readyReference = { status: "ready" as const, data: { locations: [], maxAccuracyM: 25 } };

function state(overrides: Record<string, unknown> = {}) {
  return toGuidanceViewState({
    status: "ready",
    position,
    reference: readyReference,
    evaluation: { status: "evaluated", nearby: [], maxAccuracyM: 25 },
    isStale: false,
    hasResolved: true,
    ...overrides,
  });
}

describe("guidance view state", () => {
  it.each([
    [{ status: "idle", position: undefined, hasResolved: false }, "idle"],
    [{ status: "acquiring", position: undefined, hasResolved: false }, "requesting"],
    [{ status: "acquiring", position: undefined }, "refreshing"],
    [{ isStale: true }, "stale"],
    [{ position: { ...position, accuracyM: 26 } }, "weak"],
    [{ error: { kind: "TIMEOUT" }, position: undefined }, "unavailable"],
  ] as const)("maps %o to %s", (overrides, expected) => {
    expect(state(overrides).gpsState).toBe(expected);
  });

  it("keeps reference failure separate from device failure", () => {
    const result = state({ reference: { status: "unavailable" }, evaluation: undefined });
    expect(result.referenceUnavailable).toBe(true);
    expect(result.gpsState).toBe("ready");
  });
});
