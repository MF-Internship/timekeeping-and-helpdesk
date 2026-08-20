import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { FieldEvidenceForm } from "@/features/tasks/ui/FieldEvidenceForm";

const api = vi.hoisted(() => ({ intent: vi.fn(), upload: vi.fn() }));
vi.mock("@/features/tasks/api/task-api", async (load) => ({
  ...(await load()),
  createEvidenceUpload: api.intent,
  uploadEvidenceFile: api.upload,
}));

beforeEach(() => {
  vi.stubGlobal("crypto", {
    subtle: { digest: vi.fn().mockResolvedValue(new Uint8Array([1, 2, 3]).buffer) },
    randomUUID: vi.fn().mockReturnValue("00000000-0000-4000-8000-000000000099"),
  });
  api.intent.mockReset().mockResolvedValue({
    upload_id: "00000000-0000-4000-8000-000000000001",
    upload_url: "https://storage.invalid/upload",
    headers: {},
    expires_at: "2026-08-20T12:00:00Z",
  });
  api.upload.mockReset().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "geolocation", {
    configurable: true,
    value: {
      getCurrentPosition: (success: PositionCallback) =>
        success({
          coords: { latitude: 10, longitude: 106, accuracy: 12 } as GeolocationCoordinates,
          timestamp: Date.now(),
        } as GeolocationPosition),
    },
  });
});

describe("Field evidence completion", () => {
  it("uploads once, captures fresh GPS and reuses the upload after a location choice", async () => {
    const complete = vi
      .fn()
      .mockRejectedValueOnce({
        kind: "canonical",
        errorCode: "LOCATION_CHOICE_REQUIRED",
        details: { candidates: [{ id: 2, code: "HCM", name: "Trung tâm HCM" }] },
      })
      .mockResolvedValueOnce(undefined);
    render(
      <FieldEvidenceForm
        taskId={7}
        taskTitle="Kiểm tra máy in"
        busy={false}
        onComplete={complete}
      />,
    );
    const file = new File(["jpg"], "proof.jpg", { type: "image/jpeg" });
    fireEvent.change(screen.getByLabelText("Ảnh minh chứng"), { target: { files: [file] } });
    fireEvent.submit(screen.getByRole("form", { name: "Nộp minh chứng Kiểm tra máy in" }));
    await screen.findByText(/nhiều khu vực/);
    fireEvent.change(screen.getByLabelText("Địa điểm thực tế"), { target: { value: "2" } });
    fireEvent.submit(screen.getByRole("form", { name: "Nộp minh chứng Kiểm tra máy in" }));
    await waitFor(() => expect(complete).toHaveBeenCalledTimes(2));
    expect(api.intent).toHaveBeenCalledTimes(1);
    expect(api.upload).toHaveBeenCalledTimes(1);
    expect(complete.mock.calls[1][0]).toMatchObject({
      selected_location_id: 2,
      latitude: "10",
      longitude: "106",
      accuracy_m: "12",
    });
    expect(complete.mock.calls[1][1]).toBe(complete.mock.calls[0][1]);
  });

  it("retains successful uploads and retries only the incomplete suffix", async () => {
    api.intent
      .mockResolvedValueOnce({
        upload_id: "upload-1",
        upload_url: "https://storage.invalid/1",
        headers: {},
        expires_at: "2026-08-20T12:00:00Z",
      })
      .mockResolvedValueOnce({
        upload_id: "upload-2",
        upload_url: "https://storage.invalid/2",
        headers: {},
        expires_at: "2026-08-20T12:00:00Z",
      })
      .mockResolvedValueOnce({
        upload_id: "upload-2b",
        upload_url: "https://storage.invalid/2b",
        headers: {},
        expires_at: "2026-08-20T12:00:00Z",
      });
    api.upload
      .mockResolvedValueOnce(undefined)
      .mockRejectedValueOnce(new Error("Mạng lỗi"))
      .mockResolvedValueOnce(undefined);
    const complete = vi.fn().mockResolvedValue(undefined);
    render(<FieldEvidenceForm taskId={7} taskTitle="Hai ảnh" busy={false} onComplete={complete} />);
    fireEvent.change(screen.getByLabelText("Ảnh minh chứng"), {
      target: {
        files: [
          new File(["1"], "one.jpg", { type: "image/jpeg" }),
          new File(["2"], "two.jpg", { type: "image/jpeg" }),
        ],
      },
    });
    const form = screen.getByRole("form", { name: "Nộp minh chứng Hai ảnh" });
    fireEvent.submit(form);
    await screen.findByText("Mạng lỗi");
    fireEvent.submit(form);
    await waitFor(() => expect(complete).toHaveBeenCalledTimes(1));
    expect(api.intent).toHaveBeenCalledTimes(3);
    expect(complete.mock.calls[0][0].upload_ids).toEqual(["upload-1", "upload-2b"]);
  });
});
