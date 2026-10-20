import { z } from "zod";

export const CurrencyCodeSchema = z.enum(["INR", "USD", "EUR"]);
export type CurrencyCode = z.infer<typeof CurrencyCodeSchema>;

export const EventTypeSchema = z.enum(["wedding", "birthday", "community"]);
export type EventType = z.infer<typeof EventTypeSchema>;

export const SettingTypeSchema = z.enum(["indoor", "outdoor", "hybrid"]);
export type SettingType = z.infer<typeof SettingTypeSchema>;

export const PlanSourceSchema = z.enum(["sample", "live-ai", "locally-edited"]);
export type PlanSource = z.infer<typeof PlanSourceSchema>;

export const AssumptionSchema = z.object({
  field: z.string(),
  assumption: z.string(),
  editableReason: z.string(),
});
export type Assumption = z.infer<typeof AssumptionSchema>;

export const EventBriefSchema = z.object({
  eventType: EventTypeSchema,
  title: z.string().min(1, "Event title is required").max(120),
  eventDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Date must be YYYY-MM-DD"),
  startTime: z.string().regex(/^\d{2}:\d{2}$/, "Start time must be HH:mm"),
  durationHours: z.number().positive().max(72),
  timezone: z.string().min(1),
  city: z.string().min(1).max(80),
  setting: SettingTypeSchema,
  guestCount: z.number().int().positive("Guests must be a positive integer"),
  totalBudget: z.number().int().positive("Budget must be a positive integer"),
  currency: CurrencyCodeSchema,
  themePreferences: z.string().max(500).default(""),
  dietaryRestrictions: z.string().max(500).default(""),
  culturalPreferences: z.string().max(500).default(""),
  accessibilityNeeds: z.string().max(500).default(""),
  assumptions: z.array(AssumptionSchema).default([]),
});
export type EventBrief = z.infer<typeof EventBriefSchema>;

export const ThemeIdeaSchema = z.object({
  id: z.string(),
  name: z.string().min(1).max(100),
  tagline: z.string().max(160),
  aestheticVibe: z.string().max(300),
  paletteHex: z.tuple([
    z.string().regex(/^#[0-9A-Fa-f]{6}$/),
    z.string().regex(/^#[0-9A-Fa-f]{6}$/),
    z.string().regex(/^#[0-9A-Fa-f]{6}$/),
    z.string().regex(/^#[0-9A-Fa-f]{6}$/),
  ]),
  decorDirection: z.string().max(400),
  menuDirection: z.string().max(400),
  sensoryHook: z.string().max(300),
  signatureMoment: z.string().max(300),
  diySwap: z.string().max(300),
});
export type ThemeIdea = z.infer<typeof ThemeIdeaSchema>;

export const BudgetItemSchema = z.object({
  id: z.string(),
  name: z.string(),
  amountMinor: z.number().int().nonnegative(),
});
export type BudgetItem = z.infer<typeof BudgetItemSchema>;

export const BudgetCategorySchema = z.object({
  id: z.string(),
  name: z.string(),
  amountMinor: z.number().int().nonnegative(),
  percentage: z.number().nonnegative().max(100),
  isLocked: z.boolean().default(false),
  status: z.enum(["planned", "quoted", "booked"]).default("planned"),
  lineItems: z.array(BudgetItemSchema),
  costSavingHack: z.string(),
});
export type BudgetCategory = z.infer<typeof BudgetCategorySchema>;

export const BudgetPlanSchema = z.object({
  currency: CurrencyCodeSchema,
  totalMinor: z.number().int().positive(),
  reserveMinor: z.number().int().nonnegative(),
  allocatableMinor: z.number().int().nonnegative(),
  categories: z.array(BudgetCategorySchema).length(6),
  isDeficit: z.boolean().default(false),
  deficitMinor: z.number().int().nonnegative().default(0),
  deficitReason: z.string().optional(),
});
export type BudgetPlan = z.infer<typeof BudgetPlanSchema>;

export const PreparationTaskSchema = z.object({
  id: z.string(),
  timeframe: z.string(),
  dueDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  title: z.string().min(1),
  description: z.string(),
  owner: z.string(),
  priority: z.enum(["critical", "high", "medium"]),
  isCompleted: z.boolean().default(false),
  isOverdue: z.boolean().default(false),
  dependencies: z.array(z.string()).default([]),
});
export type PreparationTask = z.infer<typeof PreparationTaskSchema>;

export const DayOfBlockSchema = z.object({
  id: z.string(),
  timeSlot: z.string(),
  frontOfHouseGuestView: z.string(),
  backOfHouseCrewAction: z.string(),
  leadVendorOrRole: z.string(),
});
export type DayOfBlock = z.infer<typeof DayOfBlockSchema>;

export const TimelinePlanSchema = z.object({
  preparationTasks: z.array(PreparationTaskSchema),
  dayOfRunOfShow: z.array(DayOfBlockSchema),
});
export type TimelinePlan = z.infer<typeof TimelinePlanSchema>;

export const VendorChecklistItemSchema = z.object({
  id: z.string(),
  item: z.string(),
  checked: z.boolean().default(false),
});
export type VendorChecklistItem = z.infer<typeof VendorChecklistItemSchema>;

export const VendorRecordSchema = z.object({
  id: z.string(),
  category: z.string(),
  title: z.string(),
  bookingWindow: z.string(),
  status: z.enum(["not-started", "inquiry-sent", "quote-received", "booked"]).default("not-started"),
  contractChecklist: z.array(VendorChecklistItemSchema),
  hiddenFeeTrapQuestion: z.string(),
  inquiryScript: z.string(),
  notes: z.string().default(""),
  quotedAmountMinor: z.number().int().nonnegative().optional(),
});
export type VendorRecord = z.infer<typeof VendorRecordSchema>;

export const RiskItemSchema = z.object({
  id: z.string(),
  risk: z.string(),
  severity: z.enum(["low", "medium", "high"]),
  mitigation: z.string(),
});
export type RiskItem = z.infer<typeof RiskItemSchema>;

export const RiskPlanSchema = z.object({
  weatherProtocol: z.string(),
  riskItems: z.array(RiskItemSchema),
});
export type RiskPlan = z.infer<typeof RiskPlanSchema>;

export const EventPlanMetadataSchema = z.object({
  id: z.string(),
  schemaVersion: z.literal(1),
  revision: z.number().int().positive(),
  source: PlanSourceSchema,
  createdAt: z.string(),
  updatedAt: z.string(),
});
export type EventPlanMetadata = z.infer<typeof EventPlanMetadataSchema>;

export const EventPlanSchema = z.object({
  metadata: EventPlanMetadataSchema,
  brief: EventBriefSchema,
  selectedThemeId: z.string(),
  themes: z.array(ThemeIdeaSchema).min(1).max(5),
  budget: BudgetPlanSchema,
  timeline: TimelinePlanSchema,
  vendors: z.array(VendorRecordSchema).min(3).max(10),
  risks: RiskPlanSchema,
});
export type EventPlan = z.infer<typeof EventPlanSchema>;

export const ReplanActionSchema = z.enum([
  "budget_cut_15",
  "guests_plus_25",
  "rain_pivot",
  "custom",
]);
export type ReplanAction = z.infer<typeof ReplanActionSchema>;

export const ReplanRequestSchema = z.object({
  currentPlan: EventPlanSchema,
  baseRevision: z.number().int().positive(),
  action: ReplanActionSchema,
  customInstruction: z.string().max(500).optional(),
});
export type ReplanRequest = z.infer<typeof ReplanRequestSchema>;

export const PlanRescueTradeoffSchema = z.object({
  summary: z.string(),
  tradeoffs: z.array(z.string()).length(3),
  affectedTasks: z.array(z.string()),
  vendorImpact: z.array(z.string()),
  isFeasible: z.boolean(),
  deficitWarning: z.string().optional(),
});
export type PlanRescueTradeoff = z.infer<typeof PlanRescueTradeoffSchema>;

export const PlanRescueProposalSchema = z.object({
  proposedPlan: EventPlanSchema,
  baseRevision: z.number().int().positive(),
  action: ReplanActionSchema,
  tradeoffs: PlanRescueTradeoffSchema,
  diffSummary: z.object({
    oldTotalMinor: z.number(),
    newTotalMinor: z.number(),
    oldReserveMinor: z.number(),
    newReserveMinor: z.number(),
    oldGuestCount: z.number(),
    newGuestCount: z.number(),
    perGuestOldMinor: z.number(),
    perGuestNewMinor: z.number(),
  }),
});
export type PlanRescueProposal = z.infer<typeof PlanRescueProposalSchema>;
