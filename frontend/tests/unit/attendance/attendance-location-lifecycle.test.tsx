import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useForegroundPosition } from "@/features/attendance/model/use-foreground-position";

describe("attendance location lifecycle", () => {
  it("starts no watch until the user explicitly acquires a punch position", () => {
    const watchPosition = vi.fn();
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: { watchPosition, clearWatch: vi.fn() },
    });
    const { unmount } = renderHook(() => useForegroundPosition());
    expect(watchPosition).not.toHaveBeenCalled();
    unmount();
  });
});
