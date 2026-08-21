import { expect, test, type Page, type Route } from "@playwright/test";

const routes = [
  ["/", "Trang chủ"],
  ["/tasks", "Quản lý công việc"],
  ["/attendance", "Chấm công"],
  ["/notifications", "Thông báo"],
  ["/reports", "Báo cáo"],
  ["/users", "Quản lý người dùng"],
  ["/locations", "Địa điểm"],
  ["/holidays", "Ngày nghỉ"],
  ["/config", "Cấu hình vận hành"],
  ["/operations/job-health", "Sức khỏe đối soát"],
  ["/change-password", "Đổi mật khẩu"],
  ["/account", "Tài khoản"],
] as const;

const allCapabilities = [
  "task.view.self",
  "attendance.view.self",
  "user.view",
  "location.view",
  "holiday.manage",
  "config.view",
  "operations.job_health.view",
  "notification.view.self",
  "report.view.self",
  "report.export",
];

async function mockShell(page: Page, role = "MANAGER", capabilities = allCapabilities) {
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/v1/auth/refresh")
      return json(route, { access: "e2e", must_change_password: false });
    if (path === "/api/v1/me/")
      return json(route, {
        id: 1,
        username: "actor",
        full_name: "Actor",
        role,
        is_active: true,
        must_change_password: false,
        phone: null,
        email: null,
        capabilities,
      });
    if (path === "/api/v1/tasks/") {
      return json(route, {
        business_date: "2026-08-20",
        overdue: [],
        today: [],
        upcoming: [],
        completed: [],
      });
    }
    if (path === "/api/v1/attendance/today")
      return json(route, {
        punches: [],
        sessions: [],
        total_duration_minutes: "0.000000",
        has_open_session: false,
      });
    if (path === "/api/v1/notifications/") return json(route, { items: [], unread_count: 0 });
    if (path === "/api/v1/reports/attendance/")
      return json(route, {
        users_in_open_session: 0,
        users_no_check_in_today: 0,
        users_checked_out_today: 0,
        punch_count: 0,
        total_valid_worked_minutes: 0,
        system_closed_missing_checkout_sessions: 0,
        anomaly_counts: {},
        attempt_counts: {},
        rejected_attempt_diagnostics: {},
        nearest_location_diagnostics: {},
        failure_rate: { numerator: 0, denominator: 0, excluded_count: 0, rate_percent: 0 },
      });
    if (path === "/api/v1/reports/tasks/")
      return json(route, {
        total_tasks: 0,
        status_counts: {},
        completion_method_counts: {},
        gps_quality_counts: {},
        actual_completer_counts: {},
        assigned_task_closed_count: 0,
      });
    if (path === "/api/v1/operations/job-health")
      return json(route, {
        state: "ok",
        refreshed_at: "2026-08-21T08:00:00Z",
        overdue_open_session_count: 0,
        evidence_counts: { job_closed_session_count: 0, missing_checkout_anomaly_count: 0 },
      });
    return route.fulfill({ status: 404, json: { error_code: "NOT_FOUND" } });
  });
}

async function json(route: Route, body: unknown) {
  await route.fulfill({ status: 200, json: body });
}

for (const viewport of [
  { width: 320, height: 720 },
  { width: 768, height: 1024 },
  { width: 1440, height: 1000 },
]) {
  test(`every authenticated route stays within ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await mockShell(page);
    for (const [path, title] of routes) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
      ).toBe(true);
    }
  });
}

for (const viewport of [
  { width: 375, height: 812 },
  { width: 430, height: 932 },
  { width: 1280, height: 900 },
]) {
  test(`primary workflows stay within ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await mockShell(page);
    for (const path of ["/", "/tasks", "/attendance", "/notifications", "/reports", "/account"]) {
      await page.goto(path);
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
      ).toBe(true);
    }
  });
}

test("role navigation keeps permitted destinations and the two employee tabs visible", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 760 });
  await mockShell(page, "HELPDESK", ["task.view.self", "attendance.view.self"]);
  await page.goto("/tasks");
  const navigation = page.getByRole("navigation", { name: "Điều hướng chính" });
  await expect(navigation.getByRole("link", { name: "Công việc" })).toBeVisible();
  await expect(navigation.getByRole("link", { name: "Chấm công" })).toBeVisible();
  await expect(navigation.getByRole("link", { name: "Người dùng" })).toHaveCount(0);
  await page.getByRole("button", { name: "Mở menu tài khoản của Actor" }).click();
  await expect(page.getByText("Nhân viên Helpdesk")).toBeVisible();
});
