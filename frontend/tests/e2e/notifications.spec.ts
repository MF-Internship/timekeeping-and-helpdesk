import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";

const reference = "00000000-0000-4000-8000-000000000008";

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, json: body });
}

async function mockNotifications(page: Page, staleTarget = false) {
  let unread = true;
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path === "/api/v1/auth/refresh")
      return json(route, { access: "e2e", must_change_password: false });
    if (path === "/api/v1/me/")
      return json(route, {
        id: 1,
        username: "actor",
        full_name: "Người dùng thử",
        role: "HELPDESK",
        is_active: true,
        must_change_password: false,
        phone: null,
        email: null,
        capabilities: ["notification.view.self", "task.view.self"],
      });
    if (path === "/api/v1/notifications/")
      return json(route, {
        items: [
          {
            public_id: reference,
            event_type: "TASK_ASSIGNED",
            title: "Bạn có công việc mới được giao",
            created_at: "2026-08-21T03:00:00Z",
            read_at: unread ? null : "2026-08-21T03:01:00Z",
            is_unread: unread,
          },
        ],
        unread_count: unread ? 1 : 0,
      });
    if (path.endsWith(`/${reference}/read`)) {
      unread = false;
      return json(route, {
        public_id: reference,
        event_type: "TASK_ASSIGNED",
        title: "Bạn có công việc mới được giao",
        created_at: "2026-08-21T03:00:00Z",
        read_at: "2026-08-21T03:01:00Z",
        is_unread: false,
      });
    }
    if (path.endsWith(`/${reference}/target`)) {
      if (staleTarget) return json(route, { error_code: "NOT_FOUND" }, 404);
      return json(route, { destination: "TASK", target_id: 42 });
    }
    return json(route, { error_code: "NOT_FOUND" }, 404);
  });
}

test("in-app inbox remains usable on mobile and marks unread as read", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 760 });
  await mockNotifications(page);
  await page.goto("/notifications");

  await expect(page.getByRole("heading", { name: "Thông báo" })).toBeVisible();
  await expect(page.getByText("1 chưa đọc")).toBeVisible();
  await page.getByRole("button", { name: "Đánh dấu đã đọc" }).click();
  await expect(page.getByText("Đã đọc", { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);

  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("safe notification link resolves through current authorization", async ({ page }) => {
  await mockNotifications(page);
  const targetRequest = page.waitForRequest((request) =>
    request.url().endsWith(`/${reference}/target`),
  );
  await page.goto(`/notifications/open/${reference}`);
  await targetRequest;
  await expect(page).toHaveURL(/\/tasks\?focus=42$/);
});

test("stale notification link fails closed without exposing a target", async ({ page }) => {
  await mockNotifications(page, true);
  await page.goto(`/notifications/open/${reference}`);
  await expect(page.locator("section[role='alert']")).toContainText("không còn quyền truy cập");
  await expect(page).toHaveURL(new RegExp(`/notifications/open/${reference}$`));
});
