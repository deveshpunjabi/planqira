# Planqira — Autonomous Event Decision, Commitment & Operations Platform
**Google PromptWars Virtual [Challenge 5] Celebration & Event Planner**  
*“Every decision. Every detail. Under control.”*  
*FastAPI • SQLite ACID Relational Persistence • Kahn's DAG Dependency Engine • Integer-Paise Precision • Google DeepMind Gemma 4*

---

## 1. Executive Summary & Philosophy

Celebration and event planning software fails when it treats planning as a generic text-generation prompt or an unformatted spreadsheet. In the real world, circumstances change constantly: 50 extra guests RSVP at the last minute, venue curfews require audio shifts, weather threatens outdoor ceremonies, and vendor quotes hide overtime penalties or generator fuel charges. Standard tools either suffer IEEE-754 floating-point drift, blindly scale down budgets to fake affordability, or break their data models upon edits.

**Planqira** is an **Event Decision, Commitment & Operations Platform**. Engineered as a high-precision editorial studio, it replaces toy generation with deterministic financial mathematics, cycle-free Directed Acyclic Graph (DAG) dependency cascades, atomic relational persistence, and Google DeepMind Gemma 4 cognitive quote parsing.

Planqira provides two unified experiences:
1. **Public Homepage (`/`)**: An editorial presentation explaining the platform value, highlighting the 4 core planning pillars, offering a live interactive calculation demo with real-time scaling, showcasing curated celebration profiles, and detailing our mathematical philosophy.
2. **Operational Dashboard (`/dashboard`)**: A full-featured workspace controlling live celebrations through 4 persistent workspaces: Creative Direction, Financial Control & Commitments, Timeline & Day-Of Runbook, and the Scenario Lab.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               PLANQIRA SYSTEM TOPOLOGY                                 │
└────────────────────────────────────────────────────────────────────────────────────────┘
                    ┌──────────────────────────────────────────────────┐
                    │      EDITORIAL PUBLIC HOMEPAGE (GET /)           │
                    │  Value Deck • Interactive Simulator • Profiles   │
                    └─────────────────────────┬────────────────────────┘
                                              │ 1-Click Deep Links
                                              ▼
                    ┌──────────────────────────────────────────────────┐
                    │      OPERATIONAL DASHBOARD (GET /dashboard)      │
                    │  Solvency HUD • 4 Workspaces • Zero CDN Drift    │
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
     │  • Kahn's Cycle Detection         │    │  • Hidden Fee Clause Extraction │
     │  • BFS Parameter Invalidation     │    │  • Counter-Negotiation Scripts  │
     │  • Solvency Deficit State Alert   │    │  • Disclosed Heuristic Fallback │
     └─────────────────┬─────────────────┘    └─────────────────────────────────┘
                       │
                       ▼
     ┌───────────────────────────────────────────────────────────────────┐
     │            SQLITE ACID RELATIONAL PERSISTENCE (planqira.db)       │
     │   Foreign Keys • Immutable Scenario Versions • Audit Ledger Logs  │
     │   (Dialect-compatible with Supabase PostgreSQL for Cloud Scaling) │
     └───────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Architectural Breakthroughs

### 1. Integer-Paise Financial Math & Solvency Deficit State
- **Zero Floating-Point Drift:** All money is computed and stored as integer paise (`₹1.00 = 100 paise`). Standard IEEE-754 precision drift (e.g. `0.1 + 0.2 = 0.30000000000000004`) is completely eliminated.
- **Half-Up Tax Rounding:** GST basis points (`1800 bps = 18.00%`, `500 bps = 5.00%`) use exact integer half-up rounding:
  $$\text{Tax Paise} = \left\lfloor \frac{\text{Subtotal Paise} \times \text{BPS} + 5000}{10000} \right\rfloor$$
- **Three Deterministic Pricing Models:**
  - `FIXED`: 1 unit regardless of guest headcount (e.g., Venue rental, candid photography, DJ truss).
  - `PER_CAPITA`: 1 unit per guest (e.g., Royal Rajasthani banquet buffet, guest welcome tokens).
  - `STEP_TIERED`: $\lceil \text{Guests} / \text{Capacity} \rceil$ units (e.g., 1 banqueting table per 8 guests, 1 dual-sided buffet station per 75 guests).
- **Zero Affordability Faking:** If total required spend (Projected spend + 10% contingency reserve) exceeds the target budget, the engine returns an explicit `DEFICIT` state with negative variance rather than forcibly deflating market prices.

### 2. Directed Acyclic Graph (DAG) Invalidation
- **Directed Graph Model:** Operational tasks and vendor commitments are modeled as nodes in a directed dependency graph.
- **Kahn's Algorithm Cycle Detection:** Verifies the operational graph is strictly acyclic on startup and simulation.
- **Cascade Parameter Invalidation:** When a core parameter changes (such as guest count shifting from 250 to 320, or setting shifting from outdoor to indoor), Planqira executes a Breadth-First Search (BFS) to identify all affected downstream nodes, reopens tasks with status `NEEDS_REVIEW`, and marks vendor contracts for reconfirmation.

### 3. Separation of Contractual Commitments from Cash Flow Ledger
Planqira strictly separates contractual obligations from actual cash flow:
- **Approval State:** `ESTIMATED` $\rightarrow$ `QUOTED` $\rightarrow$ `APPROVED` (or `REJECTED`).
- **Payment Status:** `UNPAID` $\rightarrow$ `PARTIAL` $\rightarrow$ `PAID`, computed dynamically from settled ledger records.
- **Quote Approval Deduplication:** Approving a vendor quote marks any pre-existing estimated item in that category as `REPLACED` (setting `superseded_by_id`), eliminating double counting.

### 4. Relational Persistence & Immutable Scenario Versioning
- **ACID Relational Storage:** Backed by SQLite (`planqira.db`) with `PRAGMA foreign_keys = ON;`.
- **Immutable Scenario Snapshots:** Modifying an event scenario does not overwrite history. It verifies the base version (rejecting stale updates with HTTP 409), archives previous scenarios, increments `active_scenario_version`, inserts versioned line items, and appends an immutable record to `audit_logs`.
- **Non-Destructive Reversion:** Reverting to a prior scenario creates a fresh forward revision (e.g. restoring v1 from v2 yields v3), strictly preserving settled payment records, task notes, and historical audit entries.

### 5. Google DeepMind Gemma 4 Cognitive Integration
- **Structured Pydantic Extraction:** Ingests raw, unstructured vendor messages (such as messy WhatsApp proposals) using `gemma-4-31b-it` or `gemma-4-26b-a4b-it` into typed items, tax basis points, advance requirements, and hidden fee flags.
- **Hidden Fee Trap Detection:** Flags unannounced generator fuel charges, late-night overtime rates, and travel surcharges.
- **Counter-Negotiation Scripts:** Automatically generates respectful, commercially rigorous counter-offers.
- **Disclosed Heuristic Fallback:** When running offline without credentials, the engine operates in transparent heuristic mode with `is_simulated: True` clearly labeled.

---

## 3. The Four Dedicated Workspaces

Inside the dashboard (`/dashboard`), Planqira organizes event operations into 4 distinct workspaces:

| Workspace | Purpose | Key Capabilities |
|---|---|---|
| **01. Ideas & Concepts** | Creative Direction | Multi-sensory blueprints (scent notes, lighting warmth, musical tempo), signature ceremony moments, color swatches, DIY cost-saving alternatives, and append-only audit trail. |
| **02. Budget & Commitments** | Financial Control | Deterministic integer-paise budget table (`FIXED`, `PER_CAPITA`, `STEP_TIERED`), vendor commitments pipeline, WhatsApp inquiry generator, cash flow payment ledger, and AI quote extractor modal. |
| **03. Timeline & Operations** | Execution & Contingencies | Lead-time compressed countdown checklist (<14 days vs >30 days), minute-by-minute day-of runbook (Front-of-House vs Back-of-House), failover contingency switchboards (weather, power, medical), and live incident logger. |
| **04. Scenario Lab** | Decision Impact Engine | Headcount range slider (50–600 guests), venue setting selector, side-by-side cost differentials, DAG invalidation alerts, and transactional "Commit as Scenario vNext" button. |

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
- **Calendar Schedule (.ICS):** Conforms strictly to RFC-5545 (`VCALENDAR` / `VEVENT`) with proper text escaping, timezone formatting, and multi-hour midnight crossing support.
- **Executive Print Layout:** Dedicated `@media print` stylesheet optimizing the workspace for direct printing or Save as PDF.

---

## 6. Verification & Test Suite

Planqira includes a comprehensive test suite running against dynamically isolated SQLite databases (`tmp_path`) to ensure 100% test independence:

```bash
# Run the complete test suite
python -m pytest test_engine.py -v
```

### Passing Test Matrix (23/23 Passing):
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

---

## 7. Local Getting Started

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
```

### Environment Configuration (Optional)
Copy `.env.example` to `.env`:
```dotenv
# Google AI Studio API Key (Server-side only)
GEMINI_API_KEY=your_actual_api_key_here

# Model Selection (Defaults to Gemma 4 31B)
AI_MODEL=gemma-4-31b-it
```
*Note: If no API key is configured, Planqira automatically operates in transparent credential-free heuristic mode with simulated tags clearly disclosed.*

### Launch the Platform
```bash
# Start FastAPI application
python -m uvicorn main:app --host 127.0.0.1 --port 8080 --reload
```
Open **[http://127.0.0.1:8080](http://127.0.0.1:8080)** for the Public Homepage, or **[http://127.0.0.1:8080/dashboard](http://127.0.0.1:8080/dashboard)** for the Operational Dashboard.

---

## 8. Deployment Architecture (GitHub + Vercel)

Planqira is engineered for deployment on **GitHub + Vercel**:
- `vercel.json` routes all requests (`/`, `/dashboard`, `/api/*`, `/static/*`) to the ASGI serverless function entry point (`api/index.py`).
- Single branch architecture (`main`) with a repository footprint strictly under 1 MB.
- **Persistence on Serverless:** While local SQLite is included for out-of-the-box development and single-instance environments, persistent multi-user serverless deployments can connect to an external managed PostgreSQL database (such as Supabase or Neon) by specifying `DATABASE_URL`.
