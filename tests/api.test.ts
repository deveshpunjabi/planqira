import { describe, expect, it } from "vitest";
import { GET as healthGet } from "../app/api/health/route";
import { POST as planPost } from "../app/api/plan/route";
import { POST as replanPost } from "../app/api/replan/route";
import { SAMPLE_WEDDING_BRIEF, SAMPLE_WEDDING_PLAN } from "../data/sample-plans";

describe("API Route Tests", () => {
  it("GET /api/health returns healthy configuration without leaking secrets", async () => {
    const res = await healthGet();
    expect(res.status).toBe(200);
    const data = await res.json();

    expect(data.status).toBe("ok");
    expect(data.app).toContain("UtsavAI");
    expect(data.aiConfig).toBeDefined();
    // Must never leak secret key value
    expect(data.aiConfig.apiKey).toBeUndefined();
    expect(typeof data.aiConfig.hasApiKey).toBe("boolean");
  });

  it("POST /api/plan rejects malformed or missing brief with 400", async () => {
    const req = new Request("http://localhost:3000/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ brief: { title: "" } }), // invalid brief
    });

    const res = await planPost(req as any);
    expect(res.status).toBe(400);
    const data = await res.json();
    expect(data.success).toBe(false);
  });

  it("POST /api/plan gracefully reports 503 when AI_ENABLED is false", async () => {
    // Ensure AI_ENABLED is false
    const oldEnabled = process.env.AI_ENABLED;
    process.env.AI_ENABLED = "false";

    const req = new Request("http://localhost:3000/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ brief: SAMPLE_WEDDING_BRIEF }),
    });

    const res = await planPost(req as any);
    expect(res.status).toBe(503);
    const data = await res.json();
    expect(data.success).toBe(false);
    expect(data.error).toContain("disabled");

    process.env.AI_ENABLED = oldEnabled;
  });

  it("POST /api/replan successfully generates Plan Rescue proposal", async () => {
    const req = new Request("http://localhost:3000/api/replan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        currentPlan: SAMPLE_WEDDING_PLAN,
        baseRevision: 1,
        action: "budget_cut_15",
      }),
    });

    const res = await replanPost(req as any);
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.success).toBe(true);
    expect(data.proposal.diffSummary.newTotalMinor).toBe(
      Math.round(SAMPLE_WEDDING_PLAN.budget.totalMinor * 0.85)
    );
  });

  it("POST /api/replan rejects invalid actions with 400", async () => {
    const req = new Request("http://localhost:3000/api/replan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        currentPlan: SAMPLE_WEDDING_PLAN,
        baseRevision: 1,
        action: "invalid_action_xyz",
      }),
    });

    const res = await replanPost(req as any);
    expect(res.status).toBe(400);
  });
});
