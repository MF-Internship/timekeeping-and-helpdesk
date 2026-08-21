import { beforeEach, describe, expect, it, vi } from "vitest";

import { clearUserCache, readUserCache, writeUserCache } from "@/shared/cache/user-resource-cache";

beforeEach(() => {
  window.sessionStorage.clear();
  vi.useRealTimers();
});

describe("user resource cache", () => {
  it("isolates the same resource between accounts", () => {
    writeUserCache(11, "tasks", { title: "Công việc của An" });
    writeUserCache(22, "tasks", { title: "Công việc của Bình" });

    expect(readUserCache<{ title: string }>(11, "tasks")?.title).toBe("Công việc của An");
    expect(readUserCache<{ title: string }>(22, "tasks")?.title).toBe("Công việc của Bình");
  });

  it("expires stale data and clears only the selected account resource", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-21T08:00:00Z"));
    writeUserCache(11, "tasks", [1]);
    writeUserCache(11, "task-locations", [2]);
    writeUserCache(22, "tasks", [3]);

    clearUserCache(11, "task");
    expect(readUserCache(11, "tasks")).toBeUndefined();
    expect(readUserCache(11, "task-locations")).toBeUndefined();
    expect(readUserCache(22, "tasks")).toEqual([3]);

    vi.advanceTimersByTime(301_000);
    expect(readUserCache(22, "tasks")).toBeUndefined();
  });
});
