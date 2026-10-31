import { describe, expect, it } from "vitest";

import { fromDateTimeLocal, toDateTimeLocal } from "@/lib/format";

// vitest.config.ts pins TZ=Asia/Kolkata (UTC+05:30), so a conversion that ignored the
// zone would be off by five and a half hours here and fail.
describe("datetime-local conversion", () => {
  it("shows an API timestamp in the browser's zone at minute precision", () => {
    expect(toDateTimeLocal("2027-03-01T05:00:42Z")).toBe("2027-03-01T10:30");
  });

  it("shows nothing for a missing or unreadable timestamp", () => {
    expect(toDateTimeLocal(null)).toBe("");
    expect(toDateTimeLocal("not a date")).toBe("");
  });

  it("reads an input value in the browser's zone and sends UTC", () => {
    expect(fromDateTimeLocal("2027-03-01T10:30")).toBe("2027-03-01T05:00:00.000Z");
  });
});
