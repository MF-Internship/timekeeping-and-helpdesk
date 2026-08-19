import type { LocationCandidate } from "@/features/attendance/model/attendance-state";
import { Button } from "@/shared/ui/button";

/**
 * The server's `409 LOCATION_CHOICE_REQUIRED` candidate set, rendered exactly as
 * it arrived: same members, same order, nothing filtered out, nothing added
 * from the guidance preview, and no entry pre-selected. The choice the user
 * makes is validated against this set by the server, so a list edited here
 * could only offer an answer the server would reject (FR-042).
 */
export function LocationChoice({
  candidates,
  disabled,
  onSelect,
}: {
  candidates: LocationCandidate[];
  disabled: boolean;
  onSelect(id: number): void;
}) {
  return (
    <section aria-label="Chọn địa điểm chấm công">
      <p>Vị trí hiện tại thuộc nhiều địa điểm. Vui lòng chọn:</p>
      <ul className="record-list">
        {candidates.map((candidate) => (
          <li key={candidate.id}>
            <span>
              {candidate.name} — {candidate.distance_m} m
            </span>
            <Button disabled={disabled} onClick={() => onSelect(candidate.id)}>
              Chọn
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}
