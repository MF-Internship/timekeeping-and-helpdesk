import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";

async function json(route: Route, body: unknown) {
  await route.fulfill({ status: 200, json: body });
}

async function mockHome(page: Page) {
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/v1/auth/refresh")
      return json(route, { access: "e2e", must_change_password: false });
    if (path === "/api/v1/me/")
      return json(route, {
        id: 1,
        username: "helpdesk",
        full_name: "Nguyễn An",
        role: "HELPDESK",
        is_active: true,
        must_change_password: false,
        phone: null,
        email: null,
        capabilities: ["attendance.view.self", "task.view.self", "notification.view.self"],
      });
    if (path === "/api/v1/attendance/today")
      return json(route, {
        punches: [],
        sessions: [],
        total_duration_minutes: "0.000000",
        has_open_session: false,
      });
    if (path === "/api/v1/tasks/")
      return json(route, { overdue: [], today: [], upcoming: [], completed: [] });
    if (path === "/api/v1/notifications/") return json(route, { items: [], unread_count: 0 });
    return route.fulfill({ status: 404, json: { error_code: "NOT_FOUND" } });
  });
}

test("Home shell has no serious accessibility violations and supports keyboard menus", async ({
  page,
}) => {
  await mockHome(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Trang chủ" })).toBeVisible();
  await page.getByRole("button", { name: "Mở menu tài khoản của Nguyễn An" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("menuitem", { name: "Tài khoản" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("menuitem", { name: "Tài khoản" })).toBeHidden();
  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations.filter((violation) =>
      ["serious", "critical"].includes(violation.impact ?? ""),
    ),
  ).toEqual([]);
});
