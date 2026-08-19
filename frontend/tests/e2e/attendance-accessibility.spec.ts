import AxeBuilder from "@axe-core/playwright";

import { test, expect } from "./fixtures/attendance";

test("Attendance has no automatically detectable accessibility violations", async ({
  attendancePage: page,
}) => {
  await page.getByRole("button", { name: "Xem vị trí" }).click();
  await expect(page.getByText("GPS đạt yêu cầu")).toBeVisible();
  await page.getByText("Sơ đồ vị trí tương đối").click();
  await expect(page.getByRole("region", { name: "Sơ đồ tương đối" })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("controls have keyboard semantics, visible focus, and comfortable targets", async ({
  attendancePage: page,
}) => {
  await page.keyboard.press("Tab");
  const focused = page.locator(":focus");
  await expect(focused).toBeVisible();
  const targets = await page.locator("button, a, input, summary").evaluateAll((nodes) =>
    nodes
      .filter((node) => {
        const style = getComputedStyle(node);
        return style.display !== "none" && style.visibility !== "hidden";
      })
      .map((node) => ({
        width: node.getBoundingClientRect().width,
        height: node.getBoundingClientRect().height,
        text: node.getAttribute("aria-label") || node.textContent,
        visible: node.getClientRects().length > 0 && node.getBoundingClientRect().width > 0,
      })),
  );
  expect(
    targets.filter(
      (target) =>
        target.visible &&
        target.text?.trim() &&
        target.text !== "Open Next.js Dev Tools" &&
        target.height < 44 &&
        target.width < 44,
    ),
  ).toEqual([]);
});

test("reduced motion is honored and map information remains textual", async ({
  attendancePage: page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.getByRole("button", { name: "Xem vị trí" }).click();
  await expect(page.getByRole("region", { name: "Địa điểm gần bạn" })).toContainText(
    "Cửa hàng Quận 1",
  );
  const duration = await page
    .getByRole("button", { name: "Check In" })
    .evaluate((node) => getComputedStyle(node).transitionDuration);
  expect(["0s", "0.00001s", "1e-05s"]).toContain(duration);
});
