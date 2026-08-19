/**
 * Presentation helpers. Every value they receive has already been computed from
 * the unrounded sample: rounding happens here and nowhere upstream (FR-003a).
 */

const COORDINATE_DECIMALS = 6;
const METRE_DECIMALS = 1;

/** Six decimal places for display only — never fed back into a computation. */
export function formatCoordinate(value: number): string {
  return value.toFixed(COORDINATE_DECIMALS);
}

/** Metres, with the unit always visible (FR-011, FR-014). */
export function formatMetres(value: number): string {
  return `${value.toFixed(METRE_DECIMALS)} m`;
}

/** Local clock time of a device sample timestamp. */
export function formatClockTime(isoInstant: string): string {
  return new Date(isoInstant).toLocaleTimeString("vi-VN", { hour12: false });
}
