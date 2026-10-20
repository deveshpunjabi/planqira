import { GoogleGenAI, Type } from "@google/genai";
import { z } from "zod";
import { EventBrief } from "./schema";

export const ProviderCreativeOutputSchema = z.object({
  themes: z.array(
    z.object({
      name: z.string().min(1),
      tagline: z.string().min(1),
      aestheticVibe: z.string().min(1),
      paletteHex: z.tuple([
        z.string().regex(/^#[0-9A-Fa-f]{6}$/),
        z.string().regex(/^#[0-9A-Fa-f]{6}$/),
        z.string().regex(/^#[0-9A-Fa-f]{6}$/),
        z.string().regex(/^#[0-9A-Fa-f]{6}$/),
      ]),
      decorDirection: z.string().min(1),
      menuDirection: z.string().min(1),
      sensoryHook: z.string().min(1),
      signatureMoment: z.string().min(1),
      diySwap: z.string().min(1),
    })
  ).length(3),
  categoryWeights: z.object({
    venue: z.number().int().min(5).max(60),
    catering: z.number().int().min(5).max(60),
    decor: z.number().int().min(5).max(40),
    entertainment: z.number().int().min(5).max(30),
    photo: z.number().int().min(3).max(25),
    logistics: z.number().int().min(3).max(25),
  }),
  vendorHacks: z.object({
    venue: z.string(),
    catering: z.string(),
    decor: z.string(),
    entertainment: z.string(),
    photo: z.string(),
    logistics: z.string(),
  }),
  vendorQuestions: z.object({
    venue: z.string(),
    catering: z.string(),
    decor: z.string(),
    entertainment: z.string(),
    photo: z.string(),
    logistics: z.string(),
  }),
  vendorScripts: z.object({
    venue: z.string(),
    catering: z.string(),
    decor: z.string(),
    entertainment: z.string(),
    photo: z.string(),
    logistics: z.string(),
  }),
  weatherProtocol: z.string(),
  assumptions: z.array(
    z.object({
      field: z.string(),
      assumption: z.string(),
      editableReason: z.string(),
    })
  ).default([]),
});
export type ProviderCreativeOutput = z.infer<typeof ProviderCreativeOutputSchema>;

/**
 * Returns Gemini client if configured, otherwise null.
 */
export function getGeminiClient(): { client: GoogleGenAI; model: string } | null {
  const isEnabled = process.env.AI_ENABLED === "true";
  const apiKey = process.env.GEMINI_API_KEY;
  const model = process.env.GEMINI_MODEL || "gemini-2.5-flash";

  if (!isEnabled || !apiKey || apiKey.trim() === "") {
    return null;
  }

  const client = new GoogleGenAI({ apiKey });
  return { client, model };
}

/**
 * Calls Gemini Developer API with structured JSON output schema.
 * Rejects with sanitized error messages. Timeout bounded at 35 seconds.
 */
export async function generateCreativeBrief(
  brief: EventBrief
): Promise<{ success: true; data: ProviderCreativeOutput } | { success: false; error: string }> {
  const aiConfig = getGeminiClient();
  if (!aiConfig) {
    return {
      success: false,
      error:
        process.env.AI_ENABLED !== "true"
          ? "Live AI is disabled (AI_ENABLED=false). Please use credential-free sample plans or enable AI on the server."
          : "GEMINI_API_KEY is not configured on the server.",
    };
  }

  const prompt = `
You are the creative architectural engine of UtsavAI, an elite event planner for weddings, birthdays, and community gatherings.
Design a cohesive, culturally sensitive, and deeply personalized blueprint based on the user's brief.

CRITICAL INSTRUCTIONS:
- Do not invent vendor contact information, fake phone numbers, or fabricated live weather forecasts.
- Provide actionable, location-aware suggestions that respect dietary constraints (${brief.dietaryRestrictions || "none"}), cultural preferences (${brief.culturalPreferences || "contemporary"}), and accessibility (${brief.accessibilityNeeds || "standard"}).
- Return EXACTLY 3 bespoke themes with 4 valid hex colors (#RRGGBB).
- Provide custom weights for 6 categories (venue, catering, decor, entertainment, photo, logistics) that reflect the nature of the celebration.
- Provide sharp, non-obvious hidden-fee questions to protect the client before signing vendor contracts.
- Provide professional negotiation drafts that can be copied directly to WhatsApp or email.

EVENT BRIEF:
- Event Type: ${brief.eventType}
- Title: ${brief.title}
- Date: ${brief.eventDate} at ${brief.startTime} (${brief.durationHours} hours)
- Timezone: ${brief.timezone}
- City: ${brief.city}
- Setting: ${brief.setting}
- Guests: ${brief.guestCount}
- Budget: ${brief.currency} ${(brief.totalBudget / 100).toLocaleString()}
- Theme preferences: ${brief.themePreferences}
- Dietary restrictions: ${brief.dietaryRestrictions}
- Cultural preferences: ${brief.culturalPreferences}
- Accessibility needs: ${brief.accessibilityNeeds}
`.trim();

  try {
    const abortController = new AbortController();
    const timeout = setTimeout(() => abortController.abort(), 35000);

    const response = await aiConfig.client.models.generateContent({
      model: aiConfig.model,
      contents: prompt,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            themes: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  name: { type: Type.STRING },
                  tagline: { type: Type.STRING },
                  aestheticVibe: { type: Type.STRING },
                  paletteHex: {
                    type: Type.ARRAY,
                    items: { type: Type.STRING },
                  },
                  decorDirection: { type: Type.STRING },
                  menuDirection: { type: Type.STRING },
                  sensoryHook: { type: Type.STRING },
                  signatureMoment: { type: Type.STRING },
                  diySwap: { type: Type.STRING },
                },
                required: [
                  "name",
                  "tagline",
                  "aestheticVibe",
                  "paletteHex",
                  "decorDirection",
                  "menuDirection",
                  "sensoryHook",
                  "signatureMoment",
                  "diySwap",
                ],
              },
            },
            categoryWeights: {
              type: Type.OBJECT,
              properties: {
                venue: { type: Type.INTEGER },
                catering: { type: Type.INTEGER },
                decor: { type: Type.INTEGER },
                entertainment: { type: Type.INTEGER },
                photo: { type: Type.INTEGER },
                logistics: { type: Type.INTEGER },
              },
              required: ["venue", "catering", "decor", "entertainment", "photo", "logistics"],
            },
            vendorHacks: {
              type: Type.OBJECT,
              properties: {
                venue: { type: Type.STRING },
                catering: { type: Type.STRING },
                decor: { type: Type.STRING },
                entertainment: { type: Type.STRING },
                photo: { type: Type.STRING },
                logistics: { type: Type.STRING },
              },
              required: ["venue", "catering", "decor", "entertainment", "photo", "logistics"],
            },
            vendorQuestions: {
              type: Type.OBJECT,
              properties: {
                venue: { type: Type.STRING },
                catering: { type: Type.STRING },
                decor: { type: Type.STRING },
                entertainment: { type: Type.STRING },
                photo: { type: Type.STRING },
                logistics: { type: Type.STRING },
              },
              required: ["venue", "catering", "decor", "entertainment", "photo", "logistics"],
            },
            vendorScripts: {
              type: Type.OBJECT,
              properties: {
                venue: { type: Type.STRING },
                catering: { type: Type.STRING },
                decor: { type: Type.STRING },
                entertainment: { type: Type.STRING },
                photo: { type: Type.STRING },
                logistics: { type: Type.STRING },
              },
              required: ["venue", "catering", "decor", "entertainment", "photo", "logistics"],
            },
            weatherProtocol: { type: Type.STRING },
            assumptions: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  field: { type: Type.STRING },
                  assumption: { type: Type.STRING },
                  editableReason: { type: Type.STRING },
                },
                required: ["field", "assumption", "editableReason"],
              },
            },
          },
          required: [
            "themes",
            "categoryWeights",
            "vendorHacks",
            "vendorQuestions",
            "vendorScripts",
            "weatherProtocol",
          ],
        },
      },
    });

    clearTimeout(timeout);

    const text = response.text;
    if (!text) {
      return { success: false, error: "Model returned an empty response." };
    }

    const rawJson = JSON.parse(text);
    const parsed = ProviderCreativeOutputSchema.safeParse(rawJson);
    if (!parsed.success) {
      return {
        success: false,
        error: `Model output did not match required schema: ${parsed.error.issues[0]?.message}`,
      };
    }

    return { success: true, data: parsed.data };
  } catch (err: unknown) {
    const errorMsg =
      err instanceof Error
        ? err.name === "AbortError"
          ? "AI provider request timed out (35s deadline exceeded)."
          : err.message.replace(/key=[^&\s]+/gi, "key=[REDACTED]")
        : "Failed to communicate with AI provider.";
    return { success: false, error: errorMsg };
  }
}
