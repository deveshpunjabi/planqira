import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { calculateBudget, DEFAULT_COST_HACKS, DEFAULT_WEIGHTS } from "@/lib/budget";
import { buildDayOfRunOfShow, buildPreparationTasks } from "@/lib/dates";
import { generateCreativeBrief } from "@/lib/gemini";
import { buildDefaultVendors } from "@/lib/planner";
import { EventBriefSchema, EventPlan, EventPlanSchema } from "@/lib/schema";

export const runtime = "nodejs";
export const maxDuration = 60;

const RequestBodySchema = z.object({
  brief: EventBriefSchema,
});

export async function POST(req: NextRequest) {
  try {
    const rawBody = await req.json().catch(() => null);
    if (!rawBody) {
      return NextResponse.json(
        { success: false, error: "Invalid JSON request body." },
        { status: 400 }
      );
    }

    const parseResult = RequestBodySchema.safeParse(rawBody);
    if (!parseResult.success) {
      const issue = parseResult.error.issues[0];
      return NextResponse.json(
        { success: false, error: `Brief validation error: ${issue?.path.join(".")} - ${issue?.message}` },
        { status: 400 }
      );
    }

    const { brief } = parseResult.data;

    // Check if Live AI is enabled
    const isAiEnabled = process.env.AI_ENABLED === "true";
    const apiKey = process.env.GEMINI_API_KEY;

    if (!isAiEnabled || !apiKey || apiKey.trim() === "") {
      return NextResponse.json(
        {
          success: false,
          error:
            "Live AI is currently disabled or GEMINI_API_KEY is not configured on this server. Please use one of the interactive sample plans.",
          code: "AI_DISABLED",
        },
        { status: 503 }
      );
    }

    // Call Gemini with schema-bounded output
    const aiResult = await generateCreativeBrief(brief);
    if (!aiResult.success) {
      return NextResponse.json(
        {
          success: false,
          error: aiResult.error,
          code: "AI_GENERATION_FAILED",
        },
        { status: 502 }
      );
    }

    const creative = aiResult.data;

    // Deterministically compute budget using the model's suggested weights
    const budgetRes = calculateBudget(brief.totalBudget, undefined, {
      "cat-venue": creative.categoryWeights.venue,
      "cat-catering": creative.categoryWeights.catering,
      "cat-decor": creative.categoryWeights.decor,
      "cat-entertainment": creative.categoryWeights.entertainment,
      "cat-photo": creative.categoryWeights.photo,
      "cat-logistics": creative.categoryWeights.logistics,
    });

    // Populate category cost hacks from creative output
    budgetRes.categories = budgetRes.categories.map((c) => {
      let hack = c.costSavingHack;
      if (c.id === "cat-venue") hack = creative.vendorHacks.venue;
      if (c.id === "cat-catering") hack = creative.vendorHacks.catering;
      if (c.id === "cat-decor") hack = creative.vendorHacks.decor;
      if (c.id === "cat-entertainment") hack = creative.vendorHacks.entertainment;
      if (c.id === "cat-photo") hack = creative.vendorHacks.photo;
      if (c.id === "cat-logistics") hack = creative.vendorHacks.logistics;
      return { ...c, costSavingHack: hack };
    });

    // Build timeline deterministically from eventDate & timezone
    const tasks = buildPreparationTasks(brief.eventType, brief.eventDate, brief.timezone);
    const runOfShow = buildDayOfRunOfShow(brief.eventType, brief.startTime, brief.durationHours);

    // Build vendors and merge model's custom interrogation questions and scripts
    const vendors = buildDefaultVendors(brief).map((v) => {
      let q = v.hiddenFeeTrapQuestion;
      let s = v.inquiryScript;
      if (v.id === "vendor-venue") {
        q = creative.vendorQuestions.venue;
        s = creative.vendorScripts.venue;
      } else if (v.id === "vendor-catering") {
        q = creative.vendorQuestions.catering;
        s = creative.vendorScripts.catering;
      } else if (v.id === "vendor-decor") {
        q = creative.vendorQuestions.decor;
        s = creative.vendorScripts.decor;
      } else if (v.id === "vendor-entertainment") {
        q = creative.vendorQuestions.entertainment;
        s = creative.vendorScripts.entertainment;
      } else if (v.id === "vendor-photo") {
        q = creative.vendorQuestions.photo;
        s = creative.vendorScripts.photo;
      } else if (v.id === "vendor-logistics") {
        q = creative.vendorQuestions.logistics;
        s = creative.vendorScripts.logistics;
      }
      return { ...v, hiddenFeeTrapQuestion: q, inquiryScript: s };
    });

    // Assign stable IDs to themes
    const themes = creative.themes.map((t, idx) => ({
      ...t,
      id: `theme-ai-${idx + 1}`,
    }));

    const now = new Date().toISOString();
    const finalPlan: EventPlan = {
      metadata: {
        id: `plan-live-${Date.now()}`,
        schemaVersion: 1,
        revision: 1,
        source: "live-ai",
        createdAt: now,
        updatedAt: now,
      },
      brief: {
        ...brief,
        assumptions: [
          ...(brief.assumptions || []),
          ...creative.assumptions,
        ],
      },
      selectedThemeId: themes[0].id,
      themes,
      budget: {
        ...budgetRes,
        currency: brief.currency,
      },
      timeline: {
        preparationTasks: tasks,
        dayOfRunOfShow: runOfShow,
      },
      vendors,
      risks: {
        weatherProtocol: creative.weatherProtocol,
        riskItems: [
          {
            id: "risk-ai-1",
            risk: "Logistics and timeline overrun on peak event day activities.",
            severity: "high",
            mitigation: "Assign dedicated lead coordinator to hold buffer buffers between segments.",
          },
          {
            id: "risk-ai-2",
            risk: "Dietary or cultural constraint mismatch during food service.",
            severity: "medium",
            mitigation: `Clearly label counters (${brief.dietaryRestrictions || "all dietary categories"}) with visual signage.`,
          },
        ],
      },
    };

    // Validate the final EventPlan schema
    const validation = EventPlanSchema.safeParse(finalPlan);
    if (!validation.success) {
      return NextResponse.json(
        {
          success: false,
          error: `Generated plan failed validation: ${validation.error.issues[0]?.message}`,
        },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      plan: validation.data,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "An unexpected server error occurred.";
    return NextResponse.json(
      { success: false, error: message.replace(/key=[^&\s]+/gi, "key=[REDACTED]") },
      { status: 500 }
    );
  }
}
