import { describe, expect, it } from "vitest";
import {
  calculateBudget,
  distributeByWeights,
  formatCurrency,
} from "../lib/budget";
import { BudgetCategory } from "../lib/schema";

describe("Deterministic Budget Engine Tests", () => {
  it("computes reserveMinor as exactly round(totalMinor * 12 / 100)", () => {
    const testTotals = [1000000, 120000000, 3500000, 500000, 777777, 999999, 12345];
    for (const total of testTotals) {
      const budget = calculateBudget(total);
      const expectedReserve = Math.round((total * 12) / 100);
      expect(budget.reserveMinor).toBe(expectedReserve);
      expect(budget.allocatableMinor).toBe(total - expectedReserve);
    }
  });

  it("satisfies the strict budget sum invariant: sum(categories) + reserve == total exactly", () => {
    // Test across 100 randomized budgets
    for (let i = 0; i < 100; i++) {
      const randomTotal = Math.floor(Math.random() * 50000000) + 1000;
      const budget = calculateBudget(randomTotal);

      const categorySum = budget.categories.reduce((acc, cat) => acc + cat.amountMinor, 0);
      expect(categorySum).toBe(budget.allocatableMinor);
      expect(categorySum + budget.reserveMinor).toBe(randomTotal);

      // Verify no allocation is negative
      for (const cat of budget.categories) {
        expect(cat.amountMinor).toBeGreaterThanOrEqual(0);
      }
    }
  });

  it("satisfies line item invariant: each category line items sum exactly to category amountMinor", () => {
    const budget = calculateBudget(120000000);
    for (const cat of budget.categories) {
      const lineItemSum = cat.lineItems.reduce((acc, item) => acc + item.amountMinor, 0);
      expect(lineItemSum).toBe(cat.amountMinor);
      for (const item of cat.lineItems) {
        expect(item.amountMinor).toBeGreaterThanOrEqual(0);
      }
    }
  });

  it("preserves locked categories during re-allocation", () => {
    const initial = calculateBudget(1000000);
    const venueCat = initial.categories.find((c) => c.id === "cat-venue")!;
    const lockedVenueAmount = venueCat.amountMinor;

    // Lock the venue category
    const modifiedCategories: BudgetCategory[] = initial.categories.map((c) =>
      c.id === "cat-venue" ? { ...c, isLocked: true } : c
    );

    // Increase total budget from 1,000,000 to 1,500,000
    const reallocated = calculateBudget(1500000, modifiedCategories);
    const reallocatedVenue = reallocated.categories.find((c) => c.id === "cat-venue")!;

    // Locked category must remain identical
    expect(reallocatedVenue.isLocked).toBe(true);
    expect(reallocatedVenue.amountMinor).toBe(lockedVenueAmount);

    // The entire budget must still balance exactly
    const categorySum = reallocated.categories.reduce((acc, cat) => acc + cat.amountMinor, 0);
    expect(categorySum + reallocated.reserveMinor).toBe(1500000);
  });

  it("detects impossible budget deficits when locked costs exceed allocatable budget", () => {
    const initial = calculateBudget(1000000);
    // Artificially lock categories to 950,000 (exceeding allocatable 880,000)
    const lockedCategories: BudgetCategory[] = initial.categories.map((c, idx) => ({
      ...c,
      isLocked: idx === 0,
      amountMinor: idx === 0 ? 950000 : c.amountMinor,
    }));

    const result = calculateBudget(1000000, lockedCategories);
    expect(result.isDeficit).toBe(true);
    expect(result.deficitMinor).toBe(950000 - 880000); // 70000 deficit
    expect(result.deficitReason).toBeDefined();
  });

  it("detects all-locked surplus when all categories are locked but don't match allocatable budget", () => {
    const initial = calculateBudget(1000000);
    const allLockedCategories: BudgetCategory[] = initial.categories.map((c) => ({
      ...c,
      isLocked: true,
      amountMinor: 100000, // sum = 600,000 vs allocatable 880,000
    }));

    const result = calculateBudget(1000000, allLockedCategories);
    expect(result.isDeficit).toBe(true);
    expect(result.deficitMinor).toBe(880000 - 600000);
  });

  it("formats currencies correctly for INR, USD, and EUR", () => {
    expect(formatCurrency(120000000, "INR")).toBe("₹12,00,000");
    expect(formatCurrency(500000, "USD")).toBe("$5,000");
    expect(formatCurrency(500000, "EUR")).toMatch(/5\.000|5,000/);
  });
});
