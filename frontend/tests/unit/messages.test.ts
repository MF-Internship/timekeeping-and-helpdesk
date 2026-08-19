import { describe, expect, it } from "vitest";

import { UI_MESSAGES } from "@/shared/messages";

/** The shared states every feature reuses, each owning exactly one string. */
const FOUNDATION_KEYS = [
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
];

/** Feature-scoped vocabularies live in their own nested group, never inline. */
const GROUP_KEYS = ["guidance"];

const entries = Object.entries(UI_MESSAGES);
const flat = entries.filter(([, value]) => typeof value === "string") as [string, string][];
const groups = entries.filter(([, value]) => typeof value !== "string");

/** Every leaf of a nested group, flattened for the emptiness check. */
function leaves(value: unknown): string[] {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.flatMap(leaves);
  if (typeof value === "object" && value !== null) return Object.values(value).flatMap(leaves);
  return [];
}

describe("centralized foundation messages", () => {
  it("owns one non-empty string per shared state", () => {
    expect(flat.map(([key]) => key).sort()).toEqual([...FOUNDATION_KEYS].sort());
    expect(flat.every(([, value]) => value.length > 0)).toBe(true);
    expect(new Set(flat.map(([, value]) => value)).size).toBe(flat.length);
  });

  it("keeps feature vocabularies in named groups beside the shared states", () => {
    expect(groups.map(([key]) => key).sort()).toEqual([...GROUP_KEYS].sort());
  });

  it("holds no empty string anywhere in a group", () => {
    const grouped = groups.flatMap(([, value]) => leaves(value));

    expect(grouped.length).toBeGreaterThan(0);
    expect(grouped.every((value) => value.trim().length > 0)).toBe(true);
  });
});
