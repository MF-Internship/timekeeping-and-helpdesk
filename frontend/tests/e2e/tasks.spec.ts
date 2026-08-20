import { expect, test, type Page, type Route } from "@playwright/test";

const activeUsers = [
  { id: 2, full_name: "Helpdesk An", username: "an", role: "HELPDESK", is_active: true },
  { id: 3, full_name: "Helpdesk Bình", username: "binh", role: "HELPDESK", is_active: true },
];
const locations = [{ id: 4, code: "HCM004", name: "Quận 1", is_active: true }];

function task(id: number, title: string, overrides: Record<string, unknown> = {}) {
  return {
    id,
    title,
    description: "Mô tả",
    created_by: { id: 1, full_name: "Quản lý" },
    assigned_date: "2026-08-19",
    status: "TODO",
    location: null,
    expected_location: "",
    assignees: [{ user: { id: 2, full_name: "Helpdesk An" }, assigned_at: "2026-08-18T08:00:00Z" }],
    completed_by: null,
    completed_at: null,
    completion_method: null,
    completion_note: null,
    block_reason: null,
    group: "OVERDUE",
    overdue_days: 1,
    ...overrides,
  };
}

function grouped(items: ReturnType<typeof task>[] = []) {
  return { business_date: "2026-08-20", overdue: items, today: [], upcoming: [], completed: [] };
}

type TaskMockOptions = {
  ambiguity?: boolean;
  detailUpdates?: Record<string, unknown>[];
};

async function mockTasks(
  page: Page,
  capabilities: string[],
  initial = grouped(),
  options: TaskMockOptions = {},
) {
  let projection = initial;
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (path === "/api/v1/auth/refresh")
      return json(route, { access: "e2e", must_change_password: false });
    if (path === "/api/v1/me/")
      return json(route, {
        id: 1,
        username: "actor",
        full_name: "Actor",
        role: "HELPDESK",
        is_active: true,
        must_change_password: false,
        phone: null,
        email: null,
        capabilities,
      });
    if (path === "/api/v1/users/")
      return json(route, { count: 2, next: null, previous: null, results: activeUsers });
    if (path === "/api/v1/locations/") return json(route, locations);
    if (path === "/api/v1/tasks/" && request.method() === "GET") return json(route, projection);
    if (path === "/api/v1/tasks/" && request.method() === "POST") {
      const created = task(9, "Công việc mới", {
        expected_location: request.postDataJSON().expected_location ?? "",
        assignees: (capabilities.includes("task.create.self")
          ? [{ id: 1, full_name: "Actor" }]
          : activeUsers
        ).map((user) => ({
          user: { id: user.id, full_name: user.full_name },
          assigned_at: "2026-08-20T08:00:00Z",
        })),
      });
      projection = grouped([created]);
      return json(route, created, 201);
    }
    if (/\/api\/v1\/tasks\/\d+\/$/.test(path) && request.method() === "DELETE") {
      projection = grouped();
      return route.fulfill({ status: 204 });
    }
    if (path.endsWith("/evidence-uploads"))
      return json(
        route,
        {
          upload_id: "00000000-0000-4000-8000-000000000001",
          upload_url: "https://storage.invalid/upload",
          headers: { "Content-Type": "image/jpeg" },
          expires_at: "2026-08-20T12:00:00Z",
        },
        201,
      );
    if (path.endsWith("/complete-field")) {
      const body = request.postDataJSON();
      if (options.ambiguity && body.selected_location_id === null) {
        const requestId = "00000000-0000-4000-8000-000000000002";
        const candidates = [{ id: 4, code: "HCM004", name: "Quận 1" }];
        return route.fulfill({
          status: 409,
          headers: { "Content-Type": "application/json", "X-Request-Id": requestId },
          json: {
            error: "LOCATION_CHOICE_REQUIRED",
            error_code: "LOCATION_CHOICE_REQUIRED",
            message: "Cần chọn địa điểm thực tế.",
            request_id: requestId,
            candidates,
            details: { candidates },
          },
        });
      }
      return json(route, {
        ...task(5, "Việc phát sinh", {
          status: "COMPLETED",
          completion_method: "FIELD_EVIDENCE",
          group: "COMPLETED",
          overdue_days: null,
        }),
        updates: [],
      });
    }
    if (path.endsWith("/complete-override"))
      return json(
        route,
        task(9, "Công việc mới", { status: "COMPLETED", group: "COMPLETED", overdue_days: null }),
      );
    if (path.endsWith("/status"))
      return json(route, task(5, "Việc phát sinh", { status: "IN_PROGRESS" }));
    if (/\/api\/v1\/tasks\/\d+\/photos\/\d+\/access$/.test(path))
      return json(route, {
        url: "https://storage.invalid/protected-photo",
        expires_at: "2026-08-20T12:00:00Z",
      });
    if (/\/api\/v1\/tasks\/\d+\/$/.test(path))
      return json(route, { ...task(5, "Việc phát sinh"), updates: options.detailUpdates ?? [] });
    return route.fulfill({ status: 404, json: { error_code: "NOT_FOUND" } });
  });
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, json: body });
}

test("Manager creates for multiple assignees and confirms override", async ({ page }) => {
  await mockTasks(page, [
    "task.view.self",
    "task.create.assign",
    "task.update.any",
    "task.complete.override",
  ]);
  await page.goto("/tasks");
  await page.getByLabel("Tiêu đề").fill("Công việc mới");
  await page.getByLabel("Ngày giao").fill("2026-08-20");
  await page.getByLabel("Nhân viên Helpdesk đang hoạt động").selectOption(["2", "3"]);
  const createRequest = page.waitForRequest(
    (request) => request.url().endsWith("/api/v1/tasks/") && request.method() === "POST",
  );
  await page.getByRole("button", { name: "Tạo công việc" }).click();
  expect((await createRequest).postDataJSON().assignee_ids).toEqual([2, 3]);
  const card = page.getByRole("region", { name: "Công việc mới" });
  await expect(card).toContainText("Helpdesk An, Helpdesk Bình");
  await card.getByRole("button", { name: "Hoàn thành" }).click();
  const overrideForm = card.getByRole("form", { name: "Hoàn thành Công việc mới" });
  await overrideForm.getByLabel("Ghi chú hoàn thành").fill("Đã kiểm tra");
  await overrideForm.getByLabel(/Xác nhận hoàn thành/).check();
  await overrideForm.getByRole("button", { name: "Hoàn thành" }).click();
});

test("mobile Tasks keeps Tasks and Attendance visible without page overflow", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 760 });
  await mockTasks(
    page,
    ["task.view.self", "attendance.view.self"],
    grouped([task(5, "Việc mobile")]),
  );
  await page.goto("/tasks");
  const navigation = page.getByRole("navigation", { name: "Điều hướng chính" });
  await expect(navigation.getByRole("link", { name: "Công việc" })).toBeVisible();
  await expect(navigation.getByRole("link", { name: "Chấm công" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
});

test("Helpdesk uploads evidence, captures GPS and sends an idempotency key", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["geolocation"], { origin: "http://127.0.0.1:3100" });
  await context.setGeolocation({ latitude: 10, longitude: 106, accuracy: 12 });
  await page.route("https://storage.invalid/upload", (route) => route.fulfill({ status: 200 }));
  await mockTasks(
    page,
    ["task.view.self", "task.complete.field"],
    grouped([task(5, "Việc phát sinh")]),
  );
  await page.goto("/tasks");
  const card = page.getByRole("region", { name: "Việc phát sinh" });
  await card.getByRole("button", { name: "Nộp minh chứng" }).click();
  await card.getByLabel("Ảnh minh chứng").setInputFiles({
    name: "proof.jpg",
    mimeType: "image/jpeg",
    buffer: Buffer.from("proof"),
  });
  const completion = page.waitForRequest((request) => request.url().endsWith("/complete-field"));
  await card.getByRole("button", { name: "Nộp minh chứng & hoàn thành" }).click();
  const request = await completion;
  expect(request.headers()["idempotency-key"]).toBeTruthy();
  expect(request.postDataJSON()).toMatchObject({
    upload_ids: ["00000000-0000-4000-8000-000000000001"],
    selected_location_id: null,
  });
});

test("Helpdesk resolves an overlapping location without uploading evidence twice", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["geolocation"], { origin: "http://127.0.0.1:3100" });
  await context.setGeolocation({ latitude: 10, longitude: 106, accuracy: 12 });
  let uploadCount = 0;
  await page.route("https://storage.invalid/upload", (route) => {
    uploadCount += 1;
    return route.fulfill({ status: 200 });
  });
  await mockTasks(
    page,
    ["task.view.self", "task.complete.field"],
    grouped([task(5, "Việc phát sinh")]),
    { ambiguity: true },
  );
  await page.goto("/tasks");
  const card = page.getByRole("region", { name: "Việc phát sinh" });
  await card.getByRole("button", { name: "Nộp minh chứng" }).click();
  await card.getByLabel("Ảnh minh chứng").setInputFiles({
    name: "proof.jpg",
    mimeType: "image/jpeg",
    buffer: Buffer.from("proof"),
  });
  const completionRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().endsWith("/complete-field")) {
      completionRequests.push(request.headers()["idempotency-key"]);
    }
  });
  await card.getByRole("button", { name: "Nộp minh chứng & hoàn thành" }).click();
  await card.getByLabel("Địa điểm thực tế").selectOption("4");
  const resolved = page.waitForRequest(
    (request) =>
      request.url().endsWith("/complete-field") &&
      request.postDataJSON().selected_location_id === 4,
  );
  await card.getByRole("button", { name: "Nộp minh chứng & hoàn thành" }).click();
  await resolved;
  expect(uploadCount).toBe(1);
  expect(completionRequests).toHaveLength(2);
  expect(completionRequests[0]).toBe(completionRequests[1]);
});

test("authorized task history opens evidence through the protected access endpoint", async ({
  page,
}) => {
  await mockTasks(page, ["task.view.self"], grouped([task(5, "Việc phát sinh")]), {
    detailUpdates: [
      {
        id: 11,
        status: "COMPLETED",
        actor: { id: 2, full_name: "Helpdesk An" },
        recorded_at: "2026-08-20T08:00:00Z",
        captured_at: "2026-08-20T07:59:59Z",
        captured_latitude: "10.0000000",
        captured_longitude: "106.0000000",
        accuracy_m: "12.00",
        gps_quality: "GOOD",
        resolution_method: "AUTO_SINGLE",
        actual_location_id: 4,
        actual_location: {
          id: 4,
          code: "SCHOOL-04",
          name: "Trường THCS Nguyễn Du",
          address: "Quận 1, TP.HCM",
          is_active: true,
        },
        location_candidates: [4],
        validation_result: "INSIDE",
        distance_m: "1.00",
        completion_method: "FIELD_EVIDENCE",
        completion_note: null,
        block_reason: null,
        note: null,
        photos: [{ id: 21, mime: "image/jpeg", size_bytes: 5 }],
      },
    ],
  });
  await page.goto("/tasks");
  await page
    .getByRole("region", { name: "Việc phát sinh" })
    .getByRole("button", { name: "Xem lịch sử" })
    .click();
  await expect(page.getByText(/Trường THCS Nguyễn Du — Quận 1, TP\.HCM/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Mở vị trí trên Google Maps" })).toHaveAttribute(
    "href",
    /query=10\.0000000,106\.0000000/,
  );
  const access = page.waitForRequest((request) => request.url().endsWith("/photos/21/access"));
  await page.getByRole("button", { name: "Xem ảnh 1" }).click();
  await access;
});

test("Helpdesk self-creates and changes status without assignment controls", async ({ page }) => {
  await mockTasks(
    page,
    ["task.view.self", "task.create.self", "task.update.self"],
    grouped([task(5, "Việc phát sinh")]),
  );
  await page.goto("/tasks");
  await expect(page.getByLabel("Nhân viên Helpdesk đang hoạt động")).toHaveCount(0);
  const card = page.getByRole("region", { name: "Việc phát sinh" });
  await card.getByRole("button", { name: "Đổi trạng thái" }).click();
  const statusForm = card.getByRole("form", { name: "Cập nhật trạng thái Việc phát sinh" });
  await statusForm.getByLabel("Trạng thái").selectOption("IN_PROGRESS");
  const statusRequest = page.waitForRequest((request) => request.url().endsWith("/status"));
  await statusForm.getByRole("button", { name: "Cập nhật trạng thái" }).click();
  await statusRequest;
});

test("Helpdesk creates an external-place task, sees reset fields, and soft deletes it", async ({
  page,
}) => {
  await mockTasks(page, [
    "task.view.self",
    "task.create.self",
    "task.update.self",
    "task.delete.self",
  ]);
  await page.goto("/tasks");
  await page.getByLabel("Tiêu đề").fill("Làm việc tại trường học");
  await page.getByLabel("Ngày giao").fill("2026-08-20");
  await page.getByLabel("Địa điểm dự kiến").fill("Trường THCS Nguyễn Du");
  const create = page.waitForRequest(
    (request) => request.url().endsWith("/api/v1/tasks/") && request.method() === "POST",
  );
  await page.getByRole("button", { name: "Tạo công việc" }).click();
  expect((await create).postDataJSON().expected_location).toBe("Trường THCS Nguyễn Du");
  await expect(page.getByLabel("Tiêu đề")).toHaveValue("");
  const card = page.getByRole("region", { name: "Công việc mới" });
  await card.getByRole("button", { name: "Xóa task tự tạo" }).click();
  const deleted = page.waitForRequest((request) => request.method() === "DELETE");
  await card.getByRole("button", { name: "Xác nhận xóa" }).click();
  await deleted;
});

test("Leader reads inactive history and server-owned rollover groups without controls", async ({
  page,
}) => {
  const historical = task(7, "Việc qua ngày", {
    assigned_date: "2099-01-01",
    assignees: [
      { user: { id: 88, full_name: "Nhân viên cũ" }, assigned_at: "2025-01-01T00:00:00Z" },
    ],
  });
  await mockTasks(page, ["task.view.self"], grouped([historical]));
  await page.goto("/tasks");
  const overdue = page.getByRole("region", { name: "Quá hạn" });
  await expect(overdue).toContainText("Việc qua ngày");
  await expect(overdue).toContainText("Nhân viên cũ");
  await expect(
    page.getByRole("button", { name: /Sửa nội dung|Đổi trạng thái|Hoàn thành/ }),
  ).toHaveCount(0);
});
