import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("@/features/operations/api/job-health-api", () => ({ getJobHealth: api.get }));

import { useJobHealth } from "@/features/operations/model/job-health-state";

describe("useJobHealth", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    api.get.mockReset().mockResolvedValue({ state: "ok", refreshed_at: "2026-08-19" });
  });
  afterEach(() => vi.useRealTimers());

  it("loads, refreshes every visible minute, pauses hidden, and cleans up", async () => {
    const interval = vi.spyOn(window, "setInterval");
    const clear = vi.spyOn(window, "clearInterval");
    const { result, unmount } = renderHook(() => useJobHealth());
    await act(async () => {
      vi.runAllTicks();
      await Promise.resolve();
    });
    expect(api.get).toHaveBeenCalledTimes(1);
    await act(async () => vi.advanceTimersByTimeAsync(60_000));
    expect(api.get).toHaveBeenCalledTimes(2);
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    await act(async () => vi.advanceTimersByTimeAsync(60_000));
    expect(api.get).toHaveBeenCalledTimes(2);
    await act(async () => result.current.refresh());
    expect(api.get).toHaveBeenCalledTimes(3);
    unmount();
    expect(interval).toHaveBeenCalled();
    expect(clear).toHaveBeenCalled();
  });
});
