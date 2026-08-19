import { screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { classifyGeofence } from "@/features/guidance/model/geofence";

import {
  CAPTURED_AT,
  MAX_ACCURACY_M,
  directoryRow,
  mockGeolocation,
  mockReference,
  nearbyRegion,
  positionRegion,
  renderPanel,
} from "./panel-harness";

vi.mock("@/features/locations/api/location-api", () => ({
  listLocations: vi.fn(),
  getConfig: vi.fn(),
}));

const NEAR = "HCM000012";
const FAR = "HCM000079";

let device: ReturnType<typeof mockGeolocation>;

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(CAPTURED_AT);
  device = mockGeolocation();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("scenario B — accurate reading outside every nearby Location", () => {
  /** Both radii are 50 m, so a reading at the origin is inside neither. */
  beforeEach(() => {
    mockReference([directoryRow(FAR, 900), directoryRow(NEAR, 200)]);
  });

  it("reports an outside-all status", async () => {
    await renderPanel();

    expect(screen.getByText("Bạn đang ở ngoài vùng của mọi địa điểm gần đây.")).toBeInTheDocument();
  });

  it("identifies the nearest Location", async () => {
    await renderPanel();

    const [first] = within(nearbyRegion()).getAllByRole("listitem");
    expect(first).toHaveTextContent(NEAR);
    expect(first).toHaveTextContent("(Gần nhất)");
    expect(first).toHaveTextContent("Ngoài vùng");
  });

  it("shows the remaining distance to that boundary as a labelled estimate", async () => {
    await renderPanel();

    const region = nearbyRegion();
    const [first] = within(region).getAllByRole("listitem");
    expect(first).toHaveTextContent("Còn cách ranh giới: 150.0 m (giá trị ước tính để tham khảo)");
    expect(region).toHaveTextContent(
      "Khoảng cách tới ranh giới là ước tính để tham khảo, không phải quy tắc chấp nhận chấm công.",
    );
  });
});

/**
 * Geofence membership and measurement quality are two separate gates that share
 * no input: neither threshold moves when the other one is crossed (SC-006).
 */
describe("two-gate independence", () => {
  const ACCURACIES = [0, MAX_ACCURACY_M - 0.001, MAX_ACCURACY_M, MAX_ACCURACY_M + 0.001, 5000];

  it("flips membership exactly at distance_m = radius_m", () => {
    expect(classifyGeofence(50, 50)).toBe("INSIDE_GEOFENCE");
    expect(classifyGeofence(50.0001, 50)).toBe("OUTSIDE_GEOFENCE");
  });

  it.each(ACCURACIES)(
    "renders the same membership verdicts at accuracy_m = %s",
    async (accuracyM) => {
      mockReference([directoryRow(FAR, 900), directoryRow(NEAR, 10)]);
      device.nextSample({ northM: 0, accuracyM, timestamp: CAPTURED_AT });

      await renderPanel();

      const [first, second] = within(nearbyRegion()).getAllByRole("listitem");
      expect(first).toHaveTextContent(NEAR);
      expect(first).toHaveTextContent("Trong vùng");
      expect(second).toHaveTextContent(FAR);
      expect(second).toHaveTextContent("Ngoài vùng");
      expect(
        screen.getByText("Bạn đang ở trong vùng của đúng một địa điểm đã đăng ký."),
      ).toBeInTheDocument();
    },
  );

  it.each(ACCURACIES)("flips the accuracy verdict alone at accuracy_m = %s", async (accuracyM) => {
    mockReference([directoryRow(FAR, 900), directoryRow(NEAR, 10)]);
    device.nextSample({ northM: 0, accuracyM, timestamp: CAPTURED_AT });

    await renderPanel();

    const card = positionRegion();
    const sufficient = accuracyM <= MAX_ACCURACY_M;
    expect(card).toHaveTextContent(
      sufficient ? "Sai số đạt yêu cầu chấm công." : "Sai số vượt ngưỡng.",
    );
    expect(card).not.toHaveTextContent(
      sufficient ? "Sai số vượt ngưỡng." : "Sai số đạt yêu cầu chấm công.",
    );
  });
});
