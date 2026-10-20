import { describe, expect, it } from "vitest";
import { SAMPLE_WEDDING_PLAN } from "../data/sample-plans";
import { importPlanFromJSON } from "../lib/storage";

describe("Storage and Import Validation Tests", () => {
  it("successfully imports a valid serialized EventPlan", () => {
    const jsonStr = JSON.stringify(SAMPLE_WEDDING_PLAN);
    const result = importPlanFromJSON(jsonStr);

    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.plan.brief.title).toBe(SAMPLE_WEDDING_PLAN.brief.title);
      expect(result.plan.metadata.schemaVersion).toBe(1);
    }
  });

  it("rejects malformed non-JSON strings", () => {
    const result = importPlanFromJSON("not a valid json { broken");
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error).toContain("Malformed");
    }
  });

  it("rejects JSON missing mandatory fields", () => {
    const invalidObj = { brief: { title: "Incomplete" } };
    const result = importPlanFromJSON(JSON.stringify(invalidObj));

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error).toContain("Invalid plan schema");
    }
  });

  it("rejects unsupported schema versions", () => {
    const futurePlan = JSON.parse(JSON.stringify(SAMPLE_WEDDING_PLAN));
    futurePlan.metadata.schemaVersion = 99;

    const result = importPlanFromJSON(JSON.stringify(futurePlan));
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error).toContain("schema");
    }
  });

  it("rejects plans with corrupted budget math (reserve != 12%)", () => {
    const corruptPlan = JSON.parse(JSON.stringify(SAMPLE_WEDDING_PLAN));
    corruptPlan.budget.reserveMinor = 1; // Artificially corrupt reserve

    const result = importPlanFromJSON(JSON.stringify(corruptPlan));
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error).toContain("Corrupt budget math");
    }
  });
});
