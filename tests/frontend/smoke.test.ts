/**
 * Frontend Baseline Smoke Check
 * Verifies key domain types and utility functions
 */
import { formatBytes, formatDate } from "../../frontend/lib/utils";

describe("Frontend Utilities Smoke Tests", () => {
  it("formats file sizes correctly for clinical document displays", () => {
    expect(formatBytes(0)).toBe("0 Bytes");
    expect(formatBytes(1024)).toBe("1 KB");
    expect(formatBytes(1048576)).toBe("1 MB");
  });

  it("handles empty date strings gracefully", () => {
    expect(formatDate(undefined)).toBe("N/A");
  });
});
