import { screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { formatClockTime, formatCoordinate } from "@/features/guidance/ui/format";

import {
  CAPTURED_AT,
  METRES_PER_DEGREE_LATITUDE,
  POSITION,
  advance,
  directoryRow,
  mockGeolocation,
  mockReference,
  nearbyRegion,
  positionRegion,
  pressRefresh,
  refreshButton,
  renderPanel,
} from "./panel-harness";

vi.mock("@/features/locations/api/location-api", () => ({
  listLocations: vi.fn(),
  getConfig: vi.fn(),
}));

const NEAR = "HCM000012";
const FAR = "HCM000079";

/** `NEAR` contains the origin; `FAR` is far enough to contain nothing near it. */
const DIRECTORY = [directoryRow(FAR, 900), directoryRow(NEAR, 10)];

const STALE_AFTER_SECONDS = 60;

let device: ReturnType<typeof mockGeolocation>;

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(CAPTURED_AT);
  device = mockGeolocation();
  mockReference(DIRECTORY);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("scenario A — accurate reading inside exactly one Location", () => {
  it("names the Location and shows its distance, radius and inside status", async () => {
    await renderPanel();

    expect(
      screen.getByText("Bạn đang ở trong vùng của đúng một địa điểm đã đăng ký."),
    ).toBeInTheDocument();

    const [first] = within(nearbyRegion()).getAllByRole("listitem");
    expect(first).toHaveTextContent(NEAR);
    expect(first).toHaveTextContent(`Điểm ${NEAR}`);
    expect(first).toHaveTextContent("Khoảng cách: 10.0 m");
    expect(first).toHaveTextContent("Bán kính: 50.0 m");
    expect(first).toHaveTextContent("Trong vùng");
  });

  it("states that the reading meets the accuracy requirement", async () => {
    await renderPanel();

    const card = positionRegion();
    expect(card).toHaveTextContent("Sai số hiện tại: 12.0 m");
    expect(card).toHaveTextContent("Ngưỡng sai số cho phép khi chấm công: 100.0 m");
    expect(card).toHaveTextContent("Sai số đạt yêu cầu chấm công.");
  });
});

describe("scenario D — insufficient accuracy is its own gate", () => {
  beforeEach(() => {
    device.nextSample({ northM: 0, accuracyM: 150, timestamp: CAPTURED_AT });
  });

  it("states the reading is too imprecise for attendance regardless of position", async () => {
    await renderPanel();

    expect(positionRegion()).toHaveTextContent(
      "Sai số vượt ngưỡng. Chấm công sẽ bị từ chối vì GPS yếu, bất kể bạn đang ở đâu.",
    );
  });

  it("still reports the position verdict separately from the accuracy verdict", async () => {
    await renderPanel();

    expect(
      screen.getByText("Bạn đang ở trong vùng của đúng một địa điểm đã đăng ký."),
    ).toBeInTheDocument();
    const [first] = within(nearbyRegion()).getAllByRole("listitem");
    expect(first).toHaveTextContent("Trong vùng");
    expect(positionRegion()).toHaveTextContent("Chất lượng tín hiệu được đánh giá tách biệt");
  });

  it("offers device-side remediation only", async () => {
    await renderPanel();

    const card = positionRegion();
    expect(card).toHaveTextContent("Cách cải thiện tín hiệu trên thiết bị");
    expect(card).toHaveTextContent("Bấm Làm mới vị trí.");
    expect(card).toHaveTextContent(
      "Các thao tác này chỉ cải thiện tín hiệu trên thiết bị, không thay đổi quy tắc của máy chủ.",
    );
  });
});

describe("scenario H — refresh replaces the previous reading", () => {
  const AWAY = { northM: 900, accuracyM: 150, timestamp: CAPTURED_AT };
  const BACK = { northM: 0, accuracyM: 12, timestamp: CAPTURED_AT + 30_000 };

  it("replaces every displayed value rather than showing both readings", async () => {
    device.nextSample(AWAY);
    await renderPanel();
    const before = positionRegion().textContent ?? "";

    device.nextSample(BACK);
    await advance(30_000);
    await pressRefresh();
    const after = positionRegion().textContent ?? "";

    expect(after).not.toBe(before);
    expect(after).toContain(`Vĩ độ: ${formatCoordinate(POSITION.latitude)}`);
    expect(after).toContain("Sai số hiện tại: 12.0 m");
    expect(after).toContain("Sai số đạt yêu cầu chấm công.");
    expect(after).not.toContain(
      formatCoordinate(POSITION.latitude + AWAY.northM / METRES_PER_DEGREE_LATITUDE),
    );
    expect(after).not.toContain("150.0 m");
    expect(after).not.toContain("Sai số vượt ngưỡng");
  });

  it("re-evaluates the nearby list against the new reading", async () => {
    device.nextSample(AWAY);
    await renderPanel();
    expect(within(nearbyRegion()).getAllByRole("listitem")[0]).toHaveTextContent(FAR);

    device.nextSample(BACK);
    await advance(30_000);
    await pressRefresh();

    expect(within(nearbyRegion()).getAllByRole("listitem")[0]).toHaveTextContent(NEAR);
  });

  it("updates the acquisition time to the new reading", async () => {
    device.nextSample(AWAY);
    await renderPanel();

    device.nextSample(BACK);
    await advance(30_000);
    await pressRefresh();

    const after = positionRegion().textContent ?? "";
    expect(after).toContain(
      `Thời điểm đọc: ${formatClockTime(new Date(BACK.timestamp).toISOString())}`,
    );
    expect(after).not.toContain(formatClockTime(new Date(CAPTURED_AT).toISOString()));
  });
});

describe("scenario I — refresh into a worse reading", () => {
  const WORSE = { northM: 0, accuracyM: 150, timestamp: CAPTURED_AT + 5_000 };

  it("replaces a sufficient accuracy verdict with an insufficient one", async () => {
    await renderPanel();
    expect(positionRegion()).toHaveTextContent("Sai số đạt yêu cầu chấm công.");

    device.nextSample(WORSE);
    await advance(5_000);
    await pressRefresh();

    const after = positionRegion().textContent ?? "";
    expect(after).toContain("Sai số hiện tại: 150.0 m");
    expect(after).toContain("Sai số vượt ngưỡng.");
    expect(after).not.toContain("Sai số hiện tại: 12.0 m");
    expect(after).not.toContain("Sai số đạt yêu cầu chấm công.");
  });
});

describe("ageing readings", () => {
  it("is still fresh at exactly the staleness threshold", async () => {
    await renderPanel();

    await advance(STALE_AFTER_SECONDS * 1000);

    const card = positionRegion();
    expect(card).toHaveTextContent("Số liệu còn mới.");
    expect(card).not.toHaveTextContent("Số liệu đã cũ.");
  });

  it("marks the reading as ageing past the threshold without blocking anything", async () => {
    await renderPanel();

    await advance((STALE_AFTER_SECONDS + 1) * 1000);

    const card = positionRegion();
    expect(card).toHaveTextContent("Số liệu đã cũ.");
    expect(card).toHaveTextContent("Khi chấm công, hệ thống sẽ đọc lại vị trí mới.");
    expect(refreshButton()).not.toBeDisabled();
    expect(within(nearbyRegion()).getAllByRole("listitem")[0]).toHaveTextContent(NEAR);
  });
});
