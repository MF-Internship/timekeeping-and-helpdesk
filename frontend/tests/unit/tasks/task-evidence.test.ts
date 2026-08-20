import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  clearEvidenceDraft,
  loadEvidenceDraft,
  saveEvidenceDraft,
} from "@/features/tasks/model/evidence-draft";

describe("Task evidence drafts", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.useRealTimers();
  });

  it("isolates compressed photos and note by account and Task", async () => {
    const photo = new File(["compressed"], "proof.jpg", { type: "image/jpeg" });
    await saveEvidenceDraft(1, 10, [photo], "done");
    expect(loadEvidenceDraft(1, 10)).toMatchObject({ kind: "ready", note: "done" });
    expect(loadEvidenceDraft(2, 10)).toEqual({ kind: "empty" });
    expect(loadEvidenceDraft(1, 11)).toEqual({ kind: "empty" });
    clearEvidenceDraft(1, 10);
    expect(loadEvidenceDraft(1, 10)).toEqual({ kind: "empty" });
  });

  it("expires a local draft after seven days", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-20T00:00:00Z"));
    await saveEvidenceDraft(1, 10, [], "draft note");
    vi.advanceTimersByTime(7 * 24 * 60 * 60 * 1000 + 1);
    expect(loadEvidenceDraft(1, 10)).toEqual({ kind: "expired" });
  });
});
