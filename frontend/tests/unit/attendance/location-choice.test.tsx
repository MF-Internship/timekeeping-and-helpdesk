import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { candidateFailure, freshCommand } from "@/features/attendance/model/attendance-state";
import { LocationChoice } from "@/features/attendance/ui/LocationChoice";

const candidates = [
  { id: 1, code: "A", name: "Location A", distance_m: "10.000" },
  { id: 2, code: "B", name: "Location B", distance_m: "20.000" },
];

describe("Location choice", () => {
  it("renders the latest candidates and selects by server id", () => {
    const onSelect = vi.fn();
    render(<LocationChoice candidates={candidates} disabled={false} onSelect={onSelect} />);
    fireEvent.click(screen.getAllByRole("button", { name: "Chọn" })[1]);
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it("extracts both choice-required and invalid-choice replacement lists", () => {
    for (const errorCode of ["LOCATION_CHOICE_REQUIRED", "INVALID_LOCATION_CHOICE"]) {
      expect(
        candidateFailure({
          kind: "canonical",
          errorCode,
          details: { location_candidates: candidates },
        }),
      ).toEqual(candidates);
    }
  });

  it("acquires a new GPS sample before every selected-id resubmission", async () => {
    const acquire = vi.fn().mockResolvedValue({
      latitude: "10",
      longitude: "106",
      accuracy_m: "5",
      captured_at: "2026-08-18T00:00:00Z",
    });
    await freshCommand(acquire);
    const selected = await freshCommand(acquire, 2);
    expect(acquire).toHaveBeenCalledTimes(2);
    expect("selected_location_id" in selected && selected.selected_location_id).toBe(2);
  });
});
