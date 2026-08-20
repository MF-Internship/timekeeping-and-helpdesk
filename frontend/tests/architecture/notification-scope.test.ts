import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("notification scope", () => {
  it("contains exactly five closed Web Push event hints and no alternate channel", () => {
    const source = readFileSync(
      resolve("src/features/notifications/api/notification-api.ts"),
      "utf8",
    );
    const events = source.match(
      /"(?:TASK_ASSIGNED|TASK_UPCOMING|TASK_OVERDUE|ATTENDANCE_SESSION_OPEN_NEAR_SHIFT_END|MULTI_ASSIGNEE_TASK_COMPLETED)"/g,
    );
    expect(new Set(events)).toHaveLength(5);
    expect(source).not.toMatch(/email|sms|websocket|eventsource|celery|redis/i);
  });
});
