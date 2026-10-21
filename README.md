# Planqira — Autonomous Event Decision, Commitment & Operations Engine
**PromptWars Virtual [Challenge 5] Celebration & Event Planner**  
*“Every decision. Every detail. Under control.”*  
*FastAPI • SQLite ACID Storage • Topological DAG • Integer-Paise Precision • Gemini 2.5 Flash*

---

## 1. Executive Summary & Philosophy

Most event planning applications fail under real-world pressure because they treat planning as a static AI text prompt. When real life hits—when 50 extra guests RSVP, vendor quotes carry hidden diesel surcharges, or budgets get slashed—toy generators break, produce floating-point rounding errors, or silently scale numbers down to fake affordability.

**Planqira** is an **Event Decision, Commitment & Operations Engine**. It replaces toy text cards with deterministic financial math, true Directed Acyclic Graph (DAG) dependency tracking, ACID relational persistence, and structured AI contract intelligence.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            PLANQIRA SYSTEM TOPOLOGY                         │
└─────────────────────────────────────────────────────────────────────────────┘
          ┌─────────────────────────────────────────────────────────┐
          │      PRECISION OPERATIONS STUDIO (HTML5 / Vanilla JS)   │
          │   Sticky Solvency HUD • 4 Workspaces • Zero CDN Drift   │
          └────────────────────────────┬────────────────────────────┘
                                       │ REST / JSON (Strict Pydantic)
                                       ▼
          ┌─────────────────────────────────────────────────────────┐
          │              FASTAPI OPERATIONAL CONTROL PLANE          │
          │  Simulation • Quote Ingestion • Exporters (.CSV / .ICS) │
          └───────────┬─────────────────────────────┬───────────────┘
                      │                             │
                      ▼                             ▼
┌───────────────────────────────┐     ┌─────────────────────────────────┐
│   DETERMINISTIC SOLVER & DAG  │     │      GEMINI 2.5 FLASH COGNITIVE │
│  • Integer-Paise Accounting   │     │  • WhatsApp Quote Parsing       │
│  • Half-Up Tax Rounding       │     │  • Hidden Fee Clause Extraction │
│  • Kahn's Cycle Detection     │     │  • Counter-Negotiation Scripts  │
│  • BFS Parameter Invalidation │     │  • Disclosed Heuristic Fallback │
└──────────────┬────────────────┘     └─────────────────────────────────┘
               │
               ▼
┌───────────────────────────────────────────────────────────────────────┐
│              SQLITE ACID RELATIONAL STORAGE (planqira.db)             │
│   Foreign Keys • Immutable Scenario Versions • Audit Ledger Logs      │
│   (Dialect-compatible with Supabase PostgreSQL for Cloud Scaling)     │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Architectural Breakthroughs

### 1. Integer-Paise Financial Math & Solvency Deficit State
- **Zero Floating-Point Drift:** All money is computed and stored as integer paise (`₹1.00 = 100 paise`). Standard IEEE-754 floating-point drift is eliminated.
- **Half-Up Tax Rounding:** GST basis points (1800 bps = 18.00%) use standard half-up rounding:
  $$\text{Tax Paise} = \lfloor(\text{Subtotal Paise} \times \text{BPS} + 5000) / 10000\rfloor$$
- **Granular Line-Item Pricing Models:**
  - `FIXED`: 1 unit regardless of guest headcount (e.g., Venue rental, DJ truss).
  - `PER_CAPITA`: 1 unit per guest (e.g., Royal Rajasthani dinner buffet, guest favors).
  - `STEP_TIERED`: $\lceil \text{Guests} / \text{Capacity} \rceil$ units (e.g., 1 banqueting table per 8 guests, 1 buffet station per 75 guests).
- **Zero Affordability Faking:** If total required spend (Projected spend + 10% contingency) exceeds target budget, the engine returns an explicit `DEFICIT` state with negative variance rather than forcibly compressing line items.

### 2. Directed Acyclic Graph (DAG) Invalidation
- **Directed Graph Model:** Operational tasks and vendor commitments are represented in a directed graph.
- **Kahn's Algorithm:** Verifies the operational graph is strictly acyclic.
- **Cascade Parameter Invalidation:** When a core parameter changes (such as guest count shifting from 250 to 320), Planqira executes a Breadth-First Search (BFS) to identify and flag all downstream tasks (e.g., seating cluster layout, meal prep count, catering confirmation) for re-verification.

### 3. Separation of Approval States from Payment Ledger
Planqira strictly separates contractual commitment from cash flow:
- **Approval State:** `ESTIMATED` $\rightarrow$ `QUOTED` $\rightarrow$ `APPROVED` (or `REJECTED`). Only non-rejected items count towards projected commitments.
- **Payment Status:** `UNPAID` $\rightarrow$ `PARTIAL` $\rightarrow$ `PAID`, computed from real ledger advances paid against contract totals.

### 4. Relational Persistence & Immutable Scenario Versioning
- **ACID Relational Storage:** Backed by SQLite (`planqira.db`) with `PRAGMA foreign_keys = ON;`.
- **Immutable Scenario Snapshots:** Adjusting an event scenario does not overwrite history; it archives previous scenarios, increments `active_scenario_version`, inserts versioned items, and appends an immutable record to `audit_logs`.
- **Production Readiness:** Schema is structured for clean transition to Supabase PostgreSQL by swapping the DB connection URL.

### 5. Gemini 2.5 Flash Quoting & Transparent Fallback
- **Structured Pydantic Extraction:** Ingests raw, unstructured vendor messages (e.g., messy WhatsApp texts) into typed items, tax rates, advance requirements, and hidden fee flags.
- **Disclosed Heuristic Fallback:** When running offline without credentials, the engine operates in transparent heuristic mode with `is_simulated: True` clearly labeled.

---

## 3. Four Dedicated Operational Workspaces

| Workspace | Purpose | Key Capabilities |
|---|---|---|
| **01. Mission Control** | Strategic Oversight | Executive metadata, spend breakdown across Approval states, 3 sensory creative concepts with hex color swatches & DIY swaps, live append-only audit trail. |
| **02. Scenario Lab** | Decision Impact Engine | Headcount slider (50–600 guests), side-by-side before/after line item diffs, formula flags (`FIXED`, `PER_CAPITA`, `STEP_TIERED`), DAG invalidation cascade warnings, 1-click commit to Scenario vNext. |
| **03. Commitments Hub** | Vendor Negotiations | Vendor table with approval & payment badges, direct WhatsApp outreach links (`wa.me/?text=...`), hidden fee trap questions, and the AI Vendor Quote Extractor modal with 1-click sample quotes. |
| **04. Live Operations** | Execution & Contingencies | T-Minus countdown checklist with headcount sensitivity flags, minute-by-minute day-of runbook with Front/Back-of-House split, rapid contingency switchboard (rain, generator, medical), and verified file exporters. |

---

## 4. Verified Native File Exports

- **Financial Ledger (.CSV):** Conforms strictly to RFC-4180 with metadata headers, item formulas, quantities, tax rates, approval states, and payment statuses.
- **Calendar Schedule (.ICS):** Conforms strictly to RFC-5545 (`VCALENDAR` / `VEVENT`) with UTC timestamps, timeframes, and descriptions for native import into Apple Calendar, Google Calendar, and Microsoft Outlook.
- **Executive Print Layout:** Dedicated `@media print` stylesheet that cleanly formats the event plan for print or Save as PDF.

---

## 5. Verification & Test Suite

Planqira includes a comprehensive `pytest` suite testing all financial calculations, rounding edge cases, graph invalidations, and API endpoints:

```bash
# Run complete test suite
python -m pytest test_engine.py -v
```

### Passing Test Matrix (18/18 Passing):
1. `test_calculate_tax_paise_exact_half_up_rounding` — Exact half-up rounding at boundaries
2. `test_compute_line_item_paise_fixed` — Fixed pricing independence from guest shifts
3. `test_compute_line_item_paise_per_capita` — Exact per-guest unit calculation
4. `test_compute_line_item_paise_step_tiered` — Math.ceil step capacity threshold jumps
5. `test_evaluate_event_solvency_and_approval_separation` — Approval pipeline vs payment ledger
6. `test_evaluate_event_solvency_deficit_detection` — Deficit detection without false scaling
7. `test_dag_cycle_detection` — Kahn's algorithm cycle verification
8. `test_dag_parameter_invalidation_propagation` — BFS cascade invalidation
9. `test_simulate_scenario_impact` — Decision impact comparison math
10. `test_database_idempotent_init_and_seeding` — Seeding all 3 demo events
11. `test_scenario_versioning_and_audit_logging` — Immutable scenario snapshot commits
12. `test_quote_parsing_fallback` — Disclosed heuristic quote parsing
13. `test_api_health` — Health check & persistence reporting
14. `test_api_list_and_get_events` — Event retrieval & solvency evaluation
15. `test_api_simulate_scenario` — Headcount simulation endpoint
16. `test_api_quote_parsing_and_approval` — Quote parsing and approval ledger commit
17. `test_api_csv_export` — RFC-4180 CSV export endpoint
18. `test_api_ics_export` — RFC-5545 ICS calendar export endpoint

---

## 6. Getting Started

### Prerequisites
- Python 3.12+
- `pip`

### Installation
```bash
# Clone the repository
git clone <repo-url>
cd "Challenge 5 - Celebration & Event Planner"

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration (Optional)
Copy `.env.example` to `.env`:
```dotenv
# Server-side Gemini API key (Google AI Studio)
GEMINI_API_KEY=your_actual_api_key_here
```
*Note: If no API key is provided, Planqira automatically operates in transparent credential-free heuristic mode with simulated tags clearly disclosed.*

### Running the Application
```bash
# Start FastAPI application
python -m uvicorn main:app --host 127.0.0.1 --port 8080 --reload
```
Open **[http://127.0.0.1:8080](http://127.0.0.1:8080)** in any browser.

### Docker Deployment
```bash
docker build -t planqira .
docker run -p 8080:8080 planqira
```
Open **[http://localhost:8080](http://localhost:8080)**.
