import { DayOfBlock, EventType, PreparationTask } from "./schema";

/**
 * Parses YYYY-MM-DD into a Date object at UTC midnight.
 */
export function parseISODate(dateStr: string): Date {
  const [year, month, day] = dateStr.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

/**
 * Formats a Date object to YYYY-MM-DD string.
 */
export function formatISODate(date: Date): string {
  const y = date.getUTCFullYear();
  const m = String(date.getUTCMonth() + 1).padStart(2, "0");
  const d = String(date.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/**
 * Returns today's date formatted as YYYY-MM-DD in the given timezone (or UTC fallback).
 */
export function getTodayInTimezone(timezone: string): string {
  try {
    const formatter = new Intl.DateTimeFormat("en-CA", {
      timeZone: timezone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
    return formatter.format(new Date());
  } catch {
    const d = new Date();
    return formatISODate(new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())));
  }
}

/**
 * Calculates days between two YYYY-MM-DD dates (target - base).
 */
export function diffDays(baseDateStr: string, targetDateStr: string): number {
  const base = parseISODate(baseDateStr).getTime();
  const target = parseISODate(targetDateStr).getTime();
  return Math.round((target - base) / (1000 * 60 * 60 * 24));
}

/**
 * Adds (or subtracts) days to a YYYY-MM-DD date string.
 */
export function addDays(dateStr: string, days: number): string {
  const date = parseISODate(dateStr);
  date.setUTCDate(date.getUTCDate() + days);
  return formatISODate(date);
}

export interface MilestoneTemplate {
  offsetDays: number; // e.g. 60 means 60 days before eventDate
  timeframeLabel: string;
  weddingTitle: string;
  birthdayTitle: string;
  communityTitle: string;
  priority: "critical" | "high" | "medium";
  owner: string;
  description: string;
}

const MILESTONES_LONG_LEAD: MilestoneTemplate[] = [
  {
    offsetDays: 60,
    timeframeLabel: "T-60 Days",
    weddingTitle: "Lock Ceremony & Reception Venue",
    birthdayTitle: "Secure Venue / Space Reservation",
    communityTitle: "Submit Public Permits & Facility Bookings",
    priority: "critical",
    owner: "Lead Coordinator",
    description: "Review contract terms, fire safety, and initial deposit conditions.",
  },
  {
    offsetDays: 45,
    timeframeLabel: "T-45 Days",
    weddingTitle: "Book Core Catering & Beverage Partner",
    birthdayTitle: "Finalize Food & Beverage Menu Options",
    communityTitle: "Finalize Community Food Stalls & Volunteers",
    priority: "critical",
    owner: "Catering Lead",
    description: "Account for dietary constraints (vegetarian, vegan, allergies).",
  },
  {
    offsetDays: 30,
    timeframeLabel: "T-30 Days",
    weddingTitle: "Send Formal Digital / Physical Invitations",
    birthdayTitle: "Dispatch Invites & Request RSVPs",
    communityTitle: "Launch Community Outreach & Public Registration",
    priority: "high",
    owner: "Communications",
    description: "Track response deadlines, dietary tallies, and accessibility requirements.",
  },
  {
    offsetDays: 14,
    timeframeLabel: "T-14 Days",
    weddingTitle: "Confirm Sound, Lighting & Decor Schematics",
    birthdayTitle: "Lock In DJ, Audio Gear & Photo Booth",
    communityTitle: "Verify PA Systems, Stage & Waste Management",
    priority: "high",
    owner: "Technical Lead",
    description: "Confirm power wattage capacity and rainy-day backup gear.",
  },
  {
    offsetDays: 7,
    timeframeLabel: "T-7 Days",
    weddingTitle: "Lock Final Headcount with Caterer & Seating Plan",
    birthdayTitle: "Order Custom Cake & Finalize Party Favors",
    communityTitle: "Conduct Volunteer Walkthrough & Safety Briefing",
    priority: "high",
    owner: "Event Host",
    description: "Freeze headcounts and confirm arrival windows for vendors.",
  },
  {
    offsetDays: 1,
    timeframeLabel: "T-1 Day",
    weddingTitle: "Rehearsal Walkthrough & Emergency Kit Prep",
    birthdayTitle: "Deliver Favors, Setup Playlists & Room Staging",
    communityTitle: "Erect Tents, Directional Banners & Recycling Bins",
    priority: "critical",
    owner: "Operations Lead",
    description: "Perform final sound check and verify emergency contacts.",
  },
];

const MILESTONES_MEDIUM_LEAD: MilestoneTemplate[] = [
  {
    offsetDays: 21,
    timeframeLabel: "T-21 Days",
    weddingTitle: "Emergency Venue & Catering Lockdown",
    birthdayTitle: "Lock Space & Catering Package",
    communityTitle: "Secure Park/Facility Permit & Sanitation Plan",
    priority: "critical",
    owner: "Lead Planner",
    description: "Fast-track deposits and sign verified agreements.",
  },
  {
    offsetDays: 14,
    timeframeLabel: "T-14 Days",
    weddingTitle: "Dispatch Urgent RSVPs & Diet Questionnaires",
    birthdayTitle: "Dispatch Invites & Request Rapid RSVPs",
    communityTitle: "Publish Schedule & Open Volunteer Sign-Up",
    priority: "high",
    owner: "Communications",
    description: "Gather guest headcounts with 5-day response cutoff.",
  },
  {
    offsetDays: 7,
    timeframeLabel: "T-7 Days",
    weddingTitle: "Finalize Decor Palette & AV Setup",
    birthdayTitle: "Order Cake, Audio Equipment & Props",
    communityTitle: "Coordinate Sound Equipment & Crowd Control",
    priority: "high",
    owner: "Vendor Coordinator",
    description: "Cross-check gear checklists and power availability.",
  },
  {
    offsetDays: 3,
    timeframeLabel: "T-3 Days",
    weddingTitle: "Freeze Final Guest Roster & Seating",
    birthdayTitle: "Confirm Headcount & Beverage Quantities",
    communityTitle: "Safety Inspection & Volunteer Assignment",
    priority: "high",
    owner: "Host",
    description: "Deliver final numbers to catering team.",
  },
  {
    offsetDays: 1,
    timeframeLabel: "T-1 Day",
    weddingTitle: "Stage Decor & Final Vendor Confirmation",
    birthdayTitle: "Pickup Supplies, Music Check & Room Setup",
    communityTitle: "Setup Stage, Tents & Waste Stations",
    priority: "critical",
    owner: "Operations Lead",
    description: "Verify all phone numbers and weather contingencies.",
  },
];

const MILESTONES_SHORT_NOTICE: MilestoneTemplate[] = [
  {
    offsetDays: 3,
    timeframeLabel: "T-3 Days",
    weddingTitle: "Urgent Venue, Catering & Priest/Officiant Lock",
    birthdayTitle: "Instant Space Booking & Drop-Off Catering Order",
    communityTitle: "Emergency Park Reservation & Volunteer Alert",
    priority: "critical",
    owner: "Lead Host",
    description: "Compressed timeline: Confirm only ready-to-deploy vendors.",
  },
  {
    offsetDays: 2,
    timeframeLabel: "T-2 Days",
    weddingTitle: "Immediate Digital RSVP & Diet Poll",
    birthdayTitle: "Direct WhatsApp Invites & Playlist Curations",
    communityTitle: "Broadcast Community Alert & Emergency Supplies",
    priority: "high",
    owner: "Communications",
    description: "Obtain minimum counts for catering preparation.",
  },
  {
    offsetDays: 1,
    timeframeLabel: "T-1 Day",
    weddingTitle: "Rapid Staging, Music & Emergency Kit Checklist",
    birthdayTitle: "Decor Drops, Cake Pickup & Bar Staging",
    communityTitle: "Signage Placement & Safety Marshall Briefing",
    priority: "critical",
    owner: "Operations Lead",
    description: "Verify indoor dry backup locations and run-of-show sequence.",
  },
];

const MILESTONES_SAME_DAY: MilestoneTemplate[] = [
  {
    offsetDays: 0,
    timeframeLabel: "T-Morning (Hours Before)",
    weddingTitle: "Morning Venue Access & Rapid Florals Setup",
    birthdayTitle: "Balloon Arches & Sound System Load-In",
    communityTitle: "Ground Setup, PA Testing & Signage",
    priority: "critical",
    owner: "Lead Coordinator",
    description: "Confirm power access, stage clearance, and early staff arrivals.",
  },
  {
    offsetDays: 0,
    timeframeLabel: "T-2 Hours",
    weddingTitle: "Vendor Handshake & Officiant Soundcheck",
    birthdayTitle: "Food & Beverage Setup, Ice & Cake Drop-Off",
    communityTitle: "Volunteer Orientation & Information Desk Activation",
    priority: "critical",
    owner: "Operations",
    description: "Verify temperature controls, mic levels, and seating flow.",
  },
  {
    offsetDays: 0,
    timeframeLabel: "T-30 Minutes",
    weddingTitle: "Doors Open & Ambient Music Activation",
    birthdayTitle: "Welcome Host Stationed & Photo Area Live",
    communityTitle: "Open Welcome Gates & Start Ambient Music",
    priority: "high",
    owner: "Greeter / MC",
    description: "Ready for first guest arrivals.",
  },
];

/**
 * Generates date-relative preparation tasks.
 * Avoids overlapping branches. Adapts to lead time.
 */
export function buildPreparationTasks(
  eventType: EventType,
  eventDate: string,
  timezone: string,
  existingTasks?: PreparationTask[]
): PreparationTask[] {
  const today = getTodayInTimezone(timezone);
  const leadDays = diffDays(today, eventDate);

  let templates: MilestoneTemplate[];

  if (leadDays <= 0) {
    // Same-day or past-day event
    templates = MILESTONES_SAME_DAY;
  } else if (leadDays <= 5) {
    // Ultra-short notice (1 to 5 days)
    templates = MILESTONES_SHORT_NOTICE.filter((m) => m.offsetDays <= leadDays);
    if (templates.length === 0) templates = MILESTONES_SAME_DAY;
  } else if (leadDays <= 30) {
    // Compressed medium lead time (6 to 30 days)
    templates = MILESTONES_MEDIUM_LEAD.filter((m) => m.offsetDays <= leadDays);
  } else {
    // Long lead time (> 30 days)
    templates = MILESTONES_LONG_LEAD.filter((m) => m.offsetDays <= leadDays);
  }

  return templates.map((tmpl, idx) => {
    const id = `task-${idx + 1}-${tmpl.timeframeLabel.toLowerCase().replace(/[^a-z0-9]/g, "-")}`;
    const existing = existingTasks?.find((t) => t.id === id);

    const taskDueDate = addDays(eventDate, -tmpl.offsetDays);
    const isOverdue = taskDueDate < today && !existing?.isCompleted;

    let title: string;
    if (eventType === "wedding") title = tmpl.weddingTitle;
    else if (eventType === "birthday") title = tmpl.birthdayTitle;
    else title = tmpl.communityTitle;

    return {
      id,
      timeframe: tmpl.timeframeLabel,
      dueDate: taskDueDate,
      title: existing?.title || title,
      description: existing?.description || tmpl.description,
      owner: existing?.owner || tmpl.owner,
      priority: tmpl.priority,
      isCompleted: existing?.isCompleted || false,
      isOverdue,
      dependencies: existing?.dependencies || (idx > 0 ? [`task-${idx}`] : []),
    };
  });
}

/**
 * Builds chronological Day-Of run-of-show blocks.
 */
export function buildDayOfRunOfShow(
  eventType: EventType,
  startTime: string,
  durationHours: number
): DayOfBlock[] {
  const [startH, startM] = startTime.split(":").map(Number);
  const totalDuration = Math.max(2, Math.min(12, durationHours));

  const formatSlot = (offsetStartMin: number, offsetEndMin: number) => {
    const sH = Math.floor((startH * 60 + startM + offsetStartMin) / 60) % 24;
    const sM = (startH * 60 + startM + offsetStartMin) % 60;
    const eH = Math.floor((startH * 60 + startM + offsetEndMin) / 60) % 24;
    const eM = (startH * 60 + startM + offsetEndMin) % 60;
    return `${String(sH).padStart(2, "0")}:${String(sM).padStart(2, "0")} - ${String(eH).padStart(2, "0")}:${String(eM).padStart(2, "0")}`;
  };

  const blocks: DayOfBlock[] = [
    {
      id: "block-setup",
      timeSlot: formatSlot(-60, 0),
      frontOfHouseGuestView: "Venue doors open / Exterior signage and parking greeters ready",
      backOfHouseCrewAction: "Catering bar load-in, AV mic wireless checks, ambient playlist live",
      leadVendorOrRole: "Operations Lead & Audio Tech",
    },
    {
      id: "block-arrival",
      timeSlot: formatSlot(0, 45),
      frontOfHouseGuestView: "Welcome drinks, signature mocktails, and guest book signing",
      backOfHouseCrewAction: "Staggered coat check, dietary wristbands verification, hors d'oeuvres staging",
      leadVendorOrRole: "Host & Catering Captain",
    },
    {
      id: "block-ceremony-or-kickoff",
      timeSlot: formatSlot(45, 90),
      frontOfHouseGuestView:
        eventType === "wedding"
          ? "Processional, ceremonial vows & exchange of rings"
          : eventType === "birthday"
          ? "Grand celebratory entry, welcome toast & roast"
          : "Opening keynote, founder welcome & community ribbon cutting",
      backOfHouseCrewAction: "Audio spotlights active, photographer prime positioning, silent bar replenishment",
      leadVendorOrRole: "Lead Coordinator & MC",
    },
    {
      id: "block-signature-moment",
      timeSlot: formatSlot(90, 135),
      frontOfHouseGuestView:
        eventType === "wedding"
          ? "First dance under focal lighting followed by cake cutting"
          : eventType === "birthday"
          ? "Cake cutting, confetti blast, and group tribute video"
          : "Interactive showcase, community performance & group photo",
      backOfHouseCrewAction: "Dim main lights, ready sparkle effects/confetti, queue crescendo music track",
      leadVendorOrRole: "DJ / AV Lead & MC",
    },
    {
      id: "block-dining-and-social",
      timeSlot: formatSlot(135, Math.min(totalDuration * 60 - 45, 240)),
      frontOfHouseGuestView: "Main course dinner service, social mingling & photo booth memories",
      backOfHouseCrewAction: "Buffet refilling, clearing starter plates, prepping late-night dessert bites",
      leadVendorOrRole: "Catering Captain",
    },
    {
      id: "block-closing-and-teardown",
      timeSlot: formatSlot(Math.max(180, totalDuration * 60 - 45), totalDuration * 60),
      frontOfHouseGuestView: "Farewell favors distribution, exit sparklers / thank-you gifts",
      backOfHouseCrewAction: "Tear down rental equipment, pack leftover food safely, venue walkthrough checkout",
      leadVendorOrRole: "Operations Manager & Clean-up Crew",
    },
  ];

  return blocks;
}
