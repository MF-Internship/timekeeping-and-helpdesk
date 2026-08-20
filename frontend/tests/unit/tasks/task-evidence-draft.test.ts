import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  loadEvidenceDraft,
  purgeEvidenceDrafts,
  saveEvidenceDraft,
} from "@/features/tasks/model/evidence-draft";

describe("FIELD_EVIDENCE local draft security and lifecycle", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("persists only compressed photo bytes, safe metadata, note and expiry", async () => {
    const photo = new File(["compressed-image"], "proof.jpg", {
      type: "image/jpeg",
      lastModified: 123,
    });
    expect(await saveEvidenceDraft(17, 42, [photo], "Đã xử lý")).toEqual({ kind: "saved" });
    const raw = localStorage.getItem("task-evidence-draft:17:42") ?? "";
    expect(raw).toContain("base64");
    for (const forbidden of [
      "latitude", "longitude", "accuracy", "captured_at", "access", "refresh",
      "token", "upload_id", "object_key", "presigned", "url", "idempotency",
    ]) expect(raw.toLowerCase()).not.toContain(forbidden);
    const restored = loadEvidenceDraft(17, 42);
    expect(restored).toMatchObject({ kind: "ready", note: "Đã xử lý" });
    if (restored.kind === "ready") expect(restored.files[0]?.name).toBe("proof.jpg");
  });

  it("purges only the requested account and reports browser eviction", async () => {
    await saveEvidenceDraft(17, 42, [], "account 17");
    await saveEvidenceDraft(18, 42, [], "account 18");
    purgeEvidenceDrafts(17);
    expect(loadEvidenceDraft(17, 42)).toEqual({ kind: "empty" });
    expect(loadEvidenceDraft(18, 42).kind).toBe("ready");
    localStorage.removeItem("task-evidence-draft:18:42");
    expect(loadEvidenceDraft(18, 42)).toEqual({ kind: "evicted" });
  });

  it("reports quota and unavailable storage without claiming a save", async () => {
    const quota = vi.spyOn(Storage.prototype, "setItem").mockImplementationOnce(() => {
      throw new DOMException("full", "QuotaExceededError");
    });
    expect(await saveEvidenceDraft(17, 42, [], "note")).toEqual({ kind: "quota" });
    quota.mockRestore();
    vi.spyOn(Storage.prototype, "getItem").mockImplementationOnce(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    expect(loadEvidenceDraft(17, 42)).toEqual({ kind: "unavailable" });
  });
});
