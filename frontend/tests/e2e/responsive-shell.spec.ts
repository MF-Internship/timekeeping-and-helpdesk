import { expect, test, type Page, type Route } from "@playwright/test";

const routes = [
  ["/tasks", "Quản lý công việc"],
  ["/attendance", "Chấm công"],
  ["/users", "Quản lý người dùng"],
  ["/locations", "Địa điểm"],
  ["/holidays", "Ngày nghỉ"],
  ["/config", "Cấu hình vận hành"],
  ["/operations/job-health", "Sức khỏe đối soát"],
  ["/change-password", "Đổi mật khẩu"],
] as const;

const allCapabilities = [
  "task.view.self", "attendance.view.self", "user.view", "location.view",
  "holiday.manage", "config.view", "operations.job_health.view",
];

async function mockShell(page: Page, role = "MANAGER", capabilities = allCapabilities) {
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/v1/auth/refresh") return json(route, { access: "e2e", must_change_password: false });
    if (path === "/api/v1/me/") return json(route, {
      id: 1, username: "actor", full_name: "Actor", role, is_active: true,
      must_change_password: false, phone: null, email: null, capabilities,
    });
    if (path === "/api/v1/tasks/") {
      return json(route, { business_date: "2026-08-20", overdue: [], today: [], upcoming: [], completed: [] });
    }
    return route.fulfill({ status: 404, json: { error_code: "NOT_FOUND" } });
  });
}

async function json(route: Route, body: unknown) {
  await route.fulfill({ status: 200, json: body });
}

for (const viewport of [{ width: 360, height: 760 }, { width: 1280, height: 900 }]) {
  test(`every authenticated route stays within ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await mockShell(page);
    for (const [path, title] of routes) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    }
  });
}

test("role navigation keeps permitted destinations and the two employee tabs visible", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 760 });
  await mockShell(page, "HELPDESK", ["task.view.self", "attendance.view.self"]);
  await page.goto("/tasks");
  const navigation = page.getByRole("navigation", { name: "Điều hướng chính" });
  await expect(navigation.getByRole("link", { name: "Công việc" })).toBeVisible();
  await expect(navigation.getByRole("link", { name: "Chấm công" })).toBeVisible();
  await expect(navigation.getByRole("link", { name: "Người dùng" })).toHaveCount(0);
  await expect(page.getByText("Nhân viên Helpdesk")).toBeVisible();
});
