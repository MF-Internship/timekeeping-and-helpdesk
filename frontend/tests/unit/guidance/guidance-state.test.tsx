import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getConfig, listLocations } from "@/features/locations/api/location-api";
import { STALE_AFTER_SECONDS, useGuidance } from "@/features/guidance/model/guidance-state";

vi.mock("@/features/locations/api/location-api", () => ({
  listLocations: vi.fn(),
  getConfig: vi.fn(),
}));

const CAPTURED_AT = Date.UTC(2026, 7, 19, 3, 0, 0);
const POSITION = { latitude: 10, longitude: 106 };
const METRES_PER_DEGREE_LATITUDE = 111194.93;

function directoryRow(code: string, northM: number, radiusM = "50.000") {
  return {
    id: code.length,
    code,
    name: `Điểm ${code}`,
    address: `Địa chỉ ${code}`,
    latitude: (POSITION.latitude + northM / METRES_PER_DEGREE_LATITUDE).toFixed(15),
    longitude: POSITION.longitude.toFixed(15),
    radius_m: radiusM,
    is_active: true,
    kind: "SHOP",
  };
}

const CONFIG = {
  max_attendance_accuracy_m: "100.000",
  default_radius_m: "50.000",
  max_radius_m: "70.000",
};

function mockGeolocation() {
  const geolocation = {
    watchPosition: vi.fn((success: PositionCallback) => {
      success({
        coords: { latitude: POSITION.latitude, longitude: POSITION.longitude, accuracy: 12 },
        timestamp: CAPTURED_AT,
      } as GeolocationPosition);
      return 1;
    }),
    clearWatch: vi.fn(),
  };
  Object.defineProperty(navigator, "geolocation", { value: geolocation, configurable: true });
  return geolocation;
}

/** Drains the pending microtasks without letting the mocked clock drift. */
async function settle() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
}

async function startGuidance() {
  const view = renderHook(() => useGuidance());
  await act(async () => {
    view.result.current.start();
  });
  await settle();
  return view;
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(CAPTURED_AT);
  mockGeolocation();
  Object.defineProperty(navigator, "permissions", { value: undefined, configurable: true });
  vi.mocked(listLocations).mockResolvedValue([
    directoryRow("FAR", 900),
    directoryRow("NEAR", 10),
  ] as unknown as Awaited<ReturnType<typeof listLocations>>);
  vi.mocked(getConfig).mockResolvedValue(
    CONFIG as unknown as Awaited<ReturnType<typeof getConfig>>,
  );
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("useGuidance composition", () => {
  it("composes the acquired position, the directory and the config", async () => {
    const { result } = await startGuidance();

    expect(result.current.evaluation?.status).toBe("evaluated");

    expect(result.current.position?.accuracyM).toBe(12);
    expect(result.current.reference.status).toBe("ready");
    const evaluation = result.current.evaluation;
    if (evaluation?.status !== "evaluated") throw new Error("expected an evaluated result");
    expect(evaluation.maxAccuracyM).toBe(100);
    expect(evaluation.nearby.map((entry) => entry.code)).toEqual(["NEAR", "FAR"]);
    expect(evaluation.nearby[0].status).toBe("INSIDE_GEOFENCE");
  });

  it("requests only the active Locations", async () => {
    await startGuidance();

    expect(listLocations).toHaveBeenCalledWith({ is_active: true });
  });

  it("focuses the nearest entry until another is chosen", async () => {
    const { result } = await startGuidance();

    expect(result.current.focused?.code).toBe("NEAR");

    act(() => result.current.focus("FAR"));
    expect(result.current.focused?.code).toBe("FAR");
    expect(result.current.evaluation?.status).toBe("evaluated");
  });
});

describe("useGuidance reference data", () => {
  it.each([
    ["directory", () => vi.mocked(listLocations).mockRejectedValue(new Error("boom"))],
    ["config", () => vi.mocked(getConfig).mockRejectedValue(new Error("boom"))],
  ])("reports an unevaluated result when the %s cannot be read", async (_label, fail) => {
    fail();

    const { result } = await startGuidance();

    expect(result.current.reference.status).toBe("unavailable");
    expect(result.current.evaluation).toEqual({
      status: "unevaluated",
      reason: "REFERENCE_DATA_UNAVAILABLE",
    });
  });

  it("keeps the position readout and substitutes no defaulted values", async () => {
    vi.mocked(getConfig).mockRejectedValue(new Error("boom"));

    const { result } = await startGuidance();

    expect(result.current.evaluation?.status).toBe("unevaluated");
    expect(result.current.position).toEqual({
      latitude: POSITION.latitude,
      longitude: POSITION.longitude,
      accuracyM: 12,
      capturedAt: new Date(CAPTURED_AT).toISOString(),
    });
    expect(result.current.evaluation).not.toHaveProperty("maxAccuracyM");
    expect(result.current.evaluation).not.toHaveProperty("nearby");
    expect(JSON.stringify(result.current.evaluation)).not.toContain("50");
  });
});

describe("useGuidance freshness", () => {
  it("starts at age zero and is not stale", async () => {
    const { result } = await startGuidance();

    expect(result.current.position).toBeDefined();
    expect(result.current.ageSeconds).toBe(0);
    expect(result.current.isStale).toBe(false);
  });

  it("is not yet stale at exactly the threshold", async () => {
    const { result } = await startGuidance();
    expect(result.current.position).toBeDefined();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(STALE_AFTER_SECONDS * 1000);
    });

    expect(result.current.ageSeconds).toBe(STALE_AFTER_SECONDS);
    expect(result.current.isStale).toBe(false);
  });

  it("turns stale strictly above the threshold", async () => {
    const { result } = await startGuidance();
    expect(result.current.position).toBeDefined();

    await act(async () => {
      await vi.advanceTimersByTimeAsync((STALE_AFTER_SECONDS + 1) * 1000);
    });

    expect(result.current.ageSeconds).toBe(STALE_AFTER_SECONDS + 1);
    expect(result.current.isStale).toBe(true);
  });

  it("reports no age before any position is acquired", () => {
    const { result } = renderHook(() => useGuidance());

    expect(result.current.ageSeconds).toBeUndefined();
    expect(result.current.isStale).toBe(false);
  });
});
