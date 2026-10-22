import { describe, expect, it } from "vitest";

import { formatDate, formatSalary } from "./format.js";

describe("formatSalary", () => {
  it("shows a range", () => expect(formatSalary(100000, 120000)).toBe("$100,000 – $120,000"));
  it("handles one side missing", () => {
    expect(formatSalary(90000, null)).toBe("From $90,000");
    expect(formatSalary(null, 90000)).toBe("Up to $90,000");
  });
  it("returns null when there's no salary", () => expect(formatSalary(null, null)).toBeNull());
});

describe("formatDate", () => {
  it("doesn't shift the day across time zones", () => expect(formatDate("2026-03-01")).toBe("Mar 1, 2026"));
  it("returns null for empty dates", () => expect(formatDate(null)).toBeNull());
});
