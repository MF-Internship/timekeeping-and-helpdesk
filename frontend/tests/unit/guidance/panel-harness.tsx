import { act, fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { GuidancePanel } from "@/features/guidance/ui/GuidancePanel";
import { getConfig, listLocations } from "@/features/locations/api/location-api";

/**
 * Shared scaffolding for the guidance panel scenarios. The geolocation provider
 * is stubbed rather than the model, so every scenario exercises the real
 * acquisition, ranking, and rendering path end to end.
 */

export const CAPTURED_AT = Date.UTC(2026, 7, 19, 3, 0, 0);
export const METRES_PER_DEGREE_LATITUDE = 111194.93;
export const POSITION = { latitude: 10, longitude: 106 };

/** `max_attendance_accuracy_m` as the singleton configuration reports it. */
export const MAX_ACCURACY_M = 100;

export const CONFIG = {
  max_attendance_accuracy_m: "100.000",
  default_radius_m: "50.000",
  max_radius_m: "70.000",
};

export type Sample = {
  /** Metres due north of {@link POSITION}. */
  northM: number;
  accuracyM: number;
  timestamp: number;
};

export const GOOD_SAMPLE: Sample = { northM: 0, accuracyM: 12, timestamp: CAPTURED_AT };

export function directoryRow(code: string, northM: number, radiusM = "50.000") {
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

export type Point = { latitude: number; longitude: number };

/**
 * A directory row at explicit coordinates, so a scenario can be built from the
 * real seeded Location geometry rather than from an offset of {@link POSITION}.
 */
export function locationRow(
  code: string,
  point: Point,
  options: { radiusM?: string; name?: string; address?: string } = {},
) {
  return {
    id: code.length,
    code,
    name: options.name ?? `Điểm ${code}`,
    address: options.address ?? `Địa chỉ ${code}`,
    latitude: point.latitude.toFixed(15),
    longitude: point.longitude.toFixed(15),
    radius_m: options.radiusM ?? "50.000",
    is_active: true,
    kind: "SHOP",
  };
}

/** A provider that always resolves at an explicit point. */
export function mockGeolocationAt(point: Point, accuracyM = GOOD_SAMPLE.accuracyM) {
  const geolocation = {
    watchPosition: vi.fn((success: PositionCallback) => {
      success({
        coords: { latitude: point.latitude, longitude: point.longitude, accuracy: accuracyM },
        timestamp: CAPTURED_AT,
      } as GeolocationPosition);
      return 1;
    }),
    clearWatch: vi.fn(),
  };
  installGeolocation(geolocation);
  return geolocation;
}

function asGeolocationPosition(sample: Sample): GeolocationPosition {
  return {
    coords: {
      latitude: POSITION.latitude + sample.northM / METRES_PER_DEGREE_LATITUDE,
      longitude: POSITION.longitude,
      accuracy: sample.accuracyM,
    },
    timestamp: sample.timestamp,
  } as GeolocationPosition;
}

export function mockGeolocation(initial: Sample = GOOD_SAMPLE) {
  let sample = initial;
  const geolocation = {
    watchPosition: vi.fn((success: PositionCallback) => {
      success(asGeolocationPosition(sample));
      return 1;
    }),
    clearWatch: vi.fn(),
  };
  Object.defineProperty(navigator, "geolocation", { value: geolocation, configurable: true });
  Object.defineProperty(navigator, "permissions", { value: undefined, configurable: true });
  return {
    geolocation,
    /** The sample the next acquisition will resolve with. */
    nextSample(next: Sample) {
      sample = next;
    },
  };
}

/** Installs an arbitrary `navigator.geolocation` — including none at all. */
export function installGeolocation(value: unknown) {
  Object.defineProperty(navigator, "geolocation", { value, configurable: true });
  Object.defineProperty(navigator, "permissions", { value: undefined, configurable: true });
}

/** A provider whose every acquisition fails with the given W3C error code. */
export function mockGeolocationFailure(code: number) {
  const geolocation = {
    watchPosition: vi.fn((_success: PositionCallback, failure?: PositionErrorCallback) => {
      failure?.({ code } as GeolocationPositionError);
      return 1;
    }),
    clearWatch: vi.fn(),
  };
  installGeolocation(geolocation);
  return geolocation;
}

/** A provider that never calls back, so only the watchdog can settle the request. */
export function mockGeolocationSilent() {
  const geolocation = { watchPosition: vi.fn(() => 1), clearWatch: vi.fn() };
  installGeolocation(geolocation);
  return geolocation;
}

export function mockReference(rows: ReturnType<typeof directoryRow>[], config = CONFIG) {
  vi.mocked(listLocations).mockResolvedValue(
    rows as unknown as Awaited<ReturnType<typeof listLocations>>,
  );
  vi.mocked(getConfig).mockResolvedValue(
    config as unknown as Awaited<ReturnType<typeof getConfig>>,
  );
}

/** Drains pending microtasks without letting real wall-clock time leak in. */
export async function settle() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
}

export async function advance(milliseconds: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(milliseconds);
  });
}

/** Mounts the panel and presses the explicit trigger — nothing runs on mount. */
export async function renderPanel() {
  render(<GuidancePanel />);
  fireEvent.click(screen.getByRole("button", { name: "Xem vị trí" }));
  await settle();
}

export function refreshButton(): HTMLElement {
  return screen.getByRole("button", { name: "Làm mới vị trí" });
}

export async function pressRefresh() {
  fireEvent.click(refreshButton());
  await settle();
}

export function positionRegion(): HTMLElement {
  return screen.getByRole("region", { name: "Vị trí thiết bị" });
}

export function nearbyRegion(): HTMLElement {
  return screen.getByRole("region", { name: "Địa điểm gần bạn" });
}
