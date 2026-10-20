import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET() {
  const isAiEnabled = process.env.AI_ENABLED === "true";
  const hasApiKey = Boolean(process.env.GEMINI_API_KEY && process.env.GEMINI_API_KEY.trim() !== "");
  const model = process.env.GEMINI_MODEL || "gemini-2.5-flash";

  return NextResponse.json({
    status: "ok",
    app: "UtsavAI — Celebration & Event Planner",
    version: "1.0.0",
    aiConfig: {
      aiEnabled: isAiEnabled,
      hasApiKey,
      model,
      sampleModeAvailable: true,
    },
    timestamp: new Date().toISOString(),
  });
}
