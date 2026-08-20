import { fireEvent, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getConfig, listLocations } from "@/features/locations/api/location-api";

import {
  directoryRow,
  locationRow,
  mockGeolocation,
  mockGeolocationAt,
  mockReference,
  nearbyRegion,
  renderPanel,
  settle,
  type Point,
} from "./panel-harness";

vi.mock("@/features/locations/api/location-api", () => ({
  listLocations: vi.fn(),
  getConfig: vi.fn(),
}));

/**
 * The three known overlapping Location pairs, taken from the seeded canonical
 * set exactly as `contracts/fixtures/geofence-distance.json` records them. The
 * position used for each pair is the first member's centre, so the second
 * member's distance is the fixture's own `expected_distance_m`.
 */
type Member = { code: string; point: Point; name: string; address: string };
type Pair = { label: string; anchor: Member; other: Member; otherDistance: string };

const COINCIDENT_POINT: Point = { latitude: 10.78585, longitude: 106.6926 };
const SHARED_ADDRESS = "12 Nguyễn Văn Trỗi, Phú Nhuận";

const PAIRS: readonly Pair[] = [
  {
    label: "coincident pair HCM000079 / HCM010005",
    anchor: {
      code: "HCM000079",
      point: COINCIDENT_POINT,
      name: "Cửa hàng Phú Nhuận",
      address: SHARED_ADDRESS,
    },
    other: {
      code: "HCM010005",
      point: COINCIDENT_POINT,
      name: "Kho Phú Nhuận",
      address: SHARED_ADDRESS,
    },
    otherDistance: "0.0 m",
  },
  {
    label: "overlapping pair HCM030015 / HCM030000",
    anchor: {
      code: "HCM030015",
      point: { latitude: 10.74068, longitude: 106.69802 },
      name: "Điểm HCM030015",
      address: "Địa chỉ HCM030015",
    },
    other: {
      code: "HCM030000",
      point: { latitude: 10.740723, longitude: 106.698024 },
      name: "Điểm HCM030000",
      address: "Địa chỉ HCM030000",
    },
    otherDistance: "4.8 m",
  },
  {
    label: "overlapping pair HCM010018 / HCM010000",
    anchor: {
      code: "HCM010018",
      point: { latitude: 10.7697, longitude: 106.68165 },
      name: "Điểm HCM010018",
      address: "Địa chỉ HCM010018",
    },
    other: {
      code: "HCM010000",
      point: { latitude: 10.770116582718295, longitude: 106.68157256751628 },
      name: "Điểm HCM010000",
      address: "Địa chỉ HCM010000",
    },
    otherDistance: "47.1 m",
  },
];

function rowsOf(pair: Pair) {
  return [pair.anchor, pair.other].map((member) =>
    locationRow(member.code, member.point, { name: member.name, address: member.address }),
  );
}

/** Renders the panel standing at the pair's anchor, inside both geofences. */
async function renderAtPair(pair: Pair) {
  mockReference(rowsOf(pair));
  mockGeolocationAt(pair.anchor.point);
  await renderPanel();
}

function targetRegion(): HTMLElement {
  return screen.getByRole("region", { name: "Địa điểm đang xem" });
}

function verdict(): HTMLElement {
  return screen.getByRole("status", { name: "" });
}

async function focusOn(code: string, name: string) {
  fireEvent.click(screen.getByRole("radio", { name: `${code} — ${name}` }));
  await settle();
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

/** Scenario C — every containing Location is its own row (SC-007, FR-013). */
describe("scenario C — overlapping Locations are listed separately", () => {
  it.each(PAIRS)("lists both members of the $label", async (pair) => {
    await renderAtPair(pair);
    const rows = within(nearbyRegion()).getAllByRole("listitem");

    expect(rows).toHaveLength(2);
    expect(rows.map((row) => row.textContent)).toEqual([
      expect.stringContaining(pair.anchor.code),
      expect.stringContaining(pair.other.code),
    ]);
  });

  it.each(PAIRS)(
    "gives each entry its own name, address, distance and radius ($label)",
    async (pair) => {
      await renderAtPair(pair);
      const [first, second] = within(nearbyRegion()).getAllByRole("listitem");

      expect(first).toHaveTextContent(pair.anchor.name);
      expect(first).toHaveTextContent(pair.anchor.address);
      expect(first).toHaveTextContent("Khoảng cách: 0.0 m — Bán kính: 50.0 m");
      expect(second).toHaveTextContent(pair.other.name);
      expect(second).toHaveTextContent(pair.other.address);
      expect(second).toHaveTextContent(`Khoảng cách: ${pair.otherDistance} — Bán kính: 50.0 m`);
    },
  );

  it.each(PAIRS)("classifies both as inside and says so once ($label)", async (pair) => {
    await renderAtPair(pair);
    const rows = within(nearbyRegion()).getAllByRole("listitem");

    for (const row of rows) {
      expect(row).toHaveTextContent("Trong vùng");
      expect(row).not.toHaveTextContent("Ngoài vùng");
    }
    expect(verdict()).toHaveTextContent(
      "Bạn đang ở trong vùng của nhiều địa điểm đã đăng ký chồng lấn.",
    );
  });

  it("states that the server decides which Location applies at punch time", async () => {
    await renderAtPair(PAIRS[0]);

    expect(verdict()).toHaveTextContent(
      "Khi bạn chấm công, máy chủ sẽ hỏi bạn chọn một trong số đó. Bản xem trước này không chọn thay bạn.",
    );
  });
});

/**
 * Address and distance are identical for the coincident pair, so `code` beside
 * the name is the only thing that tells the two rows apart (SC-007).
 */
describe("identical coordinates stay distinguishable", () => {
  const COINCIDENT = PAIRS[0];

  it("shows both codes even though the address and distance match", async () => {
    await renderAtPair(COINCIDENT);
    const rows = within(nearbyRegion()).getAllByRole("listitem");

    expect(rows[0]).toHaveTextContent(`${COINCIDENT.anchor.code} — ${COINCIDENT.anchor.name}`);
    expect(rows[1]).toHaveTextContent(`${COINCIDENT.other.code} — ${COINCIDENT.other.name}`);
    for (const row of rows) {
      expect(row).toHaveTextContent(SHARED_ADDRESS);
      expect(row).toHaveTextContent("Khoảng cách: 0.0 m");
    }
  });

  it("offers each of them as its own target", async () => {
    await renderAtPair(COINCIDENT);
    const choices = within(nearbyRegion()).getAllByRole("radio");

    expect(choices.map((choice) => (choice as HTMLInputElement).value)).toEqual([
      COINCIDENT.anchor.code,
      COINCIDENT.other.code,
    ]);
  });

  it("neither merges nor drops the duplicate coordinates", async () => {
    await renderAtPair(COINCIDENT);

    expect(within(nearbyRegion()).getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getAllByText(SHARED_ADDRESS).length).toBeGreaterThanOrEqual(2);
  });
});

/**
 * Scenario J — a nearer 50 m geofence and a wider 70 m one both contain the
 * position, so switching focus has to move every readout, radius included.
 */
describe("scenario J — switching the focused target", () => {
  const NEAR = "HCM000012";
  const WIDE = "HCM000034";
  const WIDE_NORTH_M = 40;
  const OVERLAPPING = [directoryRow(NEAR, 0), directoryRow(WIDE, WIDE_NORTH_M, "70.000")];

  async function renderOverlap() {
    mockReference(OVERLAPPING);
    mockGeolocation();
    await renderPanel();
  }

  it("defaults to the nearest Location with no selection made", async () => {
    await renderOverlap();
    const region = targetRegion();

    expect(
      within(nearbyRegion()).getByRole("radio", { name: `${NEAR} — Điểm ${NEAR}` }),
    ).toBeChecked();
    expect(
      within(nearbyRegion()).getByRole("radio", { name: `${WIDE} — Điểm ${WIDE}` }),
    ).not.toBeChecked();
    expect(within(region).getByText("0.0 m")).toBeVisible();
    expect(within(region).getAllByText("50.0 m")).toHaveLength(2);
  });

  it("switches the distance, radius and boundary readouts to the chosen Location", async () => {
    await renderOverlap();
    await focusOn(WIDE, `Điểm ${WIDE}`);
    const region = targetRegion();

    expect(
      within(nearbyRegion()).getByRole("radio", { name: `${WIDE} — Điểm ${WIDE}` }),
    ).toBeChecked();
    expect(region).toHaveTextContent(WIDE);
    expect(region).toHaveTextContent(`Điểm ${WIDE}`);
    expect(within(region).getByText("40.0 m")).toBeVisible();
    expect(within(region).getByText("70.0 m")).toBeVisible();
    expect(within(region).getByText("30.0 m")).toBeVisible();
    expect(region).not.toHaveTextContent("Khoảng cách: 0.0 m");
  });

  it("switches back, so focus is a way of reading and not a commitment", async () => {
    await renderOverlap();
    await focusOn(WIDE, `Điểm ${WIDE}`);
    await focusOn(NEAR, `Điểm ${NEAR}`);
    const region = targetRegion();

    expect(
      within(nearbyRegion()).getByRole("radio", { name: `${NEAR} — Điểm ${NEAR}` }),
    ).toBeChecked();
    expect(within(region).getByText("0.0 m")).toBeVisible();
    expect(within(region).getAllByText("50.0 m")).toHaveLength(2);
  });

  it("leaves the ranked list untouched when focus moves", async () => {
    await renderOverlap();
    const before = within(nearbyRegion())
      .getAllByRole("listitem")
      .map((row) => row.textContent);
    await focusOn(WIDE, `Điểm ${WIDE}`);
    const after = within(nearbyRegion())
      .getAllByRole("listitem")
      .map((row) => row.textContent);

    expect(after).toEqual(before);
  });

  it("submits nothing, persists nothing, and pre-selects nothing", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    await renderOverlap();
    vi.mocked(listLocations).mockClear();
    vi.mocked(getConfig).mockClear();

    await focusOn(WIDE, `Điểm ${WIDE}`);

    expect(listLocations).not.toHaveBeenCalled();
    expect(getConfig).not.toHaveBeenCalled();
    expect(setItem).not.toHaveBeenCalled();
    expect(document.body.textContent ?? "").not.toContain("selected_location_id");
    expect(document.querySelector("form")).toBeNull();
    expect(targetRegion()).toHaveTextContent("không chọn địa điểm cho lần chấm công");
  });

  it("keeps the focus across a position refresh", async () => {
    await renderOverlap();
    await focusOn(WIDE, `Điểm ${WIDE}`);

    fireEvent.click(screen.getByRole("button", { name: "Làm mới vị trí" }));
    await settle();

    expect(
      within(nearbyRegion()).getByRole("radio", { name: `${WIDE} — Điểm ${WIDE}` }),
    ).toBeChecked();
  });
});

/**
 * The 0% half of SC-007: overlap must not surface as an error anywhere, in any
 * vocabulary, for any of the three pairs (FR-024).
 */
describe("overlap is not an error", () => {
  const FAILURE_VOCABULARY = [
    "Không lấy được vị trí",
    "Trình duyệt đã bị từ chối quyền truy cập vị trí.",
    "Thiết bị hoặc trình duyệt này không cung cấp dịch vụ định vị.",
    "Quá thời gian chờ khi lấy vị trí.",
    "Đã xảy ra sự cố không xác định khi lấy vị trí.",
    "Không tải được danh mục địa điểm hoặc cấu hình. Chưa thể đối chiếu vị trí.",
    "Không có địa điểm đang hoạt động nào để đối chiếu.",
    "OUTSIDE_RADIUS",
    "LOCATION_CHOICE_REQUIRED",
    "INVALID_LOCATION_CHOICE",
    "VALIDATION_FAILED",
    "WEAK_GPS",
  ];

  it.each(PAIRS)("renders no error role and no failure wording for the $label", async (pair) => {
    await renderAtPair(pair);
    const rendered = document.body.textContent ?? "";

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Thử lại" })).not.toBeInTheDocument();
    for (const phrase of FAILURE_VOCABULARY) {
      expect(rendered).not.toContain(phrase);
    }
  });

  it.each(PAIRS)("marks neither member as a duplicate to merge ($label)", async (pair) => {
    await renderAtPair(pair);
    const region = nearbyRegion();

    expect(region).not.toHaveTextContent("trùng");
    expect(region).not.toHaveTextContent("Ngoài vùng");
    expect(region).toHaveTextContent(pair.anchor.code);
    expect(region).toHaveTextContent(pair.other.code);
  });
});
