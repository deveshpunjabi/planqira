import { BudgetCategory, BudgetItem, CurrencyCode } from "./schema";

export const CATEGORY_IDS = [
  "cat-venue",
  "cat-catering",
  "cat-decor",
  "cat-entertainment",
  "cat-photo",
  "cat-logistics",
] as const;

export const CATEGORY_NAMES: Record<string, string> = {
  "cat-venue": "Venue & Space",
  "cat-catering": "Catering & Beverage",
  "cat-decor": "Decor & Lighting",
  "cat-entertainment": "Entertainment & Sound",
  "cat-photo": "Photography & Memories",
  "cat-logistics": "Logistics & Swag",
};

export const DEFAULT_WEIGHTS: Record<string, number> = {
  "cat-venue": 30,
  "cat-catering": 30,
  "cat-decor": 15,
  "cat-entertainment": 10,
  "cat-photo": 8,
  "cat-logistics": 7,
};

export const DEFAULT_LINE_ITEMS: Record<string, string[]> = {
  "cat-venue": ["Hall / Ground Rental", "Setup & Breakdown Hours", "Security & Facilities Fee"],
  "cat-catering": ["Main Meal Buffet / Plated", "Welcome Beverages & Bar Service", "Dessert & Late Night Bites"],
  "cat-decor": ["Stage / Focal Backdrop", "Ambient Lighting & Rigging", "Table Centerpieces & Florals"],
  "cat-entertainment": ["Sound System & Microphones", "DJ / Live Performers", "MC & Program Coordinator"],
  "cat-photo": ["Lead Photographer Coverage", "Cinematic Video Highlights", "Raw Assets & Online Album"],
  "cat-logistics": ["Guest Signage & Badges", "Trash Disposal & Green Clean-Up", "Favors & Welcome Tokens"],
};

export const DEFAULT_COST_HACKS: Record<string, string> = {
  "cat-venue": "Inquire about non-peak booking rates or negotiate complimentary access for rehearsal and setup.",
  "cat-catering": "Opt for a seasonal menu with localized sourcing, and request corkage waiver in writing.",
  "cat-decor": "Repurpose ceremony focal florals as reception backdrops and use warm ambient up-lighting instead of heavy draping.",
  "cat-entertainment": "Bundle audio equipment with your DJ booking to eliminate third-party rental markup.",
  "cat-photo": "Book a single team covering both photo and video reels to secure a package discount.",
  "cat-logistics": "Order sustainable bulk digital signage and source local zero-waste supplies.",
};

/**
 * Largest-Remainder integer distribution.
 * Distributes totalMinor into integer allocations matching weights, ensuring exact sum.
 */
export function distributeByWeights(totalMinor: number, weights: number[]): number[] {
  if (weights.length === 0) return [];
  if (totalMinor <= 0) return weights.map(() => 0);

  const weightSum = weights.reduce((a, b) => a + b, 0);
  if (weightSum === 0) {
    const base = Math.floor(totalMinor / weights.length);
    let remainder = totalMinor - base * weights.length;
    return weights.map(() => {
      const add = remainder > 0 ? 1 : 0;
      if (remainder > 0) remainder--;
      return base + add;
    });
  }

  const floatAllocations = weights.map((w) => (totalMinor * w) / weightSum);
  const floorAllocations = floatAllocations.map(Math.floor);
  let remainder = totalMinor - floorAllocations.reduce((a, b) => a + b, 0);

  // Compute fractional remainders with stable tie-break by index
  const fractions = floatAllocations.map((val, idx) => ({
    fraction: val - floorAllocations[idx],
    idx,
  }));
  fractions.sort((a, b) => {
    if (b.fraction !== a.fraction) return b.fraction - a.fraction;
    return a.idx - b.idx;
  });

  const result = [...floorAllocations];
  for (let i = 0; i < remainder; i++) {
    const targetIdx = fractions[i % fractions.length].idx;
    result[targetIdx] += 1;
  }

  return result;
}

/**
 * Distributes category amountMinor into 3 line items deterministically.
 */
export function buildLineItems(
  categoryId: string,
  categoryAmountMinor: number,
  existingItems?: BudgetItem[]
): BudgetItem[] {
  const defaultNames = DEFAULT_LINE_ITEMS[categoryId] || ["Primary Component", "Secondary Component", "Logistics & Sundry"];
  const weights = [50, 30, 20]; // 50%, 30%, 20%
  const amounts = distributeByWeights(categoryAmountMinor, weights);

  return defaultNames.map((name, i) => {
    const existing = existingItems && existingItems[i];
    return {
      id: existing?.id || `${categoryId}-item-${i + 1}`,
      name: existing?.name || name,
      amountMinor: amounts[i],
    };
  });
}

export interface BudgetCalculationResult {
  totalMinor: number;
  reserveMinor: number;
  allocatableMinor: number;
  categories: BudgetCategory[];
  isDeficit: boolean;
  deficitMinor: number;
  deficitReason?: string;
}

/**
 * Calculates a complete deterministic budget ledger:
 * 1. reserveMinor = round(totalMinor * 12 / 100)
 * 2. allocatableMinor = totalMinor - reserveMinor
 * 3. Preserves locked categories.
 * 4. Checks for deficits (lockedSum > allocatableMinor or all locked with sum mismatch).
 * 5. Distributes remaining allocatable amount across unlocked categories using largest-remainder.
 * 6. Line items for each category sum exactly to category amountMinor.
 */
export function calculateBudget(
  totalMinor: number,
  currentCategories?: BudgetCategory[],
  customWeights?: Record<string, number>
): BudgetCalculationResult {
  if (totalMinor < 0) totalMinor = 0;
  const reserveMinor = Math.round((totalMinor * 12) / 100);
  const allocatableMinor = totalMinor - reserveMinor;

  const weightsMap = customWeights || DEFAULT_WEIGHTS;

  // Initialize categories template
  const categoriesTemplate: Array<{
    id: string;
    name: string;
    isLocked: boolean;
    lockedAmount: number;
    weight: number;
    status: "planned" | "quoted" | "booked";
    costSavingHack: string;
    existingLineItems?: BudgetItem[];
  }> = CATEGORY_IDS.map((id) => {
    const existing = currentCategories?.find((c) => c.id === id);
    return {
      id,
      name: CATEGORY_NAMES[id],
      isLocked: existing?.isLocked || false,
      lockedAmount: existing?.isLocked ? existing.amountMinor : 0,
      weight: weightsMap[id] || 15,
      status: existing?.status || "planned",
      costSavingHack: existing?.costSavingHack || DEFAULT_COST_HACKS[id],
      existingLineItems: existing?.lineItems,
    };
  });

  const lockedSum = categoriesTemplate.reduce((sum, c) => sum + (c.isLocked ? c.lockedAmount : 0), 0);
  const allLocked = categoriesTemplate.every((c) => c.isLocked);

  let isDeficit = false;
  let deficitMinor = 0;
  let deficitReason: string | undefined = undefined;

  // Check deficit constraints
  if (lockedSum > allocatableMinor) {
    isDeficit = true;
    deficitMinor = lockedSum - allocatableMinor;
    deficitReason = `Locked category costs (${lockedSum}) exceed available allocatable budget (${allocatableMinor}). Deficit: ${deficitMinor}.`;
  } else if (allLocked && lockedSum !== allocatableMinor) {
    isDeficit = true;
    deficitMinor = Math.abs(allocatableMinor - lockedSum);
    deficitReason =
      lockedSum < allocatableMinor
        ? `All categories are locked, leaving an unallocated surplus of ${deficitMinor}. Unlock a category or adjust locked totals.`
        : `Locked categories exceed allocatable budget by ${deficitMinor}.`;
  }

  const unlockedRemaining = Math.max(0, allocatableMinor - lockedSum);
  const unlockedCategories = categoriesTemplate.filter((c) => !c.isLocked);
  const unlockedWeights = unlockedCategories.map((c) => c.weight);
  const unlockedAmounts = isDeficit && lockedSum >= allocatableMinor
    ? unlockedCategories.map(() => 0)
    : distributeByWeights(unlockedRemaining, unlockedWeights);

  let unlockedIdx = 0;
  const finalCategories: BudgetCategory[] = categoriesTemplate.map((c) => {
    let catAmount: number;
    if (c.isLocked) {
      catAmount = c.lockedAmount;
    } else {
      catAmount = unlockedAmounts[unlockedIdx] ?? 0;
      unlockedIdx++;
    }

    const percentage = totalMinor > 0 ? Number(((catAmount / totalMinor) * 100).toFixed(1)) : 0;
    const lineItems = buildLineItems(c.id, catAmount, c.existingLineItems);

    return {
      id: c.id,
      name: c.name,
      amountMinor: catAmount,
      percentage,
      isLocked: c.isLocked,
      status: c.status,
      lineItems,
      costSavingHack: c.costSavingHack,
    };
  });

  return {
    totalMinor,
    reserveMinor,
    allocatableMinor,
    categories: finalCategories,
    isDeficit,
    deficitMinor,
    deficitReason,
  };
}

/**
 * Currency formatter supporting INR (lakhs/crores notation), USD, and EUR.
 */
export function formatCurrency(amountMinor: number, currency: CurrencyCode): string {
  const major = amountMinor / 100;
  if (currency === "INR") {
    // Indian numbering format (e.g., ₹12,00,000)
    const formatted = major.toLocaleString("en-IN", {
      maximumFractionDigits: 0,
      minimumFractionDigits: 0,
    });
    return `₹${formatted}`;
  } else if (currency === "USD") {
    const formatted = major.toLocaleString("en-US", {
      maximumFractionDigits: 0,
      minimumFractionDigits: 0,
    });
    return `$${formatted}`;
  } else {
    const formatted = major.toLocaleString("de-DE", {
      maximumFractionDigits: 0,
      minimumFractionDigits: 0,
    });
    return `€${formatted}`;
  }
}
