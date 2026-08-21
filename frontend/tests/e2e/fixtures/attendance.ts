import { expect, test as base, type Page } from "@playwright/test";

const account = {
  id: 1,
  username: "field.employee",
  full_name: "Nguyễn Văn An",
  phone: null,
  email: null,
  role: "HELPDESK",
  is_active: true,
  must_change_password: false,
  capabilities: ["attendance.view.self", "attendance.check_in.self", "attendance.check_out.self"],
};
const today = {
  work_date: "2026-08-20",
  punches: [],
  sessions: [],
  total_duration_minutes: "0.000000",
  has_open_session: false,
};
const locations = [
  {
    id: 1,
    code: "HCM001",
    name: "Cửa hàng Quận 1",
    address: "1 Nguyễn Huệ, Quận 1, Thành phố Hồ Chí Minh",
    latitude: "10.000000000000000",
    longitude: "106.000000000000000",
    radius_m: "50.000",
    is_active: true,
    kind: "SHOP",
  },
  {
    id: 2,
    code: "HCM002",
    name: "Cửa hàng Quận 3",
    address: "Địa chỉ thử nghiệm đủ dài để kiểm tra xuống dòng trên màn hình nhỏ",
    latitude: "10.001000000000000",
    longitude: "106.000000000000000",
    radius_m: "50.000",
    is_active: true,
    kind: "SHOP",
  },
];
const config = {
  max_attendance_accuracy_m: "25.000",
  default_radius_m: "50.000",
  max_radius_m: "100.000",
};

async function mockApi(page: Page) {
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/v1/auth/refresh")
      return route.fulfill({ json: { access: "e2e-access", must_change_password: false } });
    if (path === "/api/v1/me/") return route.fulfill({ json: account });
    if (path === "/api/v1/attendance/today") return route.fulfill({ json: today });
    if (path === "/api/v1/locations/") return route.fulfill({ json: locations });
    if (path === "/api/v1/config/") return route.fulfill({ json: config });
    if (path.includes("/api/v1/attendance/check-"))
      return route.fulfill({ json: { status: "ACCEPTED" } });
    if (path === "/api/v1/auth/logout") return route.fulfill({ status: 204 });
    return route.fulfill({ status: 404, json: { error_code: "NOT_FOUND" } });
  });
}

type Fixtures = { attendancePage: Page };

export const test = base.extend<Fixtures>({
  attendancePage: async ({ page, context }, fixtureUse) => {
    await context.grantPermissions(["geolocation"], { origin: "http://127.0.0.1:3100" });
    await context.setGeolocation({ latitude: 10, longitude: 106, accuracy: 14 });
    await mockApi(page);
    await page.goto("/attendance");
    await expect(page.getByRole("button", { name: "Check In" })).toBeVisible();
    await fixtureUse(page);
  },
});

export { expect };
