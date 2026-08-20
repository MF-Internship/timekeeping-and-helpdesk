import { screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  advance,
  directoryRow,
  installGeolocation,
  mockGeolocationFailure,
  mockGeolocationSilent,
  mockReference,
  positionRegion,
  pressRefresh,
  refreshButton,
  renderPanel,
} from "./panel-harness";

vi.mock("@/features/locations/api/location-api", () => ({
  listLocations: vi.fn(),
  getConfig: vi.fn(),
}));

/** The W3C `GeolocationPositionError` codes, plus one outside the range. */
const DENIED_CODE = 1;
const UNAVAILABLE_CODE = 2;
const TIMEOUT_CODE = 3;
const UNRECOGNISED_CODE = 99;

const ACQUISITION_TIMEOUT_MS = 15_000;

const NEAR = "HCM000012";
const FAR = "HCM000079";
const DIRECTORY = [directoryRow(FAR, 900), directoryRow(NEAR, 10)];

const DENIED_TITLE = "Trình duyệt đã bị từ chối quyền truy cập vị trí.";
const UNAVAILABLE_TITLE = "Thiết bị hoặc trình duyệt này không cung cấp dịch vụ định vị.";
const TIMEOUT_TITLE = "Quá thời gian chờ khi lấy vị trí.";
const UNKNOWN_TITLE = "Đã xảy ra sự cố không xác định khi lấy vị trí.";

function referenceRegion(): HTMLElement {
  return screen.getByRole("region", { name: "Danh mục địa điểm đang hoạt động" });
}

beforeEach(() => {
  vi.useFakeTimers();
  mockReference(DIRECTORY);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("scenario E — permission denied", () => {
  it("names the denial and offers a retry", async () => {
    mockGeolocationFailure(DENIED_CODE);

    await renderPanel();

    const card = positionRegion();
    expect(card).toHaveTextContent("Không lấy được vị trí");
    expect(card).toHaveTextContent(DENIED_TITLE);
    expect(card).toHaveTextContent("Mở cài đặt quyền của trình duyệt hoặc thiết bị");
    expect(refreshButton()).not.toBeDisabled();
  });

  it("holds no position and invents none", async () => {
    mockGeolocationFailure(DENIED_CODE);

    await renderPanel();

    const card = positionRegion();
    expect(card).toHaveTextContent(
      "Chưa ghi nhận được vị trí nào. Hệ thống không suy đoán vị trí thay cho bạn.",
    );
    expect(card).not.toHaveTextContent("Vĩ độ");
    expect(screen.queryByRole("region", { name: "Địa điểm gần bạn" })).not.toBeInTheDocument();
  });

  it("does not re-ask the device without a user action", async () => {
    const device = mockGeolocationFailure(DENIED_CODE);

    await renderPanel();
    expect(device.watchPosition).toHaveBeenCalledTimes(1);

    await advance(5 * ACQUISITION_TIMEOUT_MS);
    expect(device.watchPosition).toHaveBeenCalledTimes(1);

    await pressRefresh();
    expect(device.watchPosition).toHaveBeenCalledTimes(2);
  });
});

describe("scenario F — geolocation unavailable", () => {
  beforeEach(() => {
    installGeolocation(undefined);
  });

  it("reports unavailability in wording distinct from a denial", async () => {
    await renderPanel();

    const card = positionRegion();
    expect(card).toHaveTextContent(UNAVAILABLE_TITLE);
    expect(card).not.toHaveTextContent(DENIED_TITLE);
  });

  it("keeps the position-independent Location reference readable", async () => {
    await renderPanel();

    const region = referenceRegion();
    const rows = within(region).getAllByRole("listitem");
    expect(rows.map((row) => row.textContent)).toHaveLength(DIRECTORY.length);
    expect(region).toHaveTextContent(NEAR);
    expect(region).toHaveTextContent(FAR);
    expect(region).toHaveTextContent(`Điểm ${NEAR}`);
    expect(region).toHaveTextContent("Bán kính: 50.0 m");
    expect(region).toHaveTextContent("Danh sách này không phụ thuộc vào vị trí nên vẫn xem được.");
  });

  it("attaches no distance or membership status to that reference", async () => {
    await renderPanel();

    const region = referenceRegion();
    expect(region).not.toHaveTextContent("Khoảng cách");
    expect(region).not.toHaveTextContent("Trong vùng");
    expect(region).not.toHaveTextContent("Ngoài vùng");
    expect(region).not.toHaveTextContent("Gần nhất");
  });
});

describe("scenario G — acquisition timeout", () => {
  it("settles as a timeout, distinct from a denial", async () => {
    mockGeolocationSilent();

    await renderPanel();
    expect(positionRegion()).not.toHaveTextContent(TIMEOUT_TITLE);

    await advance(ACQUISITION_TIMEOUT_MS);

    const card = positionRegion();
    expect(card).toHaveTextContent(TIMEOUT_TITLE);
    expect(card).not.toHaveTextContent(DENIED_TITLE);
    expect(card).toHaveTextContent("Ra khu vực thoáng, chờ thiết bị bắt tín hiệu");
  });

  it("holds no partial position", async () => {
    mockGeolocationSilent();

    await renderPanel();
    await advance(ACQUISITION_TIMEOUT_MS);

    const card = positionRegion();
    expect(card).not.toHaveTextContent("Vĩ độ");
    expect(card).not.toHaveTextContent("Sai số hiện tại");
    expect(card).not.toHaveTextContent("Thời điểm đọc");
  });

  it("exposes a refresh that starts a new acquisition", async () => {
    const device = mockGeolocationSilent();

    await renderPanel();
    await advance(ACQUISITION_TIMEOUT_MS);

    expect(refreshButton()).not.toBeDisabled();
    await pressRefresh();
    expect(device.watchPosition).toHaveBeenCalledTimes(2);
  });
});

/**
 * The browser acquisition vocabulary is the guidance one: it is closed at four
 * outcomes and shares no token with the Attendance server codes (FR-008a,
 * FR-008b).
 */
describe("vocabulary separation", () => {
  const ATTENDANCE_CODES = [
    "VALIDATION_FAILED",
    "PERMISSION_DENIED",
    "INVALID_CREDENTIALS",
    "INVALID_TOKEN",
    "ACCOUNT_INACTIVE",
    "PASSWORD_CHANGE_REQUIRED",
    "SERVER_OWNED_FIELD",
    "NOT_FOUND",
    "LOCATION_VERSION_CONFLICT",
    "THROTTLED",
    "SERVICE_UNAVAILABLE",
    "WEAK_GPS",
    "OUTSIDE_RADIUS",
    "LOCATION_CHOICE_REQUIRED",
    "INVALID_LOCATION_CHOICE",
    "NO_OPEN_SESSION",
    "SESSION_ALREADY_OPEN",
  ];

  const KINDS = [DENIED_CODE, UNAVAILABLE_CODE, TIMEOUT_CODE, UNRECOGNISED_CODE];

  it.each(KINDS)("renders no Attendance error code for device error code %s", async (code) => {
    mockGeolocationFailure(code);

    await renderPanel();

    const rendered = document.body.textContent ?? "";
    expect(rendered).toContain("Không lấy được vị trí");
    for (const attendanceCode of ATTENDANCE_CODES) {
      expect(rendered).not.toContain(attendanceCode);
    }
  });

  it("gives an unrecognised failure its own message rather than one of the other three", async () => {
    mockGeolocationFailure(UNRECOGNISED_CODE);

    await renderPanel();

    const card = positionRegion();
    expect(card).toHaveTextContent(UNKNOWN_TITLE);
    expect(card).not.toHaveTextContent(DENIED_TITLE);
    expect(card).not.toHaveTextContent(UNAVAILABLE_TITLE);
    expect(card).not.toHaveTextContent(TIMEOUT_TITLE);
  });

  it("states that the failure is device-side and changes no server rule", async () => {
    mockGeolocationFailure(TIMEOUT_CODE);

    await renderPanel();

    expect(positionRegion()).toHaveTextContent(
      "Đây là sự cố phía thiết bị. Không thao tác nào ở đây thay đổi quy tắc của máy chủ.",
    );
  });
});
