import { calculateBudget } from "./budget";
import { buildDayOfRunOfShow, buildPreparationTasks } from "./dates";
import {
  EventBrief,
  EventPlan,
  PlanSource,
  RiskPlan,
  ThemeIdea,
  VendorRecord,
} from "./schema";

/**
 * Builds standard 6 vendor records with contract checklists,
 * hidden fee trap questions, and copyable negotiation scripts.
 */
export function buildDefaultVendors(
  brief: EventBrief,
  existingVendors?: VendorRecord[]
): VendorRecord[] {
  const currencySymbol = brief.currency === "INR" ? "₹" : brief.currency === "USD" ? "$" : "€";

  const definitions: Array<{
    id: string;
    category: string;
    title: string;
    bookingWindow: string;
    checklist: string[];
    hiddenFeeQuestion: string;
    script: string;
  }> = [
    {
      id: "vendor-venue",
      category: "Venue & Facilities",
      title: "Primary Space / Ground Management",
      bookingWindow: "T-60 to T-45 Days",
      checklist: [
        "Load-in and breakdown grace period (minimum 2 hours buffer)",
        "Overtime fee per hour in writing before midnight",
        "Power backup / generator availability and diesel billing",
        "Outside catering and decorator royalty charges",
      ],
      hiddenFeeQuestion:
        "Are there mandatory vendor royalty fees, garbage disposal tariffs, or security deposits deducted after load-out?",
      script: `Hello [Venue Manager], we are planning a ${brief.eventType} titled "${brief.title}" for ~${brief.guestCount} guests in ${brief.city} on ${brief.eventDate}. Our total venue allocation is approximately ${currencySymbol}${Math.round(brief.totalBudget * 0.25 / 100).toLocaleString()}. Could you share your rate card and confirm whether load-in buffer hours and generator diesel are included in your base quote? Thank you!`,
    },
    {
      id: "vendor-catering",
      category: "Catering & Beverage",
      title: "Master Kitchen & Beverage Service",
      bookingWindow: "T-45 to T-30 Days",
      checklist: [
        "Per-plate pricing for guaranteed vs actual headcounts",
        "Waiver for outside beverages / corkage charges",
        "Dedicated waitstaff-to-guest ratio (1:15 minimum)",
        "Food tasting session included before contract signing",
      ],
      hiddenFeeQuestion:
        "Is there a corkage fee per bottle or a service charge levied on top of food taxation, and who is responsible for post-event trash bagging?",
      script: `Hi [Catering Lead], we are hosting ${brief.guestCount} guests for "${brief.title}" on ${brief.eventDate} in ${brief.city}. We require ${brief.dietaryRestrictions || "standard vegetarian and non-vegetarian selections"}. Could you provide sample menu packages with transparent per-plate pricing and clarify whether service staff and live cooking stations carry additional surcharges?`,
    },
    {
      id: "vendor-decor",
      category: "Decor & Production",
      title: "Visual Design & Floral Production",
      bookingWindow: "T-30 to T-20 Days",
      checklist: [
        "Itemized mockups with exact flower varieties (local vs imported)",
        "Truss, ceiling rigging, and stage framing permit verification",
        "Teardown schedule and damage waiver deposit",
        "Rain backup layout plan for outdoor elements",
      ],
      hiddenFeeQuestion:
        "Are power cabling, extension boxes, and ladder rigging rentals billed separately from the floral and backdrop line items?",
      script: `Hello [Designer], we are styling a ${brief.eventType} with the vibe "${brief.themePreferences || "timeless elegance"}" on ${brief.eventDate}. Our decor budget is roughly ${currencySymbol}${Math.round(brief.totalBudget * 0.13 / 100).toLocaleString()}. Please send your visual portfolio and let us know if your packages include ambient LED up-lighting and stage draping.`,
    },
    {
      id: "vendor-entertainment",
      category: "Sound, DJ & Performers",
      title: "Audio Visual & Live Artists",
      bookingWindow: "T-30 to T-15 Days",
      checklist: [
        "Dedicated sound engineer present throughout live program",
        "Microphone setup (wireless lapels and hand-held mics)",
        "Local municipal noise curfew compliance plan",
        "Artist green room and rider terms clearly bounded",
      ],
      hiddenFeeQuestion:
        "Does the quote include wireless microphones and technician standby, or is there an hourly surcharge if the schedule runs 30 minutes over?",
      script: `Hi [Artist/DJ], we are organizing "${brief.title}" on ${brief.eventDate} with ${brief.guestCount} guests. We need 3–4 hours of energetic performance and ambient guest sound. Could you confirm your availability and whether audio equipment rental is bundled in your performance fee?`,
    },
    {
      id: "vendor-photo",
      category: "Photography & Cinema",
      title: "Lead Photo & Video Team",
      bookingWindow: "T-45 to T-25 Days",
      checklist: [
        "Number of photographers and cinematographers on site",
        "Delivery timeline for raw files vs edited teaser & highlights",
        "Full copyright and personal printing license included",
        "Backup cameras, lenses, and dual-card recording protocols",
      ],
      hiddenFeeQuestion:
        "Is there an extra delivery fee for full-resolution raw files, and what are the travel or overnight accommodation requirements for the crew?",
      script: `Hello [Studio Team], we love your visual storytelling style and would like to check availability for our ${brief.eventType} on ${brief.eventDate} in ${brief.city}. We want candid guest moments, family portraits, and a 3-minute highlight reel. Please share your coverage tiers and raw delivery turnaround timeline.`,
    },
    {
      id: "vendor-logistics",
      category: "Logistics & Event Day Crew",
      title: "Signage, Guest Care & Clean-Up",
      bookingWindow: "T-20 to T-7 Days",
      checklist: [
        "Parking management and directional signage placement",
        "First aid box, sanitation stations, and accessibility ramps",
        "Post-event venue clean-up and green recycling sorting",
        "Lost-and-found and valuables safeguard locker",
      ],
      hiddenFeeQuestion:
        "Will the municipal dump or recycling facility disposal fee be billed directly to us, or is hauling included in the crew quote?",
      script: `Hi [Logistics Coordinator], we need on-the-ground support for "${brief.title}" on ${brief.eventDate}. Key needs: welcome signage, guest check-in desk, and complete post-event hall clean-up. Please send your crew rates for a 6-hour operational window.`,
    },
  ];

  return definitions.map((def) => {
    const existing = existingVendors?.find((v) => v.id === def.id);
    return {
      id: def.id,
      category: def.category,
      title: def.title,
      bookingWindow: def.bookingWindow,
      status: existing?.status || "not-started",
      contractChecklist: def.checklist.map((item, i) => {
        const existingItem = existing?.contractChecklist.find((c) => c.item === item);
        return {
          id: `${def.id}-item-${i + 1}`,
          item,
          checked: existingItem?.checked || false,
        };
      }),
      hiddenFeeTrapQuestion: def.hiddenFeeQuestion,
      inquiryScript: def.script,
      notes: existing?.notes || "",
      quotedAmountMinor: existing?.quotedAmountMinor,
    };
  });
}

/**
 * Builds default risk management plan.
 */
export function buildDefaultRisks(brief: EventBrief): RiskPlan {
  const isOutdoor = brief.setting === "outdoor" || brief.setting === "hybrid";

  return {
    weatherProtocol: isOutdoor
      ? "Rain & Wind Contingency Protocol: Reserve water-resistant 30x40 canopy tenting and waterproof speaker covers. If precipitation exceeds 40%, shift dining to covered pavilion 4 hours prior."
      : "Climate Control Protocol: Inspect venue HVAC cooling/heating capacity 2 hours prior to guest arrival. Maintain emergency industrial fans and dual power circuit breakers.",
    riskItems: [
      {
        id: "risk-1",
        risk: isOutdoor
          ? "Unseasonal rainfall or heavy wind affecting audio and open-air seating."
          : "Main hall power tripping due to simultaneous heavy kitchen and AV load.",
        severity: "high",
        mitigation: isOutdoor
          ? "Contract an on-call canopy vendor and ensure ground cabling is sealed in heavy-duty rubber ramps."
          : "Separate kitchen high-load circuits from audio console power line; maintain 15kVA diesel generator standby.",
      },
      {
        id: "risk-2",
        risk: "Guest surge exceeding confirmed RSVP counts by 15-20%.",
        severity: "medium",
        mitigation:
          "Mandate caterer maintain a 10% raw ingredient buffer and prepare 2 reserve foldout dining tables behind stage partition.",
      },
      {
        id: "risk-3",
        risk: "Key vendor delayed in city traffic on event day.",
        severity: "medium",
        mitigation:
          "Schedule all core vendor load-ins 3 hours before guest doors open; collect mobile numbers of secondary assistant drivers.",
      },
    ],
  };
}

/**
 * Generates 3 bespoke themes matching event type.
 */
export function buildDefaultThemes(brief: EventBrief): ThemeIdea[] {
  if (brief.eventType === "wedding") {
    return [
      {
        id: "theme-royal-heritage",
        name: "Royal Rajputana Grandeur",
        tagline: "Timeless palace heritage with regal marigold, brass, and velvet opulence",
        aestheticVibe: "Warm candlelight, handwoven block-print fabrics, and grand floral arches",
        paletteHex: ["#800020", "#D4AF37", "#FAF0E6", "#2D112C"],
        decorDirection: "Brass urli bowls with floating marigolds, fairy-lit arches, and antique velvet diwan lounges",
        menuDirection: "Royal Rajasthani & Awadhi vegetarian banquet: Dal Baati Churma, Paneer Lababdar, and saffron Kulfi",
        sensoryHook: "Fragrance of fresh rosewater and mogra garlands accompanied by live shehnai & santoor notes",
        signatureMoment: "Grand floral phoolon ki chaadar entry under warm pyrotechnic cold-fire fountains",
        diySwap: "Use locally grown marigolds and brass-painted clay lamps instead of imported cut roses",
      },
      {
        id: "theme-pastel-meadow",
        name: "Enchanted Pastel Botanical",
        tagline: "Ethereal day-lit celebration with soft eucalyptus, blush florals, and glass accents",
        aestheticVibe: "Light and airy conservatory aesthetic with breezy chiffon drapes and botanical greenery",
        paletteHex: ["#E8D7D8", "#A3B18A", "#FDFBF7", "#C5A880"],
        decorDirection: "Suspended botanical creepers, sheer ivory drapes, and wooden cross-back banquet chairs",
        menuDirection: "Farm-to-table gourmet stations: artisanal sourdough toasts, burrata platters, and lavender lemonade",
        sensoryHook: "Crisp lavender fragrance paired with soft acoustic guitar covers of classic celebration melodies",
        signatureMoment: "Golden hour sunset vow exchange framed by circular botanical ring of baby's breath",
        diySwap: "Potted succulents and terracotta herbs as table runners that guests take home as living favors",
      },
      {
        id: "theme-celestial-night",
        name: "Midnight Starlight Romance",
        tagline: "Modern dramatic evening under a canopy of twinkling crystal constellations",
        aestheticVibe: "Deep indigo night sky contrasted with warm champagne illumination and mirrored tables",
        paletteHex: ["#0B132B", "#F59E0B", "#E0E1DD", "#3B1E3E"],
        decorDirection: "Fibre-optic star cloth ceiling, mirror mosaic centerpieces, and moody amber pin-spotting",
        menuDirection: "Contemporary fusion banquet: smoky tandoori appetizers, truffle risotto bowls, and dark chocolate fondue",
        sensoryHook: "Deep amber woodsy aroma paired with cinematic string quartet and deep cello undertones",
        signatureMoment: "First dance amidst low-lying cold dry-ice clouds with synchronized starlight ceiling effects",
        diySwap: "Repurpose fairy light curtains against dark black draping instead of costly ceiling trussing",
      },
    ];
  } else if (brief.eventType === "birthday") {
    return [
      {
        id: "theme-neon-cyber",
        name: "Neon Cyber-Retro 90s",
        tagline: "Electrifying synthwave nostalgia with glowing arcade lights and punchy beats",
        aestheticVibe: "Vibrant neon glow, holographic textures, and high-energy retro arcade aesthetics",
        paletteHex: ["#FF007F", "#00F0FF", "#2B102B", "#FFE600"],
        decorDirection: "LED neon flex quote signs, holographic iridescent backdrops, and blacklight glow lounges",
        menuDirection: "Gourmet street food bites: loaded smash sliders, loaded waffle fries, and color-changing mocktails",
        sensoryHook: "Synthwave playlist pulsing with bass, paired with sweet candy-floss aroma",
        signatureMoment: "Glow-in-the-dark cake reveal accompanied by synchronized UV strobe dance sequence",
        diySwap: "Blacklight fluorescent spray tape on craft cardstock creates custom glowing photo booth frames",
      },
      {
        id: "theme-boho-sun",
        name: "Golden Hour Boho Picnic",
        tagline: "Relaxed earthy vibes with macrame, sun-drenched wicker, and intimate acoustic sound",
        aestheticVibe: "Warm terracotta and pampas grass with floor rugs and low wooden pallet tables",
        paletteHex: ["#D97706", "#C18C5D", "#F4EBD9", "#441D44"],
        decorDirection: "Low floor cushions, Moroccan brass lanterns, dried floral bundles, and crochet bunting",
        menuDirection: "Grazing table banquet: artisanal cheese wheels, fresh figs, flatbreads, and infused herbal waters",
        sensoryHook: "Warm cedarwood and vanilla incense paired with mellow acoustic indie folk tracks",
        signatureMoment: "Sunset Polaroid memory wall tribute where every guest pins an impromptu snapshot",
        diySwap: "Sanded wooden shipping pallets and picnic blankets eliminate costly table and chair rentals",
      },
      {
        id: "theme-glam-hollywood",
        name: "Vintage Hollywood Glitz",
        tagline: "Classic cinema glamour with red carpets, champagne towers, and monochrome class",
        aestheticVibe: "Dramatic black-and-white accents, gilded brass stanchions, and warm vintage bulbs",
        paletteHex: ["#1C0A1C", "#D4AF37", "#FFFFFF", "#B45309"],
        decorDirection: "Velvet red carpet runner, vintage marquee letter lights, and black tablecloths",
        menuDirection: "Classic cocktail hour: canapes, sparkling cider flute tower, and tiered gold-leaf cake",
        sensoryHook: "Buttery gourmet popcorn aroma and big band jazz swinging through the speakers",
        signatureMoment: "VIP Red Carpet photo arrivals with vintage flash bulb sound effects and personalized guest tickets",
        diySwap: "DIY marquee cardboard letter boxes illuminated with standard warm string lights",
      },
    ];
  } else {
    // Community event
    return [
      {
        id: "theme-eco-harvest",
        name: "Community Green Harvest & Craft",
        tagline: "Sustainable neighborhood gathering celebrating local artisans, fresh food, and zero-waste living",
        aestheticVibe: "Rustic hessian, reclaimed wood, lush potted plants, and joyful natural daylight",
        paletteHex: ["#2D5A27", "#D97706", "#F0E8D9", "#361536"],
        decorDirection: "Burlap table runners, chalkboard stall signs, and living potted herb centerpieces",
        menuDirection: "Community potluck & farm stalls: woodfired flatbreads, regional stews, and fresh orchard cider",
        sensoryHook: "Earthy scent of fresh cut pine and woodsmoke paired with lively bluegrass fiddle tunes",
        signatureMoment: "Collaborative community tree planting and collective mosaic banner painting",
        diySwap: "Bring-your-own-cup initiative and volunteer-sourced upcycled pallet game booths",
      },
      {
        id: "theme-block-carnival",
        name: "Vibrant Neighborhood Street Mela",
        tagline: "Colorful family carnival with street performers, craft bazaars, and traditional music",
        aestheticVibe: "Festive kaleidoscopic bunting, colorful market canopies, and bustling interactive stalls",
        paletteHex: ["#F59E0B", "#E11D48", "#0284C7", "#2B102B"],
        decorDirection: "Multicolor fabric pendents, fairy light overhead festooning, and chalk art walking paths",
        menuDirection: "Street food bazaar: live dosa & chaat counters, artisanal ice pops, and roasted corn on the cob",
        sensoryHook: "Sizzling spice aromas from live tawa counters alongside cheerful acoustic dhol rhythms",
        signatureMoment: "All-ages community flashmob and evening lantern lighting countdown ceremony",
        diySwap: "Recycled fabric scrap bunting sewn by local neighborhood volunteers",
      },
      {
        id: "theme-heritage-story",
        name: "Unity Cultural Showcase",
        tagline: "Honoring neighborhood history, diverse folklore, and shared cultural stories",
        aestheticVibe: "Warm earth tones, photo heritage displays, and an open communal amphitheater",
        paletteHex: ["#5D295D", "#B45309", "#FCFAF6", "#1C0A1C"],
        decorDirection: "Historic neighborhood timeline photo walls, open round seating, and fabric canopy accents",
        menuDirection: "Multi-cultural tasting plates representing every neighborhood cultural tradition",
        sensoryHook: "Aromatic blend of global spices and traditional folk acoustic instruments",
        signatureMoment: "Elder storytelling circle followed by youth cultural dance exhibition",
        diySwap: "Crowdsourced historical family photos printed on cardstock as perimeter bunting",
      },
    ];
  }
}

/**
 * Creates a fully validated, deterministic EventPlan object from an EventBrief.
 */
export function buildDeterministicPlan(
  brief: EventBrief,
  source: PlanSource = "sample"
): EventPlan {
  const budget = calculateBudget(brief.totalBudget);
  const tasks = buildPreparationTasks(brief.eventType, brief.eventDate, brief.timezone);
  const runOfShow = buildDayOfRunOfShow(brief.eventType, brief.startTime, brief.durationHours);
  const vendors = buildDefaultVendors(brief);
  const themes = buildDefaultThemes(brief);
  const risks = buildDefaultRisks(brief);

  const now = new Date().toISOString();

  return {
    metadata: {
      id: `plan-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      schemaVersion: 1,
      revision: 1,
      source,
      createdAt: now,
      updatedAt: now,
    },
    brief,
    selectedThemeId: themes[0].id,
    themes,
    budget: {
      ...budget,
      currency: brief.currency,
    },
    timeline: {
      preparationTasks: tasks,
      dayOfRunOfShow: runOfShow,
    },
    vendors,
    risks,
  };
}
