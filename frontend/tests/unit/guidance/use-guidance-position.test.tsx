import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ACQUISITION_TIMEOUT_MS,
  useGuidancePosition,
} from "@/features/guidance/model/use-guidance-position";

type Handlers = { success: PositionCallback; failure: PositionErrorCallback };

const CAPTURED_AT = Date.UTC(2026, 7, 19, 3, 0, 0);

function sample(overrides: Partial<GeolocationCoordinates> = {}): GeolocationPosition {
  return {
    coords: { latitude: 10.78585, longitude: 106.6926, accuracy: 12.5, ...overrides },
    timestamp: CAPTURED_AT,
  } as GeolocationPosition;
}

describe("useGuidancePosition", () => {
  const clearWatch = vi.fn();
  const watchPosition = vi.fn();
  let handlers: Handlers[] = [];
  let nextWatchId = 0;

  beforeEach(() => {
    handlers = [];
    nextWatchId = 0;
    clearWatch.mockClear();
    watchPosition.mockReset();
    watchPosition.mockImplementation(
      (success: PositionCallback, failure: PositionErrorCallback, options: PositionOptions) => {
        expect(options).toEqual({ enableHighAccuracy: true, maximumAge: 0, timeout: 15000 });
        handlers.push({ success, failure });
        nextWatchId += 1;
        return nextWatchId;
      },
    );
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: { clearWatch, watchPosition },
    });
    Object.defineProperty(navigator, "permissions", { configurable: true, value: undefined });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  async function acquire() {
    const rendered = renderHook(() => useGuidancePosition());
    await act(async () => {
      await rendered.result.current.refresh();
    });
    return rendered;
  }

  it("clears the watch the instant the first sample arrives and never fires again", async () => {
    const { result } = await acquire();
    await act(async () => {
      handlers[0].success(sample());
    });

    expect(result.current.status).toBe("ready");
    expect(clearWatch).toHaveBeenCalledWith(1);
    expect(watchPosition).toHaveBeenCalledTimes(1);

    // T022 — no-background-tracking proof: the watch is gone, so a further
    // device callback cannot change the resolved snapshot.
    const resolved = result.current.position;
    await act(async () => {
      handlers[0].success(sample({ latitude: 0, longitude: 0, accuracy: 999 }));
    });
    expect(result.current.position).toBe(resolved);
    expect(watchPosition).toHaveBeenCalledTimes(1);
  });

  it("carries capturedAt and accuracyM through verbatim", async () => {
    const { result } = await acquire();
    await act(async () => {
      handlers[0].success(sample({ accuracy: 37.25 }));
    });

    expect(result.current.position).toEqual({
      latitude: 10.78585,
      longitude: 106.6926,
      accuracyM: 37.25,
      capturedAt: new Date(CAPTURED_AT).toISOString(),
    });
  });

  it("terminates the acquiring state within the timeout instead of hanging", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { result } = await acquire();
    expect(result.current.status).toBe("prompting");

    await act(async () => {
      vi.advanceTimersByTime(ACQUISITION_TIMEOUT_MS);
    });

    expect(result.current.status).toBe("error");
    expect(result.current.error).toEqual({ kind: "TIMEOUT" });
    expect(clearWatch).toHaveBeenCalledWith(1);
  });

  it.each([
    [1, "PERMISSION_DENIED"],
    [2, "UNAVAILABLE"],
    [3, "TIMEOUT"],
    [99, "UNKNOWN"],
  ])("classifies device error code %s as %s", async (code, kind) => {
    const { result } = await acquire();
    await act(async () => {
      handlers[0].failure({ code } as GeolocationPositionError);
    });

    expect(result.current.status).toBe("error");
    expect(result.current.error).toEqual({ kind });
  });

  it("reports UNAVAILABLE when the device exposes no geolocation at all", async () => {
    Object.defineProperty(navigator, "geolocation", { configurable: true, value: undefined });
    const { result } = await acquire();

    expect(result.current.status).toBe("error");
    expect(result.current.error).toEqual({ kind: "UNAVAILABLE" });
  });

  it.each([
    ["non-finite latitude", { latitude: Number.NaN }],
    ["out-of-range latitude", { latitude: 91 }],
    ["out-of-range longitude", { longitude: -181 }],
    ["negative accuracy", { accuracy: -1 }],
    ["non-finite accuracy", { accuracy: Number.POSITIVE_INFINITY }],
  ])("rejects an unusable sample: %s", async (_label, overrides) => {
    const { result } = await acquire();
    await act(async () => {
      handlers[0].success(sample(overrides));
    });

    expect(result.current.status).toBe("error");
    expect(result.current.error).toEqual({ kind: "UNAVAILABLE" });
    expect(result.current.position).toBeUndefined();
  });

  it("supersedes an in-flight acquisition and discards its out-of-order result", async () => {
    const { result } = await acquire();
    await act(async () => {
      await result.current.refresh();
    });

    expect(watchPosition).toHaveBeenCalledTimes(2);
    expect(clearWatch).toHaveBeenCalledWith(1);

    // the superseded request answers first and must be discarded
    await act(async () => {
      handlers[0].success(sample({ latitude: 0, longitude: 0, accuracy: 500 }));
    });
    expect(result.current.status).not.toBe("ready");
    expect(result.current.position).toBeUndefined();

    await act(async () => {
      handlers[1].success(sample());
    });
    expect(result.current.position?.latitude).toBe(10.78585);
  });

  it("tears down on a hidden tab and on unmount", async () => {
    const { result, unmount } = await acquire();
    Object.defineProperty(document, "hidden", { configurable: true, value: true });
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });

    await waitFor(() => expect(result.current.status).toBe("idle"));
    expect(clearWatch).toHaveBeenCalledWith(1);

    Object.defineProperty(document, "hidden", { configurable: true, value: false });
    clearWatch.mockClear();
    await act(async () => {
      await result.current.refresh();
    });
    unmount();
    expect(clearWatch).toHaveBeenCalledWith(2);
  });

  it("reports a denied permission without inventing an Attendance error code", async () => {
    const { result } = await acquire();
    await act(async () => {
      handlers[0].failure({ code: 1 } as GeolocationPositionError);
    });

    expect(result.current.permission).toBe("denied");
    expect(result.current.error?.kind).toBe("PERMISSION_DENIED");
  });
});
