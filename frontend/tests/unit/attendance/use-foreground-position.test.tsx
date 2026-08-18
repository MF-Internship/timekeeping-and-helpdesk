import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useForegroundPosition } from "@/features/attendance/model/use-foreground-position";

describe("useForegroundPosition", () => {
  const clearWatch = vi.fn();
  let success: PositionCallback;

  beforeEach(() => {
    clearWatch.mockClear();
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: {
        clearWatch,
        watchPosition: vi.fn((next: PositionCallback, _error, options) => {
          success = next;
          expect(options).toEqual({ enableHighAccuracy: true, maximumAge: 0, timeout: 15000 });
          return 7;
        }),
      },
    });
  });

  it("acquires only after a gesture and stops after the fresh sample", async () => {
    const { result } = renderHook(() => useForegroundPosition());
    const pending = result.current.acquire();
    await act(async () => {
      success({
        coords: { latitude: 10, longitude: 106, accuracy: 5 } as GeolocationCoordinates,
        timestamp: Date.now(),
      } as GeolocationPosition);
    });
    await expect(pending).resolves.toMatchObject({ latitude: "10", longitude: "106" });
    expect(clearWatch).toHaveBeenCalledWith(7);
  });

  it("stops on cancel, hidden lifecycle, and unmount without submitting", () => {
    const { result, unmount } = renderHook(() => useForegroundPosition());
    void result.current.acquire();
    act(() => result.current.cancel());
    Object.defineProperty(document, "hidden", { configurable: true, value: true });
    act(() => document.dispatchEvent(new Event("visibilitychange")));
    unmount();
    expect(clearWatch).toHaveBeenCalled();
  });
});
