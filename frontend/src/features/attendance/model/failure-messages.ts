import { isCanonicalFailure } from "./attendance-state";

/**
 * The wording kept from before this feature, used for every canonical code
 * without its own entry and for every non-canonical failure. Nothing is dropped
 * by the map below: an unmapped outcome still reaches the user.
 */
export const GENERIC_PUNCH_FAILURE = "Không thể hoàn tất chấm công. Vui lòng thử lại.";

/**
 * The server's verdict is the outcome the user acts on, so each canonical
 * Attendance code gets its own sentence rather than one generic string
 * (quickstart scenario 6, FR-041). Every sentence is attributed to the server,
 * because that is where the decision was taken and the on-device preview is
 * never rewritten to agree with it.
 *
 * These are Attendance server codes and nothing else. The four
 * `AcquisitionErrorKind` values of FR-008a describe a device that could not
 * produce a reading and are worded in `UI_MESSAGES.guidance.failure`; none of
 * them appears here. In particular the canonical `PERMISSION_DENIED` is an
 * authorization denial and deliberately has no entry in this map — wording it
 * as a geolocation permission denial is the conflation FR-008b forbids, so it
 * falls through to the generic text instead.
 */
const PUNCH_FAILURES: Readonly<Record<string, string>> = Object.freeze({
  OUTSIDE_RADIUS: "Máy chủ từ chối: vị trí đọc được lúc chấm công nằm ngoài bán kính của địa điểm.",
  WEAK_GPS: "Máy chủ từ chối: sai số GPS lúc chấm công vượt ngưỡng cho phép.",
  SESSION_ALREADY_OPEN: "Máy chủ từ chối: bạn đang có một phiên làm việc chưa đóng.",
  NO_OPEN_SESSION: "Máy chủ từ chối: không có phiên làm việc nào đang mở để check out.",
  INVALID_LOCATION_CHOICE:
    "Máy chủ từ chối: địa điểm bạn chọn không nằm trong danh sách máy chủ đưa ra. Hãy chọn lại trong danh sách bên dưới.",
});

/**
 * The one code that is not a message: `LOCATION_CHOICE_REQUIRED` is answered by
 * showing the server's candidate list, so it stays on that path (T078).
 */
const ANSWERED_BY_CANDIDATE_LIST = "LOCATION_CHOICE_REQUIRED";

/** `undefined` when the failure is presented as a choice rather than as text. */
export function punchFailureMessage(failure: unknown): string | undefined {
  if (!isCanonicalFailure(failure)) return GENERIC_PUNCH_FAILURE;
  if (failure.errorCode === ANSWERED_BY_CANDIDATE_LIST) return undefined;
  return PUNCH_FAILURES[failure.errorCode] ?? GENERIC_PUNCH_FAILURE;
}
