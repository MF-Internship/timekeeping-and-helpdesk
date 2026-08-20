import { test, expect } from "./fixtures/attendance";

const VIEWPORTS = [
  { width: 320, height: 640 },
  { width: 375, height: 667 },
  { width: 390, height: 844 },
  { width: 430, height: 932 },
  { width: 768, height: 1024 },
  { width: 1280, height: 800 },
  { width: 1440, height: 900 },
];

for (const viewport of VIEWPORTS) {
  test(`${viewport.width}px keeps the field action usable`, async ({ attendancePage: page }) => {
    await page.setViewportSize(viewport);
    const action = page.getByRole("button", { name: "Check In" });
    await action.scrollIntoViewIfNeeded();
    await expect(action).toBeInViewport();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    ).toBe(true);
    const map = page.getByText("Sơ đồ vị trí tương đối").locator("..");
    await expect(map).not.toHaveAttribute("open", "");
    await expect(
      page.locator(
        viewport.width < 768 ? '[data-navigation="bottom"]' : '[data-navigation="rail"]',
      ),
    ).toBeVisible();
  });
}

test("spatial guidance stays secondary and usable after disclosure", async ({
  attendancePage: page,
}) => {
  await page.setViewportSize({ width: 320, height: 640 });
  await page.getByRole("button", { name: "Xem vị trí" }).click();
  await expect(page.getByText("GPS đạt yêu cầu")).toBeVisible();
  await page.getByText("Sơ đồ vị trí tương đối").click();
  await expect(page.getByRole("region", { name: "Sơ đồ tương đối" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
});
