import { test, expect } from "./fixtures/attendance";

test("shell exposes only implemented and permitted navigation", async ({
  attendancePage: page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const logo = page.getByRole("img", { name: "MobiFone" });
  await expect(logo).toBeVisible();
  await expect
    .poll(() => logo.evaluate((image: HTMLImageElement) => image.currentSrc))
    .toContain("logo-phone.jpg");
  const navigation = page.getByRole("navigation", { name: "Điều hướng chính" }).first();
  await expect(navigation.getByRole("link", { name: "Attendance" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await expect(navigation.getByText(/Tasks|Reports|Account/)).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Tài khoản của Nguyễn Văn An" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Đăng xuất" })).toBeVisible();
});

test("bottom navigation and rail are responsive views of the same registry", async ({
  attendancePage: page,
}) => {
  const bottom = page.locator('[data-navigation="bottom"]');
  const rail = page.locator('[data-navigation="rail"]');
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(bottom).toBeVisible();
  await expect(rail).toBeHidden();
  await page.setViewportSize({ width: 768, height: 1024 });
  await expect
    .poll(() =>
      page
        .getByRole("img", { name: "MobiFone" })
        .evaluate((image: HTMLImageElement) => image.currentSrc),
    )
    .toContain("logo-desktop.png");
  await expect(bottom).toBeHidden();
  await expect(rail).toBeVisible();
});
