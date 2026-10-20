import { NextRequest, NextResponse } from "next/server";
import { generatePlanRescueProposal } from "@/lib/diff";
import { ReplanRequestSchema } from "@/lib/schema";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const rawBody = await req.json().catch(() => null);
    if (!rawBody) {
      return NextResponse.json(
        { success: false, error: "Invalid JSON request body." },
        { status: 400 }
      );
    }

    const parseResult = ReplanRequestSchema.safeParse(rawBody);
    if (!parseResult.success) {
      const issue = parseResult.error.issues[0];
      return NextResponse.json(
        { success: false, error: `Invalid replan request: ${issue?.path.join(".")} - ${issue?.message}` },
        { status: 400 }
      );
    }

    const { currentPlan, action, customInstruction } = parseResult.data;

    // Generate Proposal with strict domain calculations
    const proposal = generatePlanRescueProposal(currentPlan, action, customInstruction);

    return NextResponse.json({
      success: true,
      proposal,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Failed to process replan request.";
    return NextResponse.json(
      { success: false, error: message },
      { status: 500 }
    );
  }
}
