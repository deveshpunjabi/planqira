import { buildDeterministicPlan } from "../lib/planner";
import { EventBrief, EventPlan } from "../lib/schema";

export const SAMPLE_WEDDING_BRIEF: EventBrief = {
  eventType: "wedding",
  title: "Royal Rajputana Heritage Wedding",
  eventDate: "2026-11-20",
  startTime: "16:00",
  durationHours: 6,
  timezone: "Asia/Kolkata",
  city: "Jaipur, Rajasthan",
  setting: "hybrid",
  guestCount: 250,
  totalBudget: 120000000, // ₹12,00,000 in paise
  currency: "INR",
  themePreferences: "Palace heritage with regal marigolds, brass urlis, warm velvet, and traditional Shehnai music",
  dietaryRestrictions: "Strict Vegetarian, Satvik & Jain counter, authentic Rajasthani Dal Baati Churma & Kulfi",
  culturalPreferences: "Traditional Vedic ceremonial elements, floral Phoolon Ki Chaadar, no alcohol, live classical folk instruments",
  accessibilityNeeds: "Step-free ramp to main Mandap stage, golf cart shuttle from parking for senior family members",
  assumptions: [
    {
      field: "eventDate",
      assumption: "Set to 30 days from project creation for complete milestone demonstration.",
      editableReason: "Users can adjust date to their actual wedding muhurat.",
    },
    {
      field: "dietaryRestrictions",
      assumption: "Pure vegetarian with separate Jain preparation counter based on cultural brief.",
      editableReason: "Can be updated if multi-cuisine or non-veg counters are required.",
    },
    {
      field: "accessibilityNeeds",
      assumption: "Ground-level accessibility ensured for elderly relatives.",
      editableReason: "May be modified depending on the selected heritage haveli or hotel layout.",
    },
  ],
};

export const SAMPLE_BIRTHDAY_BRIEF: EventBrief = {
  eventType: "birthday",
  title: "Neon Cyber-Retro 21st Birthday",
  eventDate: "2026-11-05",
  startTime: "19:00",
  durationHours: 5,
  timezone: "Asia/Kolkata",
  city: "Bengaluru, Karnataka",
  setting: "indoor",
  guestCount: 45,
  totalBudget: 3500000, // ₹35,000 in paise
  currency: "INR",
  themePreferences: "Synthwave neon lights, 90s retro arcade games, glowing UV lounge, upbeat EDM & synth pop",
  dietaryRestrictions: "Vegetarian finger food, loaded sliders, churros, mocktail spritzers, peanut-free snacks",
  culturalPreferences: "Casual contemporary celebration, DIY polaroid guest wall, interactive trivia",
  accessibilityNeeds: "Elevator access to rooftop terrace, accessible all-gender restrooms",
  assumptions: [
    {
      field: "setting",
      assumption: "Indoor rooftop lounge chosen to protect UV lighting and electronic audio gear from evening wind.",
      editableReason: "Can be shifted outdoors if weather permits.",
    },
    {
      field: "beverage",
      assumption: "Non-alcoholic mocktails and craft sodas prioritized within the ₹35,000 budget.",
      editableReason: "Can be upgraded if hosts bring their own beverages with corkage waiver.",
    },
  ],
};

export const SAMPLE_COMMUNITY_BRIEF: EventBrief = {
  eventType: "community",
  title: "Neighborhood Eco-Fest & Green Fundraiser",
  eventDate: "2026-11-15",
  startTime: "10:00",
  durationHours: 7,
  timezone: "Asia/Kolkata",
  city: "Pune, Maharashtra",
  setting: "outdoor",
  guestCount: 300,
  totalBudget: 15000000, // ₹1,50,000 in paise
  currency: "INR",
  themePreferences: "Zero-waste sustainability, reclaimed wood stalls, potted living plants, local acoustic folk",
  dietaryRestrictions: "Community vegan & vegetarian street food stalls, bring-your-own-cup water station",
  culturalPreferences: "Inclusive community festival, bilingual announcements (Marathi/English), artisan craft bazaar",
  accessibilityNeeds: "Wide unblocked wheelchair paths across park lawn, accessible portable sanitation units, sensory quiet zone",
  assumptions: [
    {
      field: "volunteers",
      assumption: "20 neighborhood volunteer marshals manage check-in, green sorting, and child safety.",
      editableReason: "Adjust if paid event staffing is contracted instead.",
    },
    {
      field: "permits",
      assumption: "Park municipal sound and gathering permissions filed with local ward office.",
      editableReason: "Verify local municipal permit turnaround times.",
    },
  ],
};

export const SAMPLE_GALA_BRIEF: EventBrief = {
  eventType: "birthday",
  title: "Golden Jubilee 50th Birthday Gala",
  eventDate: "2026-11-28",
  startTime: "18:30",
  durationHours: 5,
  timezone: "America/New_York",
  city: "Boston, MA",
  setting: "hybrid",
  guestCount: 75,
  totalBudget: 500000, // $5,000 in cents
  currency: "USD",
  themePreferences: "Sophisticated golden elegance, garden glasshouse pavilion, live jazz trio, ambient candlelight",
  dietaryRestrictions: "Plated seasonal dinner, gluten-free and dairy-free options marked, sparkling cider toast",
  culturalPreferences: "Celebration of family legacy, slideshow tribute, champagne flute toast",
  accessibilityNeeds: "Ramped entrance from valet to pavilion, wide table spacing for mobility aids",
  assumptions: [
    {
      field: "entertainment",
      assumption: "Local student jazz trio booked for 3 hours with acoustic sound equipment.",
      editableReason: "Can swap to curated audio playlist to reallocate funds toward catering.",
    },
  ],
};

export const SAMPLE_WEDDING_PLAN: EventPlan = buildDeterministicPlan(SAMPLE_WEDDING_BRIEF, "sample");
export const SAMPLE_BIRTHDAY_PLAN: EventPlan = buildDeterministicPlan(SAMPLE_BIRTHDAY_BRIEF, "sample");
export const SAMPLE_COMMUNITY_PLAN: EventPlan = buildDeterministicPlan(SAMPLE_COMMUNITY_BRIEF, "sample");
export const SAMPLE_GALA_PLAN: EventPlan = buildDeterministicPlan(SAMPLE_GALA_BRIEF, "sample");

export const SAMPLE_PLANS: Record<string, EventPlan> = {
  wedding: SAMPLE_WEDDING_PLAN,
  birthday: SAMPLE_BIRTHDAY_PLAN,
  community: SAMPLE_COMMUNITY_PLAN,
  gala: SAMPLE_GALA_PLAN,
};

export const DEFAULT_PLAN: EventPlan = SAMPLE_WEDDING_PLAN;
