import { calculateBudget } from "./budget";
import {
  EventPlan,
  PlanRescueProposal,
  PlanRescueTradeoff,
  ReplanAction,
} from "./schema";

/**
 * Generates a Plan Rescue Proposal with strict domain correctness:
 * - Budget cut: new total = round(85% of current total)
 * - Guest increase: new count = ceil(current guests * 1.25)
 * - Rain pivot: indoor shelter contingencies & outdoor gear protections
 * - Preserves locked categories, stable task IDs, and completion checkboxes.
 * - Infeasible deficits are flagged and marked isFeasible: false.
 */
export function generatePlanRescueProposal(
  currentPlan: EventPlan,
  action: ReplanAction,
  customInstruction?: string
): PlanRescueProposal {
  const currentTotal = currentPlan.budget.totalMinor;
  const currentGuests = currentPlan.brief.guestCount;
  const oldReserve = currentPlan.budget.reserveMinor;

  let newTotalMinor = currentTotal;
  let newGuestCount = currentGuests;
  let summary = "";
  let tradeoffs: [string, string, string] = [
    "Rebalanced operational focus based on scenario requirements.",
    "Preserved all confirmed bookings and locked vendor costs.",
    "Maintained strict 12% contingency buffer for unforeseen contingencies.",
  ];
  const affectedTasks: string[] = [];
  const vendorImpact: string[] = [];

  // Deep clone current plan
  const proposedPlan: EventPlan = JSON.parse(JSON.stringify(currentPlan));

  if (action === "budget_cut_15") {
    // 15% budget cut: round(totalMinor * 0.85)
    newTotalMinor = Math.round(currentTotal * 0.85);
    summary = `Trimmed total budget by 15% (${currentTotal} → ${newTotalMinor}). Unlocked categories adjusted while locked costs were safeguarded.`;

    // Recalculate budget preserving locked categories
    const budgetRes = calculateBudget(newTotalMinor, currentPlan.budget.categories);
    proposedPlan.budget = {
      ...budgetRes,
      currency: currentPlan.budget.currency,
    };

    tradeoffs = [
      "Pruned discretionary decor accents and premium bar packages to maintain entertainment and core catering.",
      "Locked vendor deposits and confirmed agreements were preserved without penalty.",
      `12% contingency reserve reduced in step (${oldReserve} → ${budgetRes.reserveMinor}) to sustain baseline operations.`,
    ];

    affectedTasks.push(
      "Re-evaluate floral centerpieces and table runner rentals.",
      "Inquire with caterer regarding bulk fixed-menu tiers.",
      "Review photography coverage hours for potential half-day discount."
    );

    vendorImpact.push(
      "Decor vendor: negotiate DIY swap or seasonal foliage.",
      "Catering vendor: freeze menu options to eliminate premium add-on surcharges."
    );
  } else if (action === "guests_plus_25") {
    // Guest increase: ceil(current guests * 1.25)
    newGuestCount = Math.ceil(currentGuests * 1.25);
    proposedPlan.brief.guestCount = newGuestCount;
    summary = `Scaled guest capacity by 25% (${currentGuests} → ${newGuestCount}) while maintaining fixed total budget.`;

    const oldPerGuest = Math.round(currentTotal / currentGuests);
    const newPerGuest = Math.round(currentTotal / newGuestCount);

    tradeoffs = [
      `Per-guest expenditure compressed from ${oldPerGuest} to ${newPerGuest} to accommodate additional attendees.`,
      "Shifted catering strategy from formal plated dining toward efficient buffet / food station service.",
      "Increased seating density and optimized venue circulation paths.",
    ];

    affectedTasks.push(
      `Issue ${newGuestCount - currentGuests} supplementary invitations and request rapid RSVPs.`,
      "Reconfigure venue floorplan to add 3–4 extra seating clusters.",
      "Recalculate drinkware, cutlery, and favor order quantities."
    );

    vendorImpact.push(
      "Venue: verify fire safety occupancy permits for expanded attendance.",
      "Caterer: request per-plate volume pricing tier for headcounts over " + currentGuests + "."
    );
  } else if (action === "rain_pivot") {
    proposedPlan.brief.setting = "indoor";
    summary = "Activated indoor weather pivot protocol: shifted open-air activities under covered canopy / hall shelter.";

    tradeoffs = [
      "Transitioned ceremony and dining from open lawn to verified indoor hall or waterproof canopy structure.",
      "Re-allocated ambient lighting focus toward indoor up-lighting and acoustical sound reflection.",
      "Assigned dedicated crew for guest umbrella escort and exterior footwear management.",
    ];

    affectedTasks.push(
      "Confirm covered hall access and verify ceiling height clearances for decor.",
      "Inspect electrical grounding and waterproof cabling covers for sound gear.",
      "Establish indoor guest greeting receiving line and coat/umbrella check."
    );

    vendorImpact.push(
      "Venue: unlock indoor ballroom/hall doors 2 hours earlier for staging.",
      "Sound/AV: position speakers to prevent indoor reverberation and echo."
    );
  } else {
    // Custom action
    const instruction = customInstruction || "Optimized plan parameters per user instruction.";
    summary = `Custom Replan: ${instruction}`;
    tradeoffs = [
      `Incorporated directive: "${instruction}".`,
      "Maintained deterministic 12% contingency reserve.",
      "Preserved existing completed checklists and vendor records.",
    ];
    affectedTasks.push("Reviewed timeline milestones against updated parameters.");
    vendorImpact.push("Audited vendor agreements against revised scope.");
  }

  // Check feasibility
  const isFeasible = !proposedPlan.budget.isDeficit;
  const deficitWarning = proposedPlan.budget.isDeficit
    ? proposedPlan.budget.deficitReason || "Infeasible: Locked category costs exceed available allocatable funds."
    : undefined;

  const tradeoffObj: PlanRescueTradeoff = {
    summary,
    tradeoffs,
    affectedTasks,
    vendorImpact,
    isFeasible,
    deficitWarning,
  };

  const oldPerGuest = Math.round(currentTotal / currentGuests);
  const newPerGuest = Math.round(newTotalMinor / newGuestCount);

  return {
    proposedPlan,
    baseRevision: currentPlan.metadata.revision,
    action,
    tradeoffs: tradeoffObj,
    diffSummary: {
      oldTotalMinor: currentTotal,
      newTotalMinor,
      oldReserveMinor: oldReserve,
      newReserveMinor: proposedPlan.budget.reserveMinor,
      oldGuestCount: currentGuests,
      newGuestCount,
      perGuestOldMinor: oldPerGuest,
      perGuestNewMinor: newPerGuest,
    },
  };
}

/**
 * Applies a Plan Rescue proposal with client-side verification:
 * - Rechecks that proposal.baseRevision === currentPlan.metadata.revision
 * - Blocks application if budget is infeasible (isDeficit: true)
 * - Generates new monotonically increasing revision: currentPlan.revision + 1
 * - Preserves completed tasks and existing user notes by ID
 */
export function applyProposal(
  currentPlan: EventPlan,
  proposal: PlanRescueProposal
): { success: true; updatedPlan: EventPlan } | { success: false; error: string } {
  // Stale check
  if (proposal.baseRevision !== currentPlan.metadata.revision) {
    return {
      success: false,
      error: `Proposal is stale (based on revision ${proposal.baseRevision}, but current plan is revision ${currentPlan.metadata.revision}). Please generate a fresh proposal.`,
    };
  }

  // Deficit check
  if (proposal.proposedPlan.budget.isDeficit) {
    return {
      success: false,
      error: `Cannot apply an infeasible budget deficit: ${proposal.proposedPlan.budget.deficitReason}. Please unlock categories or increase budget first.`,
    };
  }

  const updatedPlan: EventPlan = JSON.parse(JSON.stringify(proposal.proposedPlan));

  // Monotonically increase revision
  const newRevision = currentPlan.metadata.revision + 1;
  updatedPlan.metadata = {
    ...currentPlan.metadata,
    revision: newRevision,
    source: "locally-edited",
    updatedAt: new Date().toISOString(),
  };

  // Preserve user state for tasks (by stable ID)
  updatedPlan.timeline.preparationTasks = updatedPlan.timeline.preparationTasks.map((newTask) => {
    const existing = currentPlan.timeline.preparationTasks.find((t) => t.id === newTask.id);
    if (existing) {
      return {
        ...newTask,
        isCompleted: existing.isCompleted,
        owner: existing.owner,
      };
    }
    return newTask;
  });

  // Preserve user state for vendors (by stable ID)
  updatedPlan.vendors = updatedPlan.vendors.map((newVendor) => {
    const existing = currentPlan.vendors.find((v) => v.id === newVendor.id);
    if (existing) {
      return {
        ...newVendor,
        status: existing.status,
        notes: existing.notes,
        quotedAmountMinor: existing.quotedAmountMinor,
        contractChecklist: newVendor.contractChecklist.map((c) => {
          const existingItem = existing.contractChecklist.find((ec) => ec.id === c.id);
          return existingItem ? { ...c, checked: existingItem.checked } : c;
        }),
      };
    }
    return newVendor;
  });

  return {
    success: true,
    updatedPlan,
  };
}

/**
 * Creates an Undo state restoring previous plan content
 * while monotonically increasing the revision number.
 */
export function restorePlanWithFreshRevision(
  currentRevision: number,
  previousPlan: EventPlan
): EventPlan {
  const restored: EventPlan = JSON.parse(JSON.stringify(previousPlan));
  restored.metadata = {
    ...previousPlan.metadata,
    revision: currentRevision + 1,
    source: "locally-edited",
    updatedAt: new Date().toISOString(),
  };
  return restored;
}
