import { fireEvent, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getConfig, listLocations } from "@/features/locations/api/location-api";

import {
  directoryRow,
  mockGeolocation,
  mockReference,
  nearbyRegion,
  renderPanel,
  settle,
  type Sample,
} from "./panel-harness";

vi.mock("@/features/locations/api/location-api", () => ({
  listLocations: vi.fn(),
  getConfig: vi.fn(),
}));

const DIAGRAM = "Sơ đồ tương đối";
const YOU = "Vị trí của bạn";
const ACCURACY_LABEL = "Vòng sai số của thiết bị";
const DIAGNOSTIC_NOTE =
  "Vòng sai số chỉ mô tả chất lượng tín hiệu. Nó không nới rộng, không thu hẹp và không dịch chuyển vùng đăng ký.";

/** The scenario geometry: one target north of the position, and one beyond it. */
const TARGET_CODE = "A";
const OTHER_CODE = "B";
const TARGET_NORTH_M = 40;
const OTHER_NORTH_M = 80;
const RADIUS_M = 50;
const RADIUS_TEXT = "50.000";
const ACCURACY_M = 12;

/** Wide enough to prove the geofence circle ignores every one of them (T098). */
const ACCURACY_SWEEP = [0, 3, ACCURACY_M, 45, 200];

function sample(accuracyM: number): Sample {
  return { northM: 0, accuracyM, timestamp: Date.UTC(2026, 7, 19, 3, 0, 0) };
}

function diagramRegion(): HTMLElement {
  return screen.getByRole("region", { name: DIAGRAM });
}

function canvas(): SVGSVGElement {
  const element = diagramRegion().querySelector("svg");
  if (!element) throw new Error("the diagram drew no canvas");
  return element as unknown as SVGSVGElement;
}

function shape(name: string): Element {
  return screen.getByRole("img", { name });
}

/** A secondary marker is a control, because choosing it changes the focus. */
function secondaryMarker(code: string): Element {
  return screen.getByRole("button", { name: `Địa điểm gần khác: ${code}` });
}

function attribute(element: Element, name: string): number {
  return Number(element.getAttribute(name));
}

/** The centre of a marker, whichever primitive it happens to be drawn with. */
function centreOf(element: Element): { x: number; y: number } {
  if (element.tagName.toLowerCase() === "circle") {
    return { x: attribute(element, "cx"), y: attribute(element, "cy") };
  }
  return {
    x: attribute(element, "x") + attribute(element, "width") / 2,
    y: attribute(element, "y") + attribute(element, "height") / 2,
  };
}

/**
 * Metres per drawing unit, read back out of the printed scale bar rather than
 * from the component. Every metre claim below is therefore checked against what
 * the diagram itself states its scale to be (FR-027).
 */
function metresPerUnit(): number {
  const bar = canvas().querySelector("line");
  const legend = canvas().querySelector("text");
  if (!bar || !legend) throw new Error("the diagram stated no scale");
  const units = attribute(bar, "x2") - attribute(bar, "x1");
  const metres = Number(/([\d.]+) m/.exec(legend.textContent ?? "")?.[1]);
  return metres / units;
}

function viewport(): { width: number; height: number } {
  const [, , width, height] = (canvas().getAttribute("viewBox") ?? "").split(" ").map(Number);
  return { width, height };
}

function isOnCanvas(point: { x: number; y: number }): boolean {
  const { width, height } = viewport();
  return point.x >= 0 && point.x <= width && point.y >= 0 && point.y <= height;
}

async function renderDiagram(
  accuracyM = ACCURACY_M,
  rows = [directoryRow(TARGET_CODE, TARGET_NORTH_M, RADIUS_TEXT)],
) {
  await import("@/features/guidance/ui/SpatialDiagram");
  mockReference(rows);
  mockGeolocation(sample(accuracyM));
  await renderPanel();
  fireEvent.click(screen.getByText("Sơ đồ vị trí tương đối"));
  await settle();
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

/** Scenario K — the diagram says the same thing the readouts say (T096). */
describe("scenario K — position, target, and geofence at the stated scale", () => {
  it("draws both markers and a geofence circle of radius_m, inside the viewport", async () => {
    await renderDiagram();

    const you = shape(YOU);
    const target = shape(`Địa điểm đang xem trên sơ đồ: ${TARGET_CODE}`);
    const geofence = shape(`Vùng đăng ký của địa điểm đang xem: ${TARGET_CODE}`);

    expect(attribute(geofence, "r") * metresPerUnit()).toBeCloseTo(RADIUS_M, 0);
    expect(centreOf(geofence)).toEqual(centreOf(target));
    expect(isOnCanvas(centreOf(you))).toBe(true);
    expect(isOnCanvas(centreOf(target))).toBe(true);
  });

  it("prints the scale it drew at", async () => {
    await renderDiagram();

    expect(within(diagramRegion()).getByText(/Tỉ lệ: [\d.]+ m/)).toBeInTheDocument();
  });
});

/** Scenario L — the accuracy ring is a diagnostic, not a boundary (T097). */
describe("scenario L — the accuracy overlay", () => {
  it("rings the position at accuracy_m, distinctly from the geofence circle", async () => {
    await renderDiagram();

    const accuracy = shape(ACCURACY_LABEL);
    const geofence = shape(`Vùng đăng ký của địa điểm đang xem: ${TARGET_CODE}`);

    expect(attribute(accuracy, "r") * metresPerUnit()).toBeCloseTo(ACCURACY_M, 0);
    expect(centreOf(accuracy)).toEqual(centreOf(shape(YOU)));
    expect(accuracy.getAttribute("stroke-dasharray")).toBeTruthy();
    expect(geofence.getAttribute("stroke-dasharray")).toBeNull();
  });

  it("says out loud that it is diagnostic only", async () => {
    await renderDiagram();

    const entry = within(diagramRegion()).getByText(
      (_, element) =>
        element?.tagName === "LI" && (element.textContent ?? "").includes(DIAGNOSTIC_NOTE),
    );

    expect(entry).toHaveTextContent(ACCURACY_LABEL);
  });
});

/**
 * The geofence is the registered radius and nothing else. Accuracy is a
 * separate quantity drawn separately, and no arithmetic anywhere lets one move
 * the other (T098, FR-016).
 */
describe("the geofence circle is invariant under accuracy", () => {
  it.each(ACCURACY_SWEEP)(
    "stays at radius_m and on the target with accuracy_m = %s",
    async (accuracyM) => {
      await renderDiagram(accuracyM);

      const geofence = shape(`Vùng đăng ký của địa điểm đang xem: ${TARGET_CODE}`);
      const target = shape(`Địa điểm đang xem trên sơ đồ: ${TARGET_CODE}`);

      expect(attribute(geofence, "r") * metresPerUnit()).toBeCloseTo(RADIUS_M, 0);
      expect(centreOf(geofence)).toEqual(centreOf(target));
    },
  );
});

/** The diagram is drawn, not fetched (T099, SC-005). */
describe("the diagram issues no external request", () => {
  it("renders without fetching and without any external resource element", async () => {
    const fetched = vi.spyOn(globalThis, "fetch");
    await renderDiagram();

    expect(fetched).not.toHaveBeenCalled();
    const region = diagramRegion();
    expect(
      region.querySelectorAll("img, iframe, link, script, image, use, foreignObject"),
    ).toHaveLength(0);
    expect(
      region.querySelectorAll("[src], [href], [xlink\\:href], [font-family], [style]"),
    ).toHaveLength(0);
  });
});

/** Choosing from the diagram is choosing from the list (T100, T092). */
describe("selecting a secondary marker", () => {
  async function renderPair() {
    await renderDiagram(ACCURACY_M, [
      directoryRow(TARGET_CODE, TARGET_NORTH_M, RADIUS_TEXT),
      directoryRow(OTHER_CODE, OTHER_NORTH_M, RADIUS_TEXT),
    ]);
  }

  it("re-fits the bounds to the newly focused target", async () => {
    await renderPair();
    const before = metresPerUnit();

    fireEvent.click(secondaryMarker(OTHER_CODE));

    expect(shape(`Địa điểm đang xem trên sơ đồ: ${OTHER_CODE}`)).toBeInTheDocument();
    expect(metresPerUnit()).not.toBeCloseTo(before, 3);
    expect(
      attribute(shape(`Vùng đăng ký của địa điểm đang xem: ${OTHER_CODE}`), "r") * metresPerUnit(),
    ).toBeCloseTo(RADIUS_M, 0);
  });

  it("changes display state and nothing else", async () => {
    await renderPair();
    const rowsBefore = within(nearbyRegion())
      .getAllByRole("listitem")
      .map((row) => row.textContent);
    const reads =
      vi.mocked(listLocations).mock.calls.length + vi.mocked(getConfig).mock.calls.length;

    fireEvent.click(secondaryMarker(OTHER_CODE));

    expect(screen.getByRole("radio", { name: new RegExp(OTHER_CODE) })).toBeChecked();
    expect(
      within(nearbyRegion())
        .getAllByRole("listitem")
        .map((row) => row.textContent),
    ).toEqual(rowsBefore);
    expect(
      vi.mocked(listLocations).mock.calls.length + vi.mocked(getConfig).mock.calls.length,
    ).toBe(reads);
  });
});
