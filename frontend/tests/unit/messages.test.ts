import { describe, expect, it } from "vitest";

import { UI_MESSAGES } from "@/shared/messages";

describe("centralized foundation messages", () => {
  it("owns one non-empty string per shared state", () => {
    expect(Object.keys(UI_MESSAGES).sort()).toEqual([
      "accountInactive",
      "empty",
      "invalidCredentials",
      "invalidToken",
      "loading",
      "networkFailure",
      "passwordChangeRequired",
      "permissionDenied",
      "retry",
      "serverOwnedField",
      "serviceUnavailable",
      "throttled",
      "unexpectedResponse",
      "validationFailed",
    ]);
    expect(new Set(Object.values(UI_MESSAGES)).size).toBe(Object.values(UI_MESSAGES).length);
  });
});
