import type { LocationCandidate } from "@/features/attendance/model/attendance-state";

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
            <button type="button" disabled={disabled} onClick={() => onSelect(candidate.id)}>
              Chọn
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
