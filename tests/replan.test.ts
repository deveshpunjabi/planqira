import { describe, expect, it } from "vitest";
import { SAMPLE_WEDDING_PLAN } from "../data/sample-plans";
import {
  applyProposal,
  generatePlanRescueProposal,
  restorePlanWithFreshRevision,
} from "../lib/diff";
import { EventPlan } from "../lib/schema";

describe("Plan Rescue Engine Tests", () => {
  it("calculates 15% budget cut consistently and balances budget", () => {
    const currentPlan: EventPlan = JSON.parse(JSON.stringify(SAMPLE_WEDDING_PLAN));
    const oldTotal = currentPlan.budget.totalMinor;

    const proposal = generatePlanRescueProposal(currentPlan, "budget_cut_15");
    const expectedNewTotal = Math.round(oldTotal * 0.85);

    expect(proposal.diffSummary.newTotalMinor).toBe(expectedNewTotal);
    expect(proposal.proposedPlan.budget.totalMinor).toBe(expectedNewTotal);

    // Sum of categories + reserve must equal new total
    const catSum = proposal.proposedPlan.budget.categories.reduce((a, b) => a + b.amountMinor, 0);
    expect(catSum + proposal.proposedPlan.budget.reserveMinor).toBe(expectedNewTotal);
    expect(proposal.tradeoffs.tradeoffs.length).toBe(3);
  });

  it("scales guest count by ceil(guests * 1.25) within fixed budget", () => {
    const currentPlan: EventPlan = JSON.parse(JSON.stringify(SAMPLE_WEDDING_PLAN));
    const oldGuests = currentPlan.brief.guestCount;
    const oldTotal = currentPlan.budget.totalMinor;

    const proposal = generatePlanRescueProposal(currentPlan, "guests_plus_25");
    const expectedGuests = Math.ceil(oldGuests * 1.25);

    expect(proposal.diffSummary.newGuestCount).toBe(expectedGuests);
    expect(proposal.proposedPlan.brief.guestCount).toBe(expectedGuests);
    expect(proposal.proposedPlan.budget.totalMinor).toBe(oldTotal);
  });

  it("safeguards locked category costs during budget squeeze", () => {
    const currentPlan: EventPlan = JSON.parse(JSON.stringify(SAMPLE_WEDDING_PLAN));
    // Lock the venue category
    const venueCat = currentPlan.budget.categories.find((c) => c.id === "cat-venue")!;
    venueCat.isLocked = true;
    const lockedAmount = venueCat.amountMinor;

    const proposal = generatePlanRescueProposal(currentPlan, "budget_cut_15");
    const proposedVenue = proposal.proposedPlan.budget.categories.find((c) => c.id === "cat-venue")!;

    expect(proposedVenue.isLocked).toBe(true);
    expect(proposedVenue.amountMinor).toBe(lockedAmount);
  });

  it("rejects applying a proposal if baseRevision does not match current plan revision (stale check)", () => {
    const currentPlan: EventPlan = JSON.parse(JSON.stringify(SAMPLE_WEDDING_PLAN));
    const proposal = generatePlanRescueProposal(currentPlan, "budget_cut_15");

    // Simulate user editing the plan locally, bumping revision to 2
    const mutatedPlan: EventPlan = {
      ...currentPlan,
      metadata: { ...currentPlan.metadata, revision: 2 },
    };

    const result = applyProposal(mutatedPlan, proposal);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error).toContain("stale");
    }
  });

  it("rejects applying an infeasible budget deficit proposal", () => {
    const currentPlan: EventPlan = JSON.parse(JSON.stringify(SAMPLE_WEDDING_PLAN));
    // Create an impossible situation: lock all categories at a total higher than new budget
    currentPlan.budget.categories = currentPlan.budget.categories.map((c) => ({
      ...c,
      isLocked: true,
      amountMinor: 20000000, // 6 * 200,000 = 12,000,000
    }));

    const proposal = generatePlanRescueProposal(currentPlan, "budget_cut_15");
    expect(proposal.tradeoffs.isFeasible).toBe(false);

    const result = applyProposal(currentPlan, proposal);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error).toContain("infeasible");
    }
  });

  it("applies proposal, increments revision, and preserves user task/vendor state by stable ID", () => {
    const currentPlan: EventPlan = JSON.parse(JSON.stringify(SAMPLE_WEDDING_PLAN));
    // User marked task 1 completed and added a vendor note
    currentPlan.timeline.preparationTasks[0].isCompleted = true;
    currentPlan.vendors[0].notes = "Agreed discount: 10% off";
    currentPlan.vendors[0].status = "booked";

    const proposal = generatePlanRescueProposal(currentPlan, "budget_cut_15");
    const result = applyProposal(currentPlan, proposal);

    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.updatedPlan.metadata.revision).toBe(currentPlan.metadata.revision + 1);
      // Preserved task completion
      expect(result.updatedPlan.timeline.preparationTasks[0].isCompleted).toBe(true);
      // Preserved vendor status and notes
      expect(result.updatedPlan.vendors[0].status).toBe("booked");
      expect(result.updatedPlan.vendors[0].notes).toBe("Agreed discount: 10% off");
    }
  });

  it("restores plan on Undo with a fresh monotonically increasing revision number", () => {
    const initialPlan: EventPlan = JSON.parse(JSON.stringify(SAMPLE_WEDDING_PLAN));
    initialPlan.metadata.revision = 2;

    const snapshotPlan: EventPlan = JSON.parse(JSON.stringify(SAMPLE_WEDDING_PLAN));
    snapshotPlan.metadata.revision = 1;
    snapshotPlan.brief.title = "Original Title";

    const restored = restorePlanWithFreshRevision(initialPlan.metadata.revision, snapshotPlan);

    expect(restored.metadata.revision).toBe(3); // 2 + 1
    expect(restored.brief.title).toBe("Original Title");
    expect(restored.metadata.source).toBe("locally-edited");
  });
});
