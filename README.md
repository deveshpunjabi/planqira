# UtsavAI — Celebration & Event Planner
**Challenge 5: Celebration & Event Planner (PromptWars Virtual)**  
*Next.js App Router • TypeScript • Google GenAI SDK • GitHub + Vercel Deployment*

---

## 1. Product Overview

**UtsavAI** turns celebration ideas into editable, budget-balanced event plans—and coordinates last-minute replanning when real life changes. Built for **Weddings**, **Birthdays**, and **Community Events**, UtsavAI unites creative aesthetics, deterministic accounting, compressed timelines, and contract protection into a single interactive command center.

### Core Differentiator: Plan Rescue
When budgets shrink, guest lists expand, or weather forces an outdoor celebration inside, **Plan Rescue** coordinates updates across all four planning pillars, analyzes tradeoffs, and presents a structured Before/After proposal with review gates and full Undo capability.

---

## 2. The Four Mandatory Planning Pillars

| Pillar | Features | Engineering Guarantee |
|---|---|---|
| **1. Personalized Themes** | 3 bespoke concepts per brief, visual 4-hex palettes, decor/menu directions, sensory atmosphere hooks (lighting, scent, music), 15-min signature moments, and low-cost DIY swaps. | Theme selection persists locally; colors verified against 6-hex format (`#RRGGBB`). |
| **2. Deterministic Budget** | Strict 12% Emergency Contingency Buffer card, 6 categorical allocations summing exactly to 88%, integer minor currency units (`INR ₹`, `USD $`, `EUR €`), locked costs, line item details, and an interactive What-If recalculator. | $\text{Reserve} = \text{round}(\text{total} \times 12 / 100)$; $\sum \text{Categories} + \text{Reserve} = \text{Total}$ exactly down to 1 minor unit. Deficits are detected and blocked. |
| **3. Date-Aware Timeline** | Macro countdown milestones adapting to lead time (>45 days vs. compressed 3-day rapid schedules), dynamic Planning Readiness Metric %, and chronological Day-Of Run-of-Show splitting Front-of-House (guest view) and Back-of-House (crew actions). | Date math respects local event timezone. Milestones prior to today are flagged overdue. Tasks compressed for short-notice celebrations. |
| **4. Vendor Interrogation Kit** | Essential vendor cards (Venue, Catering, Decor, Audio/DJ, Photography, Logistics), recommended booking windows, contract checklists, sharp "Hidden Fee Trap Questions", and 1-click WhatsApp/email negotiation scripts. | Hidden-fee traps expose corkage, diesel, and clean-up surcharges. Negotiation scripts copy to clipboard with toast notification. |

---

## 3. Plan Rescue & Scenario Mutations

When unforeseen real-world shifts occur, Plan Rescue executes coordinated adjustments:
1. **⚡ Squeeze Budget by 15%**: $\text{New Total} = \text{round}(\text{Current Total} \times 0.85)$. Rebalances unlocked categories while strictly preserving confirmed/locked vendor agreements.
2. **📈 Scale Guest Headcount +25%**: $\text{New Guests} = \lceil \text{Current Guests} \times 1.25 \rceil$. Maintains fixed total budget, recalculating per-guest allocations and shifting catering strategy from plated dining to efficient buffet stations.
3. **🌧️ Rain & Shelter Pivot**: Switches open-air lawns to verified indoor halls or canopy structures, shielding sound electronics and adjusting day-of run-of-show.
4. **✏️ Custom Bounded Directive**: User-specified targeted replan instruction.

### Feasibility & Review Gates
- **Deficit Protection**: If locked costs exceed available allocatable funds, the proposal is flagged **Infeasible** and the Apply button is disabled.
- **Stale Proposal Rejection**: Proposal embeds `baseRevision`. If local browser edits occurred in the interim, the proposal is rejected as stale.
- **Undo Engine**: Restores previous accepted plan content with a fresh, monotonically increasing revision number.

---

## 4. Architecture & Technical Stack

```
Browser (Next.js 15 App Router + React 19 + Tailwind CSS)
   │
   ├── Credential-Free Sample Mode (3 Rich Deterministic Blueprints, 0ms latency)
   │
   └── Live AI Route (/api/plan & /api/replan)
         │
         ├── Zod Schema Validation & Input Boundary Checks
         ├── Official @google/genai SDK (gemini-2.5-flash or GEMINI_MODEL)
         ├── Server-Side GEMINI_API_KEY (Never leaked to client)
         ├── Deterministic Budget Engine (Largest-remainder integer math)
         └── Date Engine (Timezone-aware lead time compression)
```

- **Hosting**: Vercel Git Integration (No Cloud Run, Vertex AI, or GCP server required).
- **Persistence**: Guarded `localStorage` with quota protection and schema versioning (`schemaVersion: 1`).
- **Data Portability**: Full JSON Blueprint Export and Import with validation; browser-native Print / Save as PDF with dedicated print stylesheet.

---

## 5. Environment Variables & Setup

Create a `.env.local` file (modeled on `.env.example`):

```dotenv
# Server-side Gemini API key (Google AI Studio)
GEMINI_API_KEY=your_actual_api_key_here

# Model name supporting structured JSON
GEMINI_MODEL=gemini-2.5-flash

# Set to true only after configuring key
AI_ENABLED=false
```

### Local Development Commands:
```bash
# Install dependencies
npm ci

# Run test suite (30 unit & domain tests)
npm test

# Run TypeScript type check
npm run typecheck

# Run ESLint
npm run lint

# Run production build
npm run build

# Start production server
npm start
```

---

## 6. Vercel Deployment Instructions

1. Push this repository to GitHub:
   ```bash
   git init
   git add .
   git commit -m "feat: UtsavAI Celebration & Event Planner initial release"
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```
2. In Vercel, click **Add New → Project**, import your GitHub repository.
3. Keep standard Next.js framework settings.
4. Add environment variables in Vercel Project Settings:
   - `GEMINI_API_KEY` (Server-only secret)
   - `GEMINI_MODEL`: `gemini-2.5-flash`
   - `AI_ENABLED`: `true` (or `false` for sample mode evaluation)
5. Click **Deploy**.

---

## 7. Three-Minute Judging Demo Script

- **0:00 – 0:25 (Pitch & The Problem)**:  
  *“Event planning is fractured: budgets drift, timelines slip, and sudden changes break everything. UtsavAI is an intelligent Celebration Command Center that turns an event brief into an editable, budget-balanced plan across 4 pillars—and rescues it when real life changes.”*
- **0:25 – 1:00 (The 4 Pillars & Deterministic Budget)**:  
  Open the pre-loaded **Royal Heritage Wedding** sample (`Sample Plan • stored in this browser`). Show the 3 curated themes with visual hex swatches, the **Locked 12% Contingency Buffer Card**, and the 6-category ledger. Demonstrate that category totals plus reserve equal the total budget exactly.
- **1:00 – 1:35 (Dual Timeline & Vendor Interrogation)**:  
  Switch to the **Timeline Tab**: toggle a task checkbox and watch the **Planning Readiness Metric %** update. Switch to **Day-Of Run-of-Show** to show Front-of-House guest choreography versus Back-of-House crew actions. Open the **Vendors Tab**: point out the **Hidden-Fee Trap Question** and click **Copy Script** for instant WhatsApp outreach.
- **1:35 – 2:20 (Plan Rescue in Action)**:  
  Click **Launch Plan Rescue** → select **⚡ Squeeze Budget by 15%**. Highlight the Before/After diff: show that the locked venue cost remains protected while unlocked categories rebalance cleanly. Click **Apply Changes** (bumps revision to Rev #2). Click **Undo** to restore the previous state with a linear revision history.
- **2:20 – 3:00 (Export, Print & Integrity)**:  
  Trigger **Print Plan** to display the multi-page clean print layout. Click **Export JSON** to show browser-local backup. Conclude with architecture highlights: server-side Gemini 2.5 Flash, zero credential exposure, and ultra-lightweight source (< 1 MB).

---

## 8. Limitations & Boundary Disclaimers

- **Credential-Free Sample Mode**: The initial pre-loaded blueprints operate entirely in the client without requiring an API key. Live AI requires `AI_ENABLED=true` and a valid server-side `GEMINI_API_KEY`.
- **Planning Estimates**: Displayed currency figures are planning benchmarks based on standard allocations, not guaranteed binding quotes from external vendors.
- **No Direct Vendor Booking**: UtsavAI generates copyable negotiation drafts; it does not book vendors or process financial payments.
- **Repository Size**: Total uncompressed source code is **611 KB** (Zip archive: **166 KB**), well within the 10 MB event target.
