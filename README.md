# Planqira — Autonomous Event Decision, Commitment & Operations Platform
**Google PromptWars Virtual [Challenge 5] Celebration & Event Planner**  
*“Every decision. Every detail. Under control.”*  

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg)](https://fastapi.tiangolo.com/)
[![Tests 37 Passed](https://img.shields.io/badge/tests-37%20passed-brightgreen.svg)](TEST-REPORT.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-deveshpunjabi%2Fplanqira-181717.svg)](https://github.com/deveshpunjabi/planqira)

> **Quick Links:** [Architecture & Deep Technical Documentation](DOCUMENTATION.md) • [Automated Verification & Test Report](TEST-REPORT.md) • [Project Context & Roadmap](CONTEXT.md)

*FastAPI • Dual PostgreSQL/SQLite Relational Persistence • Kahn's DAG Dependency Engine • Integer-Paise Precision • Google DeepMind Gemma 4*

---

## 1. Executive Summary & Philosophy

Celebration and event planning software fails when it treats planning as a generic text-generation prompt or an unformatted spreadsheet. In the real world, circumstances change constantly: 50 extra guests RSVP at the last minute, venue curfews require audio shifts, weather threatens outdoor ceremonies, and vendor quotes hide overtime penalties or generator fuel charges. Standard tools either suffer IEEE-754 floating-point drift, blindly scale down budgets to fake affordability, or break their data models upon edits.

**Planqira** is an **Autonomous Event Decision, Commitment & Operations Platform**. Engineered as a high-precision editorial operations studio, it replaces toy generation with deterministic financial mathematics, cycle-free Directed Acyclic Graph (DAG) dependency cascades, atomic relational persistence, and Google DeepMind Gemma 4 cognitive quote parsing.

Planqira provides two unified, responsive experiences:
1. **Public Homepage (`/`)**: An editorial presentation explaining the platform value, highlighting the core planning pillars, offering a live interactive calculation demo with real-time 10% contingency scaling, showcasing curated celebration profiles, and detailing our mathematical philosophy.
2. **Operational Dashboard (`/dashboard`)**: A full-featured workspace controlling live celebrations through 6 persistent workspaces: Overview & Solvency HUD, Creative Direction, Financial Control & Commitments, Timeline & Lead-Time Sequencing, Event Day Operations, and the Scenario Lab.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               PLANQIRA SYSTEM TOPOLOGY                                 │
│                   Strict Light Editorial Aesthetic (Ivory • Charcoal • Olive)           │
└────────────────────────────────────────────────────────────────────────────────────────┘
                    ┌──────────────────────────────────────────────────┐
                    │      EDITORIAL PUBLIC HOMEPAGE (GET /)           │
                    │  Value Deck • Interactive Simulator • Profiles   │
                    └─────────────────────────┬────────────────────────┘
                                              │ 1-Click Deep Links
                                              ▼
                    ┌──────────────────────────────────────────────────┐
                    │      OPERATIONAL DASHBOARD (GET /dashboard)      │
                    │  Solvency HUD • 6 Workspaces • Zero CDN Drift    │
                    └─────────────────────────┬────────────────────────┘
                                              │ REST / JSON (Strict Pydantic V2)
                                              ▼
                    ┌──────────────────────────────────────────────────┐
                    │        FASTAPI OPERATIONAL CONTROL PLANE         │
                    │  Simulation • Quote Ingestion • Exporters (.CSV) │
                    └────────────┬────────────────────────┬────────────┘
                                 │                        │
                                 ▼                        ▼
     ┌───────────────────────────────────┐    ┌─────────────────────────────────┐
     │      DETERMINISTIC SOLVER & DAG   │    │    GEMMA 4 COGNITIVE ENGINE     │
     │  • Integer-Paise Accounting       │    │  • gemma-4-31b-it / 26b-a4b-it  │
     │  • Half-Up Tax Rounding           │    │  • WhatsApp Quote Parsing       │
     │  • Kahn's Cycle Detection         │    │  • Negation & Waived Fee Logic  │
     │  • BFS Parameter Invalidation     │    │  • Percentage Advance Detection │
     │  • Solvency Deficit State Alert   │    │  • Counter-Negotiation Scripts  │
     │  • Separate Commitments & Ledger  │    │  • Disclosed Heuristic Fallback │
     └─────────────────┬─────────────────┘    └─────────────────────────────────┘
                       │
                       ▼
     ┌───────────────────────────────────────────────────────────────────┐
     │           DUAL-MODE RELATIONAL PERSISTENCE (ACID)                 │
     │   • Production: Managed PostgreSQL / Supabase (DATABASE_URL)      │
     │   • Local / Tests: SQLite ACID with Foreign Keys (planqira.db)    │
     │   • Immutable Scenario Snapshots & Append-Only Audit Trail Logs   │
     │   • Strict Tenant Isolation (event_id scoped on all mutations)    │
     └───────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Architectural Breakthroughs

### 1. Integer-Paise Financial Math & Solvency Deficit State
- **Zero Floating-Point Drift:** All money is computed and stored as integer paise (`₹1.00 = 100 paise`). Standard IEEE-754 precision drift (e.g. `0.1 + 0.2 = 0.30000000000000004`) is completely eliminated.
- **Half-Up Tax Rounding:** GST basis points (`1800 bps = 18.00%`, `500 bps = 5.00%`) use exact integer half-up rounding:
  $$\text{Tax Paise} = \left\lfloor \frac{\text{Subtotal Paise} \times \text{BPS} + 5000}{10000} \right\rfloor$$
- **Three Deterministic Pricing Models:**
  - `FIXED`: 1 unit regardless of guest headcount (e.g., Venue rental, candid photography, DJ sound system).
  - `PER_CAPITA`: 1 unit per guest (e.g., Gourmet banquet buffet, guest welcome tokens).
  - `STEP_TIERED`: $\lceil \text{Guests} / \text{Capacity} \rceil$ units (e.g., 1 banqueting table per 8 guests, 1 dual-sided buffet station per 75 guests).
- **Zero Affordability Faking:** If total required spend (Projected spend + 10% contingency reserve) exceeds the target budget, the engine triggers an explicit `DEFICIT` state with negative variance rather than forcibly deflating market prices.

### 2. Directed Acyclic Graph (DAG) Invalidation
- **Directed Graph Model:** Operational tasks and vendor commitments are modeled as nodes in a directed dependency graph.
- **Kahn's Algorithm Cycle Detection:** Verifies the operational graph is strictly acyclic on startup and simulation.
- **Cascade Parameter Invalidation:** When a core parameter changes (such as guest count shifting from 250 to 320, or setting shifting from outdoor to indoor), Planqira executes a Breadth-First Search (BFS) to identify all affected downstream nodes, transitions tasks to `NEEDS_REVIEW` (recording the previous state in `reverification_reason`), and flags vendor commitments for reconfirmation.

### 3. Separation of Contractual Commitments from Cash Flow Ledger
Planqira strictly decouples contractual obligations from actual cash flow:
- **Approval State:** `ESTIMATED` $\rightarrow$ `QUOTED` $\rightarrow$ `APPROVED` (or `REJECTED`).
- **Payment Status:** `UNPAID` $\rightarrow$ `PARTIAL` $\rightarrow$ `PAID`, computed dynamically from settled ledger records in the `payments` table.
- **Zero Double-Counting:** Approving a vendor quote marks pre-existing estimated items in that category as `REPLACED` (`superseded_by_id`), adjusting totals deterministically.
- **Zero Deposit Duplication:** Contract deposits are tracked exclusively on the commitment record (`vendor_commitments.deposit_required_paise`), preventing deposit multiplication across multi-item quotes.

### 4. Relational Persistence & Safe Forward Scenario Reversion
- **Dual PostgreSQL / SQLite Adapter:** Automatically connects to PostgreSQL (Supabase / Neon) in production via `DATABASE_URL` with auto-migration, while defaulting to zero-config SQLite (`planqira.db`) for local testing.
- **Tenant Isolation:** All mutations (`patch_task`, `patch_runbook`, `record_payment`, `approve_quote`, `commit_scenario`, `revert_scenario`) enforce tenant isolation by verifying `event_id` ownership before write operations.
- **Immutable Scenario Snapshots:** Modifying an event scenario does not overwrite history. It verifies the base version (rejecting stale updates with HTTP 409), archives previous scenarios, increments `active_scenario_version`, inserts versioned line items, and appends an immutable record to `audit_logs`.
- **Non-Destructive Reversion:** Reverting to a prior scenario creates a fresh forward revision (e.g. restoring v1 from v2 yields v3) with `paid_amount_paise = 0` on forward items, deriving cash paid strictly from the `payments` ledger without historical snapshot drift.

### 5. Google DeepMind Gemma 4 Cognitive Integration
- **Structured Pydantic Extraction:** Ingests raw, unstructured vendor messages (such as WhatsApp proposals) using `gemma-4-31b-it` or `gemma-4-26b-a4b-it` into typed items, tax basis points, advance requirements, and hidden fee flags.
- **Negation & Context Awareness:** Distinguishes between included items and surcharges (e.g., "Diesel included. No corkage fee. Free delivery." is correctly parsed as waived fees rather than hidden penalties).
- **Percentage Advance Parsing:** Correctly computes percentage advances (e.g., `40% advance` of ₹2,40,000 = ₹96,000) rather than interpreting the integer `40` as ₹40.
- **Counter-Negotiation Scripts:** Automatically generates respectful, commercially rigorous counter-offers.
- **Disclosed Heuristic Fallback:** When running offline without credentials, the engine operates in transparent heuristic mode with `is_simulated: True` clearly labeled.

---

## 3. The Six Dedicated Workspaces

Inside the dashboard (`/dashboard`), Planqira organizes event operations into 6 persistent workspaces accessible via the 235px sidebar navigation:

| Workspace | Purpose | Key Capabilities |
|---|---|---|
| **01. Overview & Solvency HUD** | Command Center | Solvency diagnostic health card, financial KPI metric strip (Target Budget, Solvency Deficit/Surplus, Total Committed, Cash Paid, Remaining Gap), quick action launch buttons, and recent immutable audit log table. |
| **02. Ideas & Creative Direction** | Sensory Blueprints | Multi-sensory blueprints (ambient lighting warmth, olfactory scent notes, acoustic tempos), signature ceremony moments, contrast-rated color swatches, and affordable DIY cost-saving alternatives. |
| **03. Financial Control & Commitments** | Ledger & Quotes | Deterministic integer-paise budget table (`FIXED`, `PER_CAPITA`, `STEP_TIERED`), vendor commitments pipeline, WhatsApp inquiry generator, cash flow payments ledger, and AI quote extractor modal. |
| **04. Timeline & Lead-Time Sequencing** | T-Minus Countdown | Lead-time compressed countdown checklist (<14 days vs >30 days), topological dependency sequencing, priority badges, and reverification warnings for invalidated tasks. |
| **05. Event Day Operations** | Day-Of Execution | Minute-by-minute runbook cues (Front-of-House vs Back-of-House), failover contingency switchboards (weather, power, delay protocols), and live operational incident logger. |
| **06. Scenario Lab** | Decision Simulation | Headcount range slider (50–600 guests), venue setting selector, date picker, side-by-side cost differentials, DAG invalidation alerts, transactional "Commit as Scenario vNext" button, and non-destructive revert modal. |

---

## 4. Curated Demonstration Events

Planqira comes pre-configured with 3 rich, realistic celebration profiles:

1. **Royal Rajputana Heritage Wedding (Jaipur):**
   - 250 Guests • ₹12,00,000 Target Budget • Outdoor Haveli Lawn
   - Pure Vegetarian & Jain banquet buffet, floral mandap, candid photography, shehnai ensemble, live Baraat runbook, and weather/rain failover protocols.
2. **Neo-Tokyo Cyberpunk 21st Birthday (Bengaluru):**
   - 75 Guests • ₹3,50,000 Target Budget • Rooftop Glasshouse
   - Pan-Asian bao sliders, molecular mocktail bar, custom UV neon tunnel, synthwave DJ set, and 11 PM curfew transition protocol.
3. **Sunlit Monsoon Community Harvest Festival (Pune):**
   - 400 Attendees • ₹8,00,000 Target Budget • Open Botanical Amphitheatre
   - Solar-powered acoustic stage, zero-waste compost sorting stations, organic millet feast, and municipal permit clearance.

---

## 5. Native RFC-Compliant File Exports

- **Financial Ledger (.CSV):** Conforms strictly to RFC-4180 with CSV formula injection defense (sanitizing cells starting with `=`, `+`, `-`, `@` with a leading apostrophe `'`).
- **Calendar Schedule (.ICS):** Conforms strictly to RFC-5545 (`VCALENDAR` / `VEVENT`) with non-inclusive exclusive `DTEND` (+1 day for all-day events), 75-octet line folding, proper text escaping, and timezone formatting.
- **Executive Print Layout:** Dedicated `@media print` stylesheet optimizing the workspace for direct printing or Save as PDF.

---

## 6. Comprehensive Verification Suite (37/37 Tests Passing)

Planqira includes two comprehensive automated test suites:

```bash
# 1. Run the deterministic backend test suite (29 tests)
python -m pytest test_engine.py -v

# 2. Run the Playwright browser end-to-end suite (8 tests)
python -m pytest test_e2e_playwright.py -v
```

### Backend Engine Matrix (29/29 Passing):
1. `test_tax_and_contingency_half_up_rounding` — Exact half-up rounding at arithmetic boundaries
2. `test_compute_line_item_paise_models` — FIXED, PER_CAPITA, and STEP_TIERED formulas
3. `test_compute_line_item_paise_rejections` — Input validation rejections for negative numbers
4. `test_evaluate_solvency_deficit_detection` — Deficit detection without false price compression
5. `test_quote_approval_multi_item_and_unique_ids` — Multi-line approval and UUID generation
6. `test_quote_approval_separates_deposit_from_payment` — Contractual deposit separated from cash ledger
7. `test_record_payment_updates_ledger_and_balances` — Cash payment settlement updates
8. `test_quote_replacement_eliminates_double_counting` — Replacing estimated items with contract quotes
9. `test_quote_approval_idempotency_retries` — Safe retry submission handling
10. `test_stale_scenario_proposal_rejection` — HTTP 409 conflict on stale base version
11. `test_scenario_commit_persists_task_and_vendor_invalidation` — Persistence of NEEDS_REVIEW task flags
12. `test_scenario_commit_preserves_completed_tasks_and_payments` — Preserving completed items and ledger
13. `test_scenario_revert_creates_forward_revision` — Non-destructive forward-revision restore
14. `test_create_custom_event` — Custom celebration creation with foundation items
15. `test_short_notice_schedule_compression` — Compressed milestone schedule for lead times < 14 days
16. `test_incident_logging_and_resolution` — Operational incident logging and resolution state
17. `test_ai_model_configuration_and_quote_parsing` — Configurable Gemma 4 model extraction
18. `test_ai_quote_parsing_short_input_rejection` — Rejection of gibberish/short vendor text
19. `test_csv_export_formula_injection_sanitization` — RFC-4180 formula injection defense
20. `test_ics_export_escaping_and_timezone` — RFC-5545 iCalendar escaping and timestamps
21. `test_invalid_nested_inputs` — Pydantic 422 Unprocessable Entity rejections
22. `test_public_homepage_and_dashboard_routes` — Verification of `/`, `/dashboard`, and `/api/health`
23. `test_simulation_endpoint_with_dag_invalidations` — End-to-end simulation endpoint with DAG cascades
24. `test_payment_reconciliation_total_paid_paise` — Total paid paise derived strictly from payments ledger
25. `test_scenario_revert_preserves_payment_integrity` — Cash paid preserved during forward revert
26. `test_cross_event_authorization_isolation` — Multi-tenant event isolation on all patch/record routes
27. `test_quote_negation_and_percentage_advance` — Waived fee logic and 40% advance parsing
28. `test_rfc5545_exclusive_end_date_and_line_folding` — RFC-5545 75-octet folding and exclusive DTEND
29. `test_event_dietary_and_aesthetic_personalization` — Jain/Halal/Vegan dietary line-item shaping

### Playwright Browser E2E Matrix (8/8 Passing):
1. `test_homepage_render` — Editorial typography, 10% contingency calculator, and CTA deep links
2. `test_dashboard_workspaces_and_navigation` — Persistent 235px sidebar navigation across all 6 workspaces
3. `test_quote_extraction_modal` — Multi-item extraction, percentage advance calculation, and negation detection
4. `test_record_payment_modal` — Cash payment recording, ledger posting, and HUD balance update
5. `test_scenario_lab_simulation` — Headcount slider, real-time diff calculation, and DAG invalidation alert
6. `test_accessibility_keyboard_modal_dismissal` — Escape key modal dismiss listener and focus retention
7. `test_file_exports_csv_and_ics` — RFC-4180 CSV and RFC-5545 ICS download endpoints
8. `test_light_editorial_theme_styling` — Strict Light Theme verification (zero dark mode, warm ivory palette)

---

## 7. 10-Step Judge Demonstration Script

Judges can verify the entire platform in under 3 minutes following these steps:

1. **Open the Homepage (`http://127.0.0.1:8080/`):**
   - Observe the editorial typography and warm ivory theme (`#F7F6F2`).
   - Scroll to the interactive budget solver: change budget to ₹20,00,000 and verify the 10% contingency reserve updates instantly to ₹2,00,000.
2. **Launch the Dashboard (`http://127.0.0.1:8080/dashboard`):**
   - Click "Launch Live Dashboard" or use the top navigation button.
   - Observe the persistent 235px sidebar and Solvency HUD.
3. **Inspect Workspace 01 (Overview):**
   - Review the Solvency Health Card, KPI grid, and immutable audit log.
4. **Inspect Workspace 02 (Creative Direction):**
   - Click "02. Ideas & Creative Direction". Observe the 3 multi-sensory blueprints, color swatches, sensory hooks, and DIY cost-saving alternatives.
5. **Extract a Messy Vendor Quote in Workspace 03 (Budget):**
   - Click "03. Financial Control & Commitments".
   - Click **"AI Quote Extractor"** and paste:  
     `"Royal Sound & Stage Setup: Grand banquet stage ₹1,20,000, Acoustic line-array ₹60,000. Diesel included. No corkage fee. 30% advance deposit due by 2026-11-05."`
   - Click "Extract Line Items". Observe that 30% advance (₹54,000) and waived fees (diesel, corkage) are correctly recognized.
6. **Record an Actual Cash Payment:**
   - In Workspace 03, click **"Record Payment"**.
   - Enter ₹25,000 via UPI with reference `UPI-JUDGE-VERIFY-001` and submit.
   - Observe the cash paid metric update immediately and the payment appear in the settled payments ledger.
7. **Inspect Workspace 04 (Timeline) & Lead-Time Tasks:**
   - Click "04. Timeline & Lead-Time Sequencing".
   - Review the topological preparation sequence and priority badges.
8. **Inspect Workspace 05 (Event Day) & Incident Logger:**
   - Click "05. Event Day Operations".
   - Review the minute-by-minute runbook and contingency switchboards.
   - Click **"Log Incident"**, record a simulated weather delay, and observe it log to the live incident ledger.
9. **Simulate Headcount Surge in Workspace 06 (Scenario Lab):**
   - Click "06. Scenario Lab".
   - Drag the headcount slider from 250 to 350 guests.
   - Click **"Compute Impact"**.
   - Observe the side-by-side cost differentials, spend delta, and DAG task invalidation alert.
10. **Export Native CSV and ICS Files:**
    - Click **"Export CSV"** in the sidebar. Inspect the clean RFC-4180 spreadsheet with formula injection sanitization.
    - Click **"Export Calendar (.ics)"**. Verify RFC-5545 compliance with proper multi-day line folding.

---

## 8. Local Getting Started

### Prerequisites
- Python 3.12+
- `pip`

### Installation & Setup
```bash
# Clone the repository
git clone https://github.com/<your-username>/<repo-name>.git
cd "Challenge 5 - Celebration & Event Planner"

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

### Environment Configuration (Optional)
Copy `.env.example` to `.env`:
```dotenv
# Google AI Studio API Key (Server-side only)
GEMINI_API_KEY=your_actual_api_key_here

# Model Selection (Defaults to Gemma 4 31B)
AI_MODEL=gemma-4-31b-it

# PostgreSQL Database URL (Optional for production; defaults to SQLite)
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```
*Note: If no API key is configured, Planqira automatically operates in transparent credential-free heuristic mode with simulated tags clearly disclosed.*

### Launch the Platform
```bash
# Start FastAPI application
python -m uvicorn main:app --host 127.0.0.1 --port 8080 --reload
```
Open **[http://127.0.0.1:8080](http://127.0.0.1:8080)** for the Public Homepage, or **[http://127.0.0.1:8080/dashboard](http://127.0.0.1:8080/dashboard)** for the Operational Dashboard.

---

## 9. Deployment Architecture (GitHub + Vercel / Cloud Run)

Planqira is engineered for seamless production deployment:
- **Vercel Serverless:** `vercel.json` routes all requests (`/`, `/dashboard`, `/api/*`, `/static/*`) to the ASGI serverless function entry point (`api/index.py`).
- **Google Cloud Run:** Multi-stage `Dockerfile` with gunicorn/uvicorn workers.
- **Repository Footprint:** Strictly under 1 MB (< 800 KB total size), single git branch (`main`), with zero bundled vendor binaries or secrets.
